#!/usr/bin/env python3
"""
Merge extracted chunk results into the Garden Crawler database.

Usage:
    python3 merge_chunks.py <chunks_dir> [--dry-run] [--source-file <original_file>] [--campaign <name>]

Reads all extraction_*.json files from the chunks directory,
deduplicates by name (case-insensitive), and commits to garden.db.

Also runs a verification pass against the original document.
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")


def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def search_website(actor_name: str) -> tuple[str, str] | None:
    """Use brave-cli to find an actor's website. Returns (url, domain) or None."""
    try:
        result = subprocess.run(
            ["brave-cli", "--query", f"{actor_name} official website", "--count", "3"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        results = data.get("results", [])
        if not results:
            return None
        skip_domains = {'wikipedia.org', 'crunchbase.com', 'linkedin.com', 'bloomberg.com',
                       'pitchbook.com', 'tracxn.com', 'reddit.com', 'youtube.com'}
        for r in results:
            url = r.get('url', '')
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            if not any(sd in domain for sd in skip_domains):
                return (f"{parsed.scheme}://{parsed.netloc}", domain)
        url = results[0]['url']
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return (f"{parsed.scheme}://{parsed.netloc}", domain)
    except Exception:
        return None


def merge_intel(existing_intel: list, new_intel: list) -> list:
    """Merge intel arrays, keeping unique (field, value) pairs."""
    seen = set()
    merged = []
    for item in existing_intel + new_intel:
        key = (item.get("field", ""), item.get("value", ""))
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def resolve_orientation_id(cur, code):
    """Look up orientation ID from code (GARDEN, SPACESHIP, TEMPLE, ASSEMBLY)."""
    if not code:
        return None
    cur.execute("SELECT id FROM orientations WHERE code = ?", (code.upper(),))
    row = cur.fetchone()
    return row[0] if row else None


def resolve_category_id(cur, name):
    """Look up category ID from name."""
    if not name:
        return None
    cur.execute("SELECT id FROM categories WHERE lower(name) = lower(?)", (name,))
    row = cur.fetchone()
    return row[0] if row else None


def normalize_tag(text):
    """Normalize a string into a valid tag: lowercase, hyphenated."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def ensure_tag(cur, tag_name):
    """Insert tag if not exists, return tag_id."""
    tag_name = normalize_tag(tag_name)
    if not tag_name or len(tag_name) < 2:
        return None
    cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    return cur.fetchone()[0]


def link_entity_tag(cur, tag_id, entity_type, entity_id):
    """Link a tag to an entity."""
    if tag_id:
        cur.execute("INSERT OR IGNORE INTO entity_tag (tag_id, entity_type, entity_id) VALUES (?, ?, ?)",
                    (tag_id, entity_type, entity_id))


def main():
    parser = argparse.ArgumentParser(description="Merge chunk extractions into garden.db")
    parser.add_argument("chunks_dir", help="Directory containing extraction_*.json files")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without committing")
    parser.add_argument("--source-file", default=None, help="Original source file path (for verification)")
    parser.add_argument("--skip-website-lookup", action="store_true", help="Skip brave-cli website lookups")
    parser.add_argument("--campaign", default="garden-landscape", help="Campaign name to associate intel with")
    parser.add_argument("--brief", default=None, help="Brief filename to link this result back to")
    args = parser.parse_args()

    load_env()

    # Collect all extraction files
    extraction_files = sorted([
        os.path.join(args.chunks_dir, f) for f in os.listdir(args.chunks_dir)
        if f.startswith("extraction_") and f.endswith(".json")
    ])

    if not extraction_files:
        print(f"No extraction_*.json files found in {args.chunks_dir}")
        sys.exit(1)

    print(f"Found {len(extraction_files)} extraction files")

    # Merge all extractions
    all_actors = {}       # name_lower -> best record
    all_projects = {}
    all_people = {}       # (first_lower, last_lower) -> record
    all_events = {}       # name_lower -> best record
    all_phrases = {}
    all_sources = {}
    all_project_actors = []  # (project_name, actor_name, relationship)
    all_existing_actor_intel = {}  # (name_lower, field, value) -> record

    for ef in extraction_files:
        with open(ef) as f:
            data = json.load(f)

        # Actors — dedup by name, keep the one with more data
        for a in data.get("actors", []):
            key = a["name"].strip().lower()
            if key in all_actors:
                existing = all_actors[key]
                for field in a:
                    if field == "intel":
                        existing["intel"] = merge_intel(existing.get("intel", []), a.get("intel", []))
                    elif field == "categories":
                        # Merge category lists
                        existing_cats = set(existing.get("categories", []))
                        existing_cats.update(a.get("categories", []))
                        existing["categories"] = list(existing_cats)
                    elif field == "tags":
                        # Merge tag lists
                        existing_tags = set(existing.get("tags", []))
                        existing_tags.update(a.get("tags", []))
                        existing["tags"] = list(existing_tags)
                    elif a[field] and (not existing.get(field) or
                                    (field == "description" and len(str(a[field])) > len(str(existing.get(field, ""))))):
                        existing[field] = a[field]
                    # Keep highest relevance score
                    if field == "relevance_score" and a.get(field, 0) > existing.get(field, 0):
                        existing[field] = a[field]
            else:
                all_actors[key] = dict(a)

        # Projects — dedup by name
        for p in data.get("projects", []):
            key = p["name"].strip().lower()
            if key not in all_projects:
                all_projects[key] = dict(p)
            else:
                existing = all_projects[key]
                for field in p:
                    if field == "intel":
                        existing["intel"] = merge_intel(existing.get("intel", []), p.get("intel", []))
                    elif field == "tags":
                        existing_tags = set(existing.get("tags", []))
                        existing_tags.update(p.get("tags", []))
                        existing["tags"] = list(existing_tags)
                    elif p[field] and not existing.get(field):
                        existing[field] = p[field]
            # Extract actor relationships
            for ai in p.get("actors_involved", []):
                if isinstance(ai, str):
                    ai = {"name": ai, "relationship": ""}
                if isinstance(ai, dict) and "name" in ai:
                    all_project_actors.append((p["name"], ai["name"], ai.get("relationship", "")))

        # People — dedup by (first, last)
        for person in data.get("people", []):
            first = person.get("first_name", "").strip().lower()
            last = person.get("last_name", "").strip().lower()
            if not first and not last:
                continue
            key = (first, last)
            if key in all_people:
                existing = all_people[key]
                for field in person:
                    if field == "actor_names":
                        existing_names = set(existing.get("actor_names", []))
                        existing_names.update(person.get("actor_names", []))
                        existing["actor_names"] = list(existing_names)
                    elif field == "tags":
                        existing_tags = set(existing.get("tags", []))
                        existing_tags.update(person.get("tags", []))
                        existing["tags"] = list(existing_tags)
                    elif person[field] and not existing.get(field):
                        existing[field] = person[field]
            else:
                all_people[key] = dict(person)

        # Search phrases — dedup by phrase text
        for sp in data.get("search_phrases", []):
            key = sp["phrase"].strip().lower()
            if key not in all_phrases:
                all_phrases[key] = sp

        # Source URLs — dedup by URL
        for s in data.get("source_urls", []):
            if isinstance(s, str):
                s = {"url": s, "title": "", "description": "", "monitor": False}
            if isinstance(s, dict) and "url" in s and s["url"] not in all_sources:
                all_sources[s["url"]] = s

        # Events — dedup by name
        for evt in data.get("events", []):
            key = evt.get("name", "").strip().lower()
            if not key:
                continue
            if key not in all_events:
                all_events[key] = dict(evt)
            else:
                existing = all_events[key]
                for field in evt:
                    if field == "actors":
                        # Merge actor lists
                        existing_actors = {a["name"].lower(): a for a in existing.get("actors", [])}
                        for a in evt.get("actors", []):
                            existing_actors.setdefault(a["name"].lower(), a)
                        existing["actors"] = list(existing_actors.values())
                    elif evt[field] and not existing.get(field):
                        existing[field] = evt[field]

        # Existing actor intel — dedup by (actor_name, field, value)
        for entry in data.get("existing_actor_intel", []):
            actor_name = entry.get("actor_name", "").strip()
            if not actor_name:
                continue
            for intel in entry.get("intel", []):
                key = (actor_name.lower(), intel.get("field", ""), intel.get("value", ""))
                if key not in all_existing_actor_intel:
                    all_existing_actor_intel[key] = {
                        "actor_name": actor_name,
                        "field": intel.get("field", ""),
                        "value": intel.get("value", ""),
                    }

    print(f"\nMerged totals (after dedup):")
    print(f"  Actors: {len(all_actors)}")
    print(f"  Projects: {len(all_projects)}")
    print(f"  People: {len(all_people)}")
    print(f"  Events: {len(all_events)}")
    print(f"  Search phrases: {len(all_phrases)}")
    print(f"  Source URLs: {len(all_sources)}")
    print(f"  Project-Actor links: {len(all_project_actors)}")

    total_intel = sum(len(a.get("intel", [])) for a in all_actors.values())
    total_intel += sum(len(p.get("intel", [])) for p in all_projects.values())
    if total_intel:
        print(f"  Intel items: {total_intel}")
    if all_existing_actor_intel:
        print(f"  Existing actor intel items: {len(all_existing_actor_intel)}")

    # Website resolution for actors missing websites
    if not args.skip_website_lookup:
        missing_websites = [(k, v) for k, v in all_actors.items()
                           if not v.get("url") and not v.get("website")]
        if missing_websites:
            print(f"\nLooking up {len(missing_websites)} missing actor websites...")
            for key, actor in missing_websites:
                result = search_website(actor["name"])
                if result:
                    url, domain = result
                    actor["url"] = url
                    actor["domain"] = domain
                    print(f"  {actor['name']}: {url}")
                else:
                    actor["url"] = "UNKNOWN"
                    print(f"  {actor['name']}: NOT FOUND")

    if args.dry_run:
        print("\n=== DRY RUN — no database changes ===")
        print("\nActors:")
        for a in sorted(all_actors.values(), key=lambda x: x.get("relevance_score", 0), reverse=True):
            orient = a.get("primary_orientation", "?")
            print(f"  [{a.get('relevance_score', 0)}] {a['name']} ({a.get('type', '?')}) [{orient}] — {a.get('url', 'NO URL')}")
            for intel in a.get("intel", []):
                print(f"        intel: {intel['field']} = {intel['value']}")
        print("\nProjects:")
        for p in all_projects.values():
            print(f"  {p['name']} — {p.get('stage', '?')}")
        if all_people:
            print("\nPeople:")
            for person in all_people.values():
                name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                print(f"  {name} — {person.get('skills', '?')} [{person.get('primary_orientation', '?')}]")
        if all_events:
            print("\nEvents:")
            for evt in all_events.values():
                actors_str = ", ".join(a.get("name", "?") for a in evt.get("actors", []))
                print(f"  {evt['name']} ({evt.get('type', '?')}) — {evt.get('date_start', 'no date')} @ {evt.get('location', 'no location')}")
                if actors_str:
                    print(f"    actors: {actors_str}")
        return

    # Commit to database
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Resolve campaign_id
    campaign_id = None
    if args.campaign:
        cur.execute("SELECT id FROM campaigns WHERE name = ?", (args.campaign,))
        row = cur.fetchone()
        if row:
            campaign_id = row[0]

    # Register the source file
    source_file_id = None
    if args.source_file:
        source_uri = f"file://inbox/{os.path.basename(args.source_file)}"
        cur.execute("INSERT OR IGNORE INTO sources (url, title, description, monitor) VALUES (?, ?, ?, 0)",
                    (source_uri, os.path.basename(args.source_file), f"Ingested document: {os.path.basename(args.source_file)}"))
        cur.execute("SELECT id FROM sources WHERE url = ?", (source_uri,))
        source_file_id = cur.fetchone()[0]

    # ─── Insert actors ───
    actor_ids = {}  # name_lower -> db id
    new_actors = 0
    for key, a in all_actors.items():
        cur.execute("SELECT id FROM actors WHERE lower(name) = lower(?)", (a["name"],))
        row = cur.fetchone()
        if row:
            actor_ids[key] = row[0]
            continue

        # Resolve orientation IDs
        primary_oid = resolve_orientation_id(cur, a.get("primary_orientation"))
        secondary_oid = resolve_orientation_id(cur, a.get("secondary_orientation"))

        # Normalize type
        actor_type = a.get("type", "Network")
        valid_types = {'NGO', 'Company', 'Research', 'Government', 'Network', 'Movement', 'Person'}
        if actor_type not in valid_types:
            actor_type = "Network"

        # Normalize scale/maturity
        scale = a.get("scale")
        valid_scales = {'Local', 'National', 'Regional', 'Global'}
        if scale not in valid_scales:
            scale = None

        maturity = a.get("maturity")
        valid_maturities = {'Idea', 'Early', 'Active', 'Established'}
        if maturity not in valid_maturities:
            maturity = None

        relevance = a.get("relevance_score", 3)
        relevance = max(1, min(5, int(relevance)))

        website = a.get("url") or a.get("website")
        domain = a.get("domain")

        cur.execute("""INSERT INTO actors
            (name, type, primary_orientation_id, secondary_orientation_id,
             description, website, domain, location, scale, maturity,
             relevance_score, connection, contact_pathway, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (a["name"], actor_type, primary_oid, secondary_oid,
             a.get("description"), website, domain,
             a.get("location"), scale, maturity, relevance,
             a.get("connection"), a.get("contact_pathway"), a.get("notes")))
        aid = cur.lastrowid
        actor_ids[key] = aid
        new_actors += 1

        # Add website as source
        if website and website != "UNKNOWN":
            cur.execute("INSERT OR IGNORE INTO sources (url, title, description, monitor) VALUES (?, ?, ?, 0)",
                        (website, f"{a['name']} - Official Website", f"Website for {a['name']}"))
            cur.execute("SELECT id FROM sources WHERE url = ?", (website,))
            sid = cur.fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO source_actor VALUES (?, ?)", (sid, aid))

        # Link to source file
        if source_file_id:
            cur.execute("INSERT OR IGNORE INTO source_actor VALUES (?, ?)", (source_file_id, aid))

        # Link categories
        for cat_name in a.get("categories", []):
            cat_id = resolve_category_id(cur, cat_name)
            if cat_id:
                cur.execute("INSERT OR IGNORE INTO actor_category VALUES (?, ?)", (aid, cat_id))

        # Link tags
        for tag_name in a.get("tags", []):
            tag_id = ensure_tag(cur, tag_name)
            link_entity_tag(cur, tag_id, 'actor', aid)

    # ─── Insert intel for actors ───
    new_intel = 0
    for key, a in all_actors.items():
        aid = actor_ids.get(key)
        if not aid:
            continue
        for intel in a.get("intel", []):
            cur.execute("""INSERT OR IGNORE INTO intel
                (entity_type, entity_id, field, value, source_id, confidence, campaign_id)
                VALUES ('actor', ?, ?, ?, ?, 'extracted', ?)""",
                (aid, intel["field"], intel["value"], source_file_id, campaign_id))
            new_intel += cur.rowcount

    # ─── Insert intel for existing actors in DB ───
    new_existing_actor_intel = 0
    for record in all_existing_actor_intel.values():
        cur.execute("SELECT id FROM actors WHERE lower(name) = lower(?)", (record["actor_name"],))
        row = cur.fetchone()
        if not row:
            continue
        aid = row[0]
        cur.execute("""INSERT OR IGNORE INTO intel
            (entity_type, entity_id, field, value, source_id, confidence, campaign_id)
            VALUES ('actor', ?, ?, ?, ?, 'extracted', ?)""",
            (aid, record["field"], record["value"], source_file_id, campaign_id))
        new_existing_actor_intel += cur.rowcount

    # ─── Insert projects ───
    project_ids = {}
    new_projects = 0
    for key, p in all_projects.items():
        cur.execute("SELECT id FROM projects WHERE lower(name) = lower(?)", (p["name"],))
        row = cur.fetchone()
        if row:
            project_ids[key] = row[0]
            continue

        cur.execute("""INSERT INTO projects (name, website, description, geography, stage, notes)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (p["name"], p.get("website"), p.get("description"),
                     p.get("geography"), p.get("stage"), p.get("notes")))
        pid = cur.lastrowid
        project_ids[key] = pid
        new_projects += 1

        website = p.get("website")
        if website and website != "UNKNOWN":
            cur.execute("INSERT OR IGNORE INTO sources (url, title, description, monitor) VALUES (?, ?, ?, 0)",
                        (website, f"{p['name']} - Project Page", f"Project page for {p['name']}"))
            cur.execute("SELECT id FROM sources WHERE url = ?", (website,))
            sid = cur.fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO source_project VALUES (?, ?)", (sid, pid))

        if source_file_id:
            cur.execute("INSERT OR IGNORE INTO source_project VALUES (?, ?)", (source_file_id, pid))

        # Link tags
        for tag_name in p.get("tags", []):
            tag_id = ensure_tag(cur, tag_name)
            link_entity_tag(cur, tag_id, 'project', pid)

    # Insert intel for projects
    for key, p in all_projects.items():
        pid = project_ids.get(key)
        if not pid:
            continue
        for intel in p.get("intel", []):
            cur.execute("""INSERT OR IGNORE INTO intel
                (entity_type, entity_id, field, value, source_id, confidence, campaign_id)
                VALUES ('project', ?, ?, ?, ?, 'extracted', ?)""",
                (pid, intel["field"], intel["value"], source_file_id, campaign_id))
            new_intel += cur.rowcount

    # ─── Insert project-actor links ───
    new_pa_links = 0
    for proj_name, actor_name, relationship in all_project_actors:
        proj_key = proj_name.strip().lower()
        actor_key = actor_name.strip().lower()
        pid = project_ids.get(proj_key)
        aid = actor_ids.get(actor_key)
        if pid and aid:
            cur.execute("INSERT OR IGNORE INTO project_actor VALUES (?, ?, ?)", (pid, aid, relationship))
            new_pa_links += cur.rowcount

    # ─── Insert people ───
    new_people = 0
    for (first_key, last_key), person in all_people.items():
        first = person.get("first_name")
        last = person.get("last_name")

        # Check for existing person
        if first and last:
            cur.execute("SELECT id FROM people WHERE lower(first_name) = lower(?) AND lower(last_name) = lower(?)",
                        (first, last))
        elif last:
            cur.execute("SELECT id FROM people WHERE lower(last_name) = lower(?)", (last,))
        else:
            cur.execute("SELECT id FROM people WHERE lower(first_name) = lower(?)", (first,))
        if cur.fetchone():
            continue

        primary_oid = resolve_orientation_id(cur, person.get("primary_orientation"))

        cur.execute("""INSERT INTO people
            (first_name, last_name, email, phone, job_title, linkedin_url,
             primary_orientation_id, skills, relationship_tier, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (first, last, person.get("email"), person.get("phone"),
             person.get("job_title"), person.get("linkedin_url"),
             primary_oid, person.get("skills"),
             person.get("relationship_tier", "To explore"),
             person.get("status", "Not yet contacted"),
             person.get("notes")))
        person_id = cur.lastrowid
        new_people += 1

        # Link person to actors
        for actor_name in person.get("actor_names", []):
            actor_key = actor_name.strip().lower()
            aid = actor_ids.get(actor_key)
            if not aid:
                cur.execute("SELECT id FROM actors WHERE lower(name) = lower(?)", (actor_name,))
                row = cur.fetchone()
                if row:
                    aid = row[0]
            if aid:
                role = person.get("role", "")
                cur.execute("INSERT OR IGNORE INTO person_actor VALUES (?, ?, ?)",
                            (person_id, aid, role))

        # Link tags
        for tag_name in person.get("tags", []):
            tag_id = ensure_tag(cur, tag_name)
            link_entity_tag(cur, tag_id, 'person', person_id)

        # Link to source file
        if source_file_id:
            cur.execute("INSERT OR IGNORE INTO source_person VALUES (?, ?)", (source_file_id, person_id))

    # ─── Insert search phrases ───
    new_phrases = 0
    for sp in all_phrases.values():
        cur.execute("INSERT OR IGNORE INTO search_phrases (phrase, priority) VALUES (?, ?)",
                    (sp["phrase"], sp.get("priority", "medium")))
        new_phrases += cur.rowcount

    # ─── Insert source URLs ───
    new_sources = 0
    for s in all_sources.values():
        cur.execute("INSERT OR IGNORE INTO sources (url, title, description, monitor) VALUES (?, ?, ?, ?)",
                    (s["url"], s.get("title", ""), s.get("description", ""), int(s.get("monitor", False))))
        new_sources += cur.rowcount

    # ─── Insert events ───
    new_events = 0
    new_event_actor_links = 0
    for key, evt in all_events.items():
        cur.execute("SELECT id FROM events WHERE lower(name) = lower(?)", (evt["name"],))
        row = cur.fetchone()
        if row:
            event_id = row[0]
        else:
            # Validate type
            valid_types = {'Conference', 'Festival', 'Workshop', 'Assembly', 'Summit',
                          'Symposium', 'Webinar', 'LARP', 'Convention', 'Forum', 'Prize',
                          'Campaign', 'Other'}
            etype = evt.get("type", "Other")
            if etype not in valid_types:
                etype = "Other"

            valid_recurrence = {'one-off', 'annual', 'biennial', 'irregular', 'ongoing'}
            recurrence = evt.get("recurrence")
            if recurrence not in valid_recurrence:
                recurrence = None

            cur.execute("""INSERT INTO events
                (name, type, series, edition, location, date_start, date_end,
                 recurrence, website, description, relevance_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (evt["name"], etype, evt.get("series"), evt.get("edition"),
                 evt.get("location"), evt.get("date_start"), evt.get("date_end"),
                 recurrence, evt.get("website"), evt.get("description"),
                 evt.get("relevance_note")))
            event_id = cur.lastrowid
            new_events += 1

        # Link actors to event
        for actor_ref in evt.get("actors", []):
            actor_name = actor_ref.get("name", "").strip()
            if not actor_name:
                continue
            # Resolve actor ID
            actor_key = actor_name.lower()
            aid = actor_ids.get(actor_key)
            if not aid:
                cur.execute("SELECT id FROM actors WHERE lower(name) = lower(?)", (actor_name,))
                arow = cur.fetchone()
                if arow:
                    aid = arow[0]
            if aid:
                valid_roles = {'organizer', 'speaker', 'attendee', 'sponsor', 'exhibitor', 'partner'}
                role = actor_ref.get("role", "attendee")
                if role not in valid_roles:
                    role = "attendee"
                cur.execute("INSERT OR IGNORE INTO event_actor (event_id, actor_id, role, notes) VALUES (?, ?, ?, ?)",
                            (event_id, aid, role, actor_ref.get("notes")))
                new_event_actor_links += cur.rowcount

    # Link result back to a brief if specified
    if args.brief:
        try:
            source_basename = os.path.basename(args.source_file) if args.source_file else None
            cur.execute("UPDATE briefs SET result_file = ? WHERE filename = ?",
                        (source_basename, args.brief))
        except sqlite3.OperationalError:
            pass

    conn.commit()

    print(f"\n=== Committed to DB ===")
    print(f"  New actors: {new_actors}")
    print(f"  New projects: {new_projects}")
    print(f"  New people: {new_people}")
    print(f"  New intel items: {new_intel}")
    print(f"  New existing-actor intel items: {new_existing_actor_intel}")
    print(f"  New search phrases: {new_phrases}")
    print(f"  New sources: {new_sources}")
    print(f"  New project-actor links: {new_pa_links}")
    print(f"  New events: {new_events}")
    print(f"  New event-actor links: {new_event_actor_links}")

    # ─── Verification pass ───
    if args.source_file and os.path.exists(args.source_file):
        print(f"\n=== Verification ===")
        with open(args.source_file, 'r', encoding='utf-8', errors='replace') as f:
            original_text = f.read()

        STOP_WORDS = {
            # Roles and titles
            'chief', 'executive', 'officer', 'president', 'vice', 'director', 'manager',
            'head', 'senior', 'principal', 'lead', 'founder', 'chairman', 'partner',
            'coordinator', 'facilitator', 'researcher', 'professor', 'fellow',
            # Report/document structure
            'target', 'account', 'analysis', 'strategic', 'overview', 'section',
            'table', 'figure', 'summary', 'recommendation', 'conclusion', 'appendix',
            # Garden-domain descriptive terms (not entity names)
            'governance', 'regenerative', 'assembly', 'participatory', 'democracy',
            'biodiversity', 'ecosystem', 'stewardship', 'indigenous', 'commons',
            'sustainability', 'planetary', 'transformation', 'consciousness',
            'deliberative', 'decentralised', 'decentralized', 'cooperative',
            'agroforestry', 'permaculture', 'rewilding', 'bioacoustic',
            'experiential', 'immersive', 'speculative', 'contemplative',
            # Generic nouns
            'platform', 'system', 'service', 'program', 'project', 'initiative',
            'network', 'movement', 'foundation', 'institute', 'alliance', 'coalition',
            'framework', 'model', 'approach', 'method', 'practice', 'protocol',
            # Generic adjectives
            'global', 'national', 'international', 'european', 'local', 'regional',
            'advanced', 'integrated', 'open', 'new', 'alternative', 'digital',
            'primary', 'key', 'major', 'core', 'next', 'full', 'real',
            # Locations
            'north', 'south', 'east', 'west', 'central', 'northern', 'southern',
            'united', 'states', 'kingdom', 'sweden', 'nordic', 'european',
            # Common orientation-related terms
            'garden', 'eden', 'spaceship', 'earth', 'temple', 'mysteries',
            'general', 'eleusinian',
        }

        def is_likely_entity(phrase: str) -> bool:
            words = phrase.lower().split()
            if len(words) > 5:
                return False
            if words[0] == 'the':
                return False
            non_stop = [w for w in words if w not in STOP_WORDS]
            if len(non_stop) <= len(words) * 0.4:
                return False
            if len(words) == 2 and words[0] in STOP_WORDS:
                return False
            return True

        candidates = set(re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', original_text))
        table_cells = re.findall(r'\|\s*([^|]+?)\s*\|', original_text)
        for cell in table_cells:
            cell = cell.strip()
            if (cell and cell[0].isupper() and len(cell) > 3
                    and len(cell.split()) <= 4
                    and '(' not in cell and '/' not in cell
                    and not any(c in cell for c in ['+', '=', ','])):
                candidates.add(cell)

        candidates = {c for c in candidates if len(c) > 5 and is_likely_entity(c)}

        all_names = set(k for k in all_actors.keys()) | set(k for k in all_projects.keys())
        cur.execute("SELECT lower(name) FROM actors")
        all_names |= set(r[0] for r in cur.fetchall())
        cur.execute("SELECT lower(name) FROM projects")
        all_names |= set(r[0] for r in cur.fetchall())
        for person in all_people.values():
            full = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip().lower()
            if full:
                all_names.add(full)
        cur.execute("SELECT lower(first_name || ' ' || last_name) FROM people WHERE first_name IS NOT NULL AND last_name IS NOT NULL")
        all_names |= set(r[0] for r in cur.fetchall())

        missed = []
        for candidate in sorted(candidates):
            candidate_lower = candidate.lower()
            found = any(candidate_lower in n or n in candidate_lower for n in all_names)
            if not found:
                missed.append(candidate)

        if missed:
            print(f"  Potential entities NOT in database ({len(missed)}):")
            for m in missed[:30]:
                print(f"    - {m}")
            if len(missed) > 30:
                print(f"    ... and {len(missed) - 30} more")
        else:
            print(f"  All detected entity candidates are in the database.")

    conn.close()


if __name__ == "__main__":
    main()
