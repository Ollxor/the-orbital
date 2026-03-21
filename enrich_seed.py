#!/usr/bin/env python3
"""
Enrich seed actors in garden.db with websites, domains, sources, and category links.

Reads actors missing websites, uses brave-cli to find their official sites,
updates website/domain fields, creates source records and source_actor links,
and matches actors to categories via keyword heuristic.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRIPT_DIR, "garden.db")
ENV_FILE = os.path.join(SCRIPT_DIR, ".env.local")


def load_env():
    """Load environment variables from .env.local."""
    if not os.path.exists(ENV_FILE):
        print(f"ERROR: {ENV_FILE} not found")
        sys.exit(1)
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def search_website(actor_name: str) -> tuple[str, str, str, str] | None:
    """
    Use brave-cli to find an actor's website.
    Returns (url, domain, title, description) or None.
    """
    try:
        result = subprocess.run(
            ["brave-cli", "--query", f"{actor_name} official website", "--count", "3"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            print(f"    brave-cli error: {result.stderr.strip()}")
            return None
        data = json.loads(result.stdout)
        results = data.get("results", [])
        if not results:
            return None

        skip_domains = {
            'wikipedia.org', 'crunchbase.com', 'linkedin.com', 'bloomberg.com',
            'pitchbook.com', 'tracxn.com', 'reddit.com', 'youtube.com',
            'twitter.com', 'x.com', 'facebook.com', 'instagram.com',
            'wikidata.org', 'amazon.com',
        }

        for r in results:
            url = r.get('url', '')
            title = r.get('title', '')
            description = r.get('description', '')
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            if not any(sd in domain for sd in skip_domains):
                clean_url = f"{parsed.scheme}://{parsed.netloc}"
                return (clean_url, domain, title, description)

        # Fallback to first result if all were skip domains
        r = results[0]
        url = r.get('url', '')
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        clean_url = f"{parsed.scheme}://{parsed.netloc}"
        return (clean_url, domain, r.get('title', ''), r.get('description', ''))
    except subprocess.TimeoutExpired:
        print(f"    brave-cli timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"    brave-cli returned invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"    brave-cli unexpected error: {e}")
        return None


def build_category_keywords(categories: list[dict]) -> dict[int, set[str]]:
    """
    Build a keyword set for each category from its name, description,
    and search_terms. Returns {category_id: set of lowercase keywords}.
    """
    cat_keywords = {}
    for cat in categories:
        cid = cat['id']
        words = set()

        # Tokenize name
        for token in re.findall(r'[a-z]+', cat['name'].lower()):
            if len(token) > 3:
                words.add(token)

        # Tokenize description
        if cat['description']:
            for token in re.findall(r'[a-z]+', cat['description'].lower()):
                if len(token) > 3:
                    words.add(token)

        # Tokenize search_terms JSON
        if cat['search_terms']:
            try:
                terms = json.loads(cat['search_terms'])
                for term in terms:
                    for token in re.findall(r'[a-z]+', term.lower()):
                        if len(token) > 3:
                            words.add(token)
            except (json.JSONDecodeError, TypeError):
                pass

        # Remove very generic stop words that would cause false matches
        stop = {
            'that', 'this', 'with', 'from', 'have', 'been', 'were', 'they',
            'their', 'will', 'would', 'could', 'should', 'about', 'also',
            'into', 'than', 'then', 'them', 'each', 'make', 'like', 'long',
            'look', 'many', 'some', 'such', 'more', 'most', 'only', 'over',
            'just', 'made', 'after', 'year', 'back', 'come', 'when', 'very',
            'based', 'well', 'models', 'tools', 'design', 'practice',
            'scale', 'large', 'systems', 'world', 'global', 'local',
            'new', 'human', 'social', 'change', 'making', 'driven',
            'research', 'science', 'network', 'platform', 'framework',
        }
        words -= stop

        cat_keywords[cid] = words
    return cat_keywords


def match_actor_to_categories(
    actor_name: str,
    actor_description: str | None,
    actor_type: str | None,
    cat_keywords: dict[int, set[str]],
    min_matches: int = 2,
) -> list[int]:
    """
    Match an actor to categories based on keyword overlap.
    Returns list of category IDs where overlap >= min_matches.
    """
    # Build actor's keyword set from name + description
    actor_text = actor_name
    if actor_description:
        actor_text += " " + actor_description
    if actor_type:
        actor_text += " " + actor_type

    actor_words = set()
    for token in re.findall(r'[a-z]+', actor_text.lower()):
        if len(token) > 3:
            actor_words.add(token)

    scored = []
    for cid, kw_set in cat_keywords.items():
        overlap = actor_words & kw_set
        if len(overlap) >= min_matches:
            scored.append((cid, len(overlap)))

    # Sort by score descending, take top 3 to avoid over-linking
    scored.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored[:3]]


def main():
    load_env()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Read actors with no website
    cur.execute(
        "SELECT id, name, type, description FROM actors "
        "WHERE website IS NULL OR website = ''"
    )
    actors = [dict(row) for row in cur.fetchall()]
    print(f"Found {len(actors)} actors without websites.\n")

    if not actors:
        print("Nothing to enrich.")
        conn.close()
        return

    # 2. Load categories for keyword matching
    cur.execute("SELECT id, name, description, search_terms FROM categories")
    categories = [dict(row) for row in cur.fetchall()]
    cat_keywords = build_category_keywords(categories)
    print(f"Loaded {len(categories)} categories for matching.\n")

    # 3. For each actor, search for website and update
    stats = {
        'websites_found': 0,
        'websites_not_found': 0,
        'sources_created': 0,
        'source_actor_links': 0,
        'category_links': 0,
    }

    for i, actor in enumerate(actors, 1):
        aid = actor['id']
        name = actor['name']
        print(f"[{i}/{len(actors)}] {name}")

        # Rate-limit: small delay between requests
        if i > 1:
            time.sleep(0.5)

        result = search_website(name)

        if result:
            url, domain, title, description = result
            print(f"  -> {url} ({domain})")

            # Update actor website and domain
            cur.execute(
                "UPDATE actors SET website = ?, domain = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (url, domain, aid)
            )
            stats['websites_found'] += 1

            # Insert source
            cur.execute(
                "INSERT OR IGNORE INTO sources (url, title, description, monitor) "
                "VALUES (?, ?, ?, 0)",
                (url, f"{name} - Official Website", f"Website for {name}")
            )
            cur.execute("SELECT id FROM sources WHERE url = ?", (url,))
            sid = cur.fetchone()['id']
            stats['sources_created'] += cur.rowcount if cur.rowcount > 0 else 0

            # Link source to actor
            cur.execute(
                "INSERT OR IGNORE INTO source_actor (source_id, actor_id) VALUES (?, ?)",
                (sid, aid)
            )
            if cur.rowcount > 0:
                stats['source_actor_links'] += 1

        else:
            print(f"  -> NOT FOUND")
            stats['websites_not_found'] += 1

        # 5. Category matching (do this regardless of website result)
        matched_cats = match_actor_to_categories(
            name,
            actor['description'],
            actor['type'],
            cat_keywords,
            min_matches=2,
        )
        if matched_cats:
            cat_names = []
            for cid in matched_cats:
                cur.execute(
                    "INSERT OR IGNORE INTO actor_category (actor_id, category_id) "
                    "VALUES (?, ?)",
                    (aid, cid)
                )
                if cur.rowcount > 0:
                    stats['category_links'] += 1
                # Get category name for display
                cur.execute("SELECT name FROM categories WHERE id = ?", (cid,))
                cat_names.append(cur.fetchone()['name'])
            print(f"  categories: {', '.join(cat_names)}")

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'='*50}")
    print(f"  Websites found:      {stats['websites_found']}")
    print(f"  Websites not found:  {stats['websites_not_found']}")
    print(f"  Sources created:     {stats['sources_created']}")
    print(f"  Source-actor links:  {stats['source_actor_links']}")
    print(f"  Category links:      {stats['category_links']}")


if __name__ == "__main__":
    main()
