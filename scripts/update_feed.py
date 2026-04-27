#!/usr/bin/env python3
"""
The Orbital — Automated feed updater
Fetches RSS feeds, filters for relevant articles, generates structured entries
via Claude Haiku, and prepends them to news.json.

Cost: ~$0.001 per article processed. Runs daily via GitHub Actions.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import feedparser
import requests
import anthropic

# ── Configuration ────────────────────────────────────────────────────────────

LOOKBACK_DAYS = 7       # How far back to look (was 5 — widened to reduce dry-run risk)
MAX_CANDIDATES = 30     # Max articles to evaluate per run (was 20)
MAX_NEW_ENTRIES = 8     # Max articles to actually add per run
NEWS_JSON = "src/data/news.json"

# RSS feeds — all URLs verified live as of 2026-04-27.
# Organised by thematic cluster for easy maintenance.
RSS_FEEDS = [
    # ── Ecological / regenerative ──────────────────────────────────────────
    # High volume, consistently on-topic
    {"url": "https://www.resilience.org/feed/",
     "name": "Resilience.org"},
    # Post-growth, local economies, Slow Food adjacent
    {"url": "https://localfutures.org/feed/",
     "name": "Local Futures"},
    # Rights of nature legal news
    {"url": "https://www.garn.org/feed/",
     "name": "GARN"},
    # Global south environmental reporting
    {"url": "https://www.ipsnews.net/feed/",
     "name": "IPS News"},
    # Sharing economy, commons, community
    {"url": "https://www.shareable.net/feed/",
     "name": "Shareable"},
    # Justice / ecology / social movements
    {"url": "https://www.yesmagazine.org/feed",
     "name": "YES! Magazine"},

    # ── Deliberative democracy / participation ─────────────────────────────
    # Dedicated citizens-assembly outlet
    {"url": "https://democracynext.org/feed/",
     "name": "DemocracyNext"},
    # Democratic theory, global governance reform
    {"url": "https://www.opendemocracy.net/feed/",
     "name": "openDemocracy"},
    # Civil society, nonprofit governance
    {"url": "https://nonprofitquarterly.org/feed/",
     "name": "Nonprofit Quarterly"},
    # Commons practices and governance resources
    {"url": "https://commonslibrary.org/feed/",
     "name": "Commons Library"},

    # ── Systems / tech / civic innovation ─────────────────────────────────
    # Civic tech aggregator — tools, platforms, experiments
    {"url": "https://civictech.guide/feed/",
     "name": "Civic Tech Guide"},
    # Climate data and systems science journalism
    {"url": "https://www.carbonbrief.org/feed/",
     "name": "Carbon Brief"},
    # Climate investigation reporting
    {"url": "https://insideclimatenews.org/feed/",
     "name": "Inside Climate News"},

    # ── Economics / transition ─────────────────────────────────────────────
    # New Economics Foundation — wellbeing, post-growth policy
    {"url": "https://neweconomics.org/feed",
     "name": "New Economics Foundation"},
    # Existential risk / global governance think-tank
    {"url": "https://globalchallenges.org/feed/",
     "name": "Global Challenges Foundation"},

    # ── Broad academic / international ─────────────────────────────────────
    # Large quality academic feed — good signal when filtered
    {"url": "https://theconversation.com/articles.atom",
     "name": "The Conversation"},
]

# Keyword pre-filter — only articles containing one of these strings
# (case-insensitive) pass to Claude. Keeps API cost minimal.
KEYWORDS = [
    # Ecological / land
    "agroecology", "rewilding", "rights of nature", "rights of the",
    "food sovereignty", "biodiversity", "planetary boundaries",
    "regenerative", "bioregion", "ecocide", "ecosystem restoration",
    "land rights", "ocean governance", "water governance",
    "seed sovereignty", "agroforestry", "permaculture",
    "community land trust", "biocultural", "nature-based",
    "ecological", "indigenous land", "food system",
    # Governance / democracy
    "citizens assembly", "citizen assembly", "citizens' assembly",
    "deliberative democracy", "sortition", "digital democracy",
    "participatory", "climate assembly", "global governance",
    "degrowth", "post-growth", "wellbeing economy",
    "commons", "metagovernance", "earth governance",
    "planetary governance", "collective intelligence",
    "cooperative", "cooperatives", "commons-based",
    "climate justice", "just transition", "polycrisis",
    "doughnut economics", "circular economy",
    "transition towns", "community resilience",
    # Systems / civic tech
    "civic tech", "open data", "digital twin",
    "satellite monitoring", "blockchain governance",
    # Cultural / futures
    "experiential futures", "futures literacy",
]

# ── Prompts ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the curator of The Orbital (theorbital.net), a news feed tracking the planetary systems governance movement — the slow global shift toward regenerative, participatory, ecologically grounded governance.

The feed uses four "orientations" as lenses:
- GARDEN: How do we tend living systems? (agroecology, rewilding, rights of nature, soil, food sovereignty, biodiversity, indigenous land practice, ocean commons)
- SPACESHIP: How do we build and model the systems? (AI, digital twins, satellite monitoring, blockchain governance, open data protocols, climate modelling, civic tech, systems thinking)
- MYSTERIES: How do we transform culture and consciousness? (LARP, megagames, ritual design, experiential futures, festival culture, theatre, ceremony, inner work, narrative)
- ASSEMBLY: How do we decide together? (citizens assemblies, deliberative democracy, sortition, rights of nature legal frameworks, global governance, commons governance, participatory budgeting)

Orientation assignment rules:
- Rights of nature LEGAL work → GARDEN + ASSEMBLY
- Citizens assembly process → ASSEMBLY primary; add GARDEN if topic is ecological
- Regenerative farming → GARDEN only, unless policy angle (add ASSEMBLY)
- Indigenous knowledge holders → GARDEN + MYSTERIES (not ASSEMBLY unless doing governance advocacy)
- Climate science research → SPACESHIP + GARDEN (not ASSEMBLY unless governance-focused)
- Digital democracy tools → SPACESHIP + ASSEMBLY
- Polycrisis / systems collapse → SPACESHIP primary
- Cultural/narrative/inner work around ecology → MYSTERIES + GARDEN

You respond ONLY with valid JSON. No preamble, no explanation outside the JSON."""

ENTRY_PROMPT = """Evaluate this article for The Orbital feed:

Title: {title}
Source: {source}
URL: {url}
Description: {description}

Respond with JSON in EXACTLY this format:

If RELEVANT to planetary systems governance:
{{
  "include": true,
  "slug": "kebab-case-slug-max-60-chars",
  "summary": "1-2 sentence summary, 120-160 chars, factual and specific — what happened, what was found, or what is argued",
  "insight": "One sentence: why this matters for planetary governance — specific implication, not a restatement of the summary",
  "orientations": ["GARDEN"],
  "tags": ["tag-1", "tag-2", "tag-3", "tag-4"]
}}

If NOT relevant:
{{"include": false}}

Rules:
- slug: derived from title, lowercase, hyphens only, max 60 chars, no year needed unless disambiguating
- summary: concrete and informative, not vague ("The article argues X because Y")
- insight: forward-looking and specific ("When X, it changes Y — not just a summary repeat")
- orientations: 1-3 values from [GARDEN, SPACESHIP, MYSTERIES, ASSEMBLY]
- tags: 4-6 lowercase kebab-case strings, specific (prefer "rights-of-nature" over "environment")
- Only include if the article clearly advances the planetary governance / ecological transition / deliberative democracy agenda"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].rstrip("-")


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_og_image(url: str) -> str:
    """Fetch og:image from a URL. Returns empty string on failure."""
    try:
        headers = {
            "User-Agent": "TheOrbital/1.0 (https://theorbital.net)",
            "Accept": "text/html",
        }
        r = requests.get(url, timeout=12, headers=headers)
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r.text, re.IGNORECASE
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r.text, re.IGNORECASE
            )
        return match.group(1).strip() if match else ""
    except Exception:
        return ""


def is_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)


def load_news() -> tuple[list, set]:
    with open(NEWS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    slugs = {item["slug"] for item in data}
    return data, slugs


def load_existing_urls() -> set:
    with open(NEWS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {item.get("sourceUrl", "") for item in data}


# ── Main logic ───────────────────────────────────────────────────────────────

def fetch_candidates(cutoff: datetime, existing_urls: set) -> list:
    """Fetch and keyword-filter new articles from all RSS feeds."""
    candidates = []
    seen_urls = set(existing_urls)
    feed_stats = []

    for feed_info in RSS_FEEDS:
        feed_name = feed_info["name"]
        try:
            feed = feedparser.parse(feed_info["url"])
            if feed.bozo and not feed.entries:
                print(f"  ✗ {feed_name}: parse error")
                feed_stats.append((feed_name, 0, 0))
                continue

            total_recent = 0
            matched = 0
            for entry in feed.entries:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if not pub:
                    continue
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue

                total_recent += 1
                url = entry.get("link", "").strip()
                if not url or url in seen_urls:
                    continue

                title = strip_html(entry.get("title", ""))
                description = strip_html(
                    entry.get("summary", "") or entry.get("description", "")
                )[:600]

                if not is_relevant(f"{title} {description}"):
                    continue

                candidates.append({
                    "title": title,
                    "url": url,
                    "date": pub_dt.strftime("%Y-%m-%d"),
                    "description": description,
                    "source": feed_name,
                })
                seen_urls.add(url)
                matched += 1

            feed_stats.append((feed_name, total_recent, matched))

        except Exception as e:
            print(f"  ✗ {feed_name}: {e}")
            feed_stats.append((feed_name, 0, 0))

    # Per-feed summary
    print("\nFeed results (recent entries / keyword matches):")
    for name, total, matched in feed_stats:
        marker = "✓" if matched > 0 else "·"
        print(f"  {marker} {name}: {total} recent, {matched} matched")

    candidates.sort(key=lambda c: c["date"], reverse=True)
    return candidates


def generate_entry(client: anthropic.Anthropic, candidate: dict) -> dict | None:
    """Call Claude Haiku to evaluate and structure an article."""
    prompt = ENTRY_PROMPT.format(
        title=candidate["title"],
        source=candidate["source"],
        url=candidate["url"],
        description=candidate["description"],
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=450,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        text = re.sub(r"^```json?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  Claude API error: {e}")
        return None


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    print(f"The Orbital — feed updater")
    print(f"Lookback: {LOOKBACK_DAYS} days (since {cutoff.strftime('%Y-%m-%d')})")
    print(f"Sources:  {len(RSS_FEEDS)}")
    print(f"Max candidates: {MAX_CANDIDATES}, max new entries: {MAX_NEW_ENTRIES}\n")

    existing_news, existing_slugs = load_news()
    existing_urls = load_existing_urls()

    candidates = fetch_candidates(cutoff, existing_urls)
    print(f"\n{len(candidates)} keyword-matching candidates\n")

    if not candidates:
        print("Nothing new — done.")
        return 0

    candidates = candidates[:MAX_CANDIDATES]

    new_entries = []
    added_slugs = set(existing_slugs)

    for candidate in candidates:
        if len(new_entries) >= MAX_NEW_ENTRIES:
            break

        print(f"Evaluating: {candidate['title'][:65]}")
        result = generate_entry(client, candidate)
        if not result:
            print("  → skipped (API error)")
            continue
        if not result.get("include"):
            print("  → not relevant")
            continue

        slug = result.get("slug") or slugify(candidate["title"])
        base_slug = slug[:55]
        final_slug = base_slug
        suffix = 2
        while final_slug in added_slugs:
            final_slug = f"{base_slug}-{suffix}"
            suffix += 1

        image = get_og_image(candidate["url"])

        entry = {
            "slug": final_slug,
            "title": candidate["title"],
            "date": candidate["date"],
            "image": image,
            "imageAlt": candidate["title"][:120],
            "summary": result.get("summary", ""),
            "body": "",
            "insight": result.get("insight", ""),
            "actors": [],
            "tags": result.get("tags", []),
            "orientations": result.get("orientations", ["GARDEN"]),
            "sourceUrl": candidate["url"],
        }

        new_entries.append(entry)
        added_slugs.add(final_slug)
        print(f"  → [{', '.join(entry['orientations'])}] {final_slug}")

    if not new_entries:
        print("\nNo entries passed the relevance filter — done.")
        return 0

    updated = new_entries + existing_news
    with open(NEWS_JSON, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Added {len(new_entries)} entries:")
    for e in new_entries:
        print(f"  {e['date']}  {e['slug']}")

    return len(new_entries)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
