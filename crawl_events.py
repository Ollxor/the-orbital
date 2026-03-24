#!/usr/bin/env python3
"""
Event Crawler for Garden Crawler

Scrapes event listings from curated sources and populates the events table.
Uses Claude to extract structured event data from HTML pages.

Sources:
  Tier 1 (structured, scrape weekly):
    - People Powered         events page
    - Earth System Governance events page
    - Nordic Larp Calendar    RSS feed
    - GARN                    WordPress RSS + events page
    - Funding the Commons     website

  Tier 2 (curated, scrape monthly):
    - OIDP                    conference page
    - RadicalxChange          events page
    - UNFCCC                  calendar

Usage:
    python3 crawl_events.py                     # Scrape all sources
    python3 crawl_events.py --dry-run           # Preview without writing to DB
    python3 crawl_events.py --source garn       # Scrape a single source
    python3 crawl_events.py --list-sources      # Show all configured sources
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import anthropic
import httpx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "garden.db")
ENV_FILE = os.path.join(BASE_DIR, ".env.local")

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
HTTP_TIMEOUT = 20

# ─── Sources registry ────────────────────────────────────────────────────────

SOURCES = {
    "peoplepowered": {
        "name": "People Powered",
        "urls": ["https://www.peoplepowered.org/events-content"],
        "type": "html",
        "orientation": "ASSEMBLY",
        "description": "Deliberative democracy, citizens assemblies, participatory governance events",
    },
    "esg": {
        "name": "Earth System Governance",
        "urls": [
            "https://www.earthsystemgovernance.org/events/",
            "https://www.earthsystemgovernance.org/annual-conferences/",
        ],
        "type": "html",
        "orientation": "GARDEN",
        "description": "Planetary governance research conferences",
    },
    "nordiclarp": {
        "name": "Nordic Larp",
        "urls": [
            "https://nordiclarp.org/category/events/feed/",
            "https://nordiclarp.org/calendar/",
        ],
        "type": "rss+html",
        "orientation": "TEMPLE",
        "description": "Nordic LARP events, conventions, festivals",
    },
    "garn": {
        "name": "GARN — Global Alliance for the Rights of Nature",
        "urls": [
            "https://www.garn.org/events/",
            "https://www.garn.org/feed/",
        ],
        "type": "html+rss",
        "orientation": "GARDEN",
        "description": "Rights of nature tribunals, symposia, COP side events",
    },
    "ftc": {
        "name": "Funding the Commons",
        "urls": ["https://www.fundingthecommons.io/"],
        "type": "html",
        "orientation": "SPACESHIP",
        "description": "Commons and public goods funding events",
    },
    "oidp": {
        "name": "OIDP — Intl Observatory on Participatory Democracy",
        "urls": ["https://oidp.net/en/conference.php"],
        "type": "html",
        "orientation": "ASSEMBLY",
        "description": "Participatory democracy conferences worldwide",
    },
    "radicalxchange": {
        "name": "RadicalxChange",
        "urls": ["https://www.radicalxchange.org/events/"],
        "type": "html",
        "orientation": "SPACESHIP",
        "description": "Digital democracy, governance innovation, plural technology",
    },
    "unfccc": {
        "name": "UNFCCC",
        "urls": ["https://unfccc.int/calendar"],
        "type": "html",
        "orientation": "GARDEN",
        "description": "UN climate governance events and COP schedule",
    },
    "nordsustainability": {
        "name": "Nordic Sustainability Conferences",
        "urls": ["https://sustainabilityonline.net/news/sustainability-conferences-in-the-nordics/"],
        "type": "html",
        "orientation": "GARDEN",
        "description": "Curated list of Nordic sustainability conferences",
    },
    "democracyrd": {
        "name": "Democracy R&D",
        "urls": ["https://democracyrd.org/events/"],
        "type": "html",
        "orientation": "ASSEMBLY",
        "description": "Deliberative democracy research and practice events",
    },
    "larpradar": {
        "name": "Larp Radar",
        "urls": ["https://larp-radar.com/larps-list"],
        "type": "html",
        "orientation": "TEMPLE",
        "description": "European LARP events calendar",
    },
    "cop_demos": {
        "name": "EU CoP on Deliberative Democracy",
        "urls": ["https://cop-demos.jrc.ec.europa.eu/events"],
        "type": "html",
        "orientation": "ASSEMBLY",
        "description": "European deliberative democracy events",
    },
}


# ─── Env & clients ───────────────────────────────────────────────────────────

def load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_anthropic_client():
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env.local")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


# ─── HTTP ────────────────────────────────────────────────────────────────────

def fetch_url(url, timeout=HTTP_TIMEOUT):
    """Fetch URL with error handling. Returns text content or None."""
    headers = {
        "User-Agent": "GardenCrawler/1.0 (event discovery; +https://github.com/garden-crawler)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        print(f"    FETCH ERROR {url}: {e}")
        return None


def html_to_text(html, max_chars=15000):
    """Strip HTML to readable text, keeping structure hints."""
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self.skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "nav", "footer", "header", "iframe"):
                self.skip = True
            elif tag in ("h1", "h2", "h3", "h4"):
                self.parts.append(f"\n## ")
            elif tag in ("li",):
                self.parts.append("\n- ")
            elif tag == "br":
                self.parts.append("\n")
            elif tag == "a":
                href = dict(attrs).get("href", "")
                if href and href.startswith("http"):
                    self.parts.append(f" [{href}] ")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "nav", "footer", "header", "iframe"):
                self.skip = False
            elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr", "article"):
                self.parts.append("\n")

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    extractor = TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass

    text = "".join(extractor.parts)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text[:max_chars].strip()


# ─── Claude extraction ───────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an event data extractor for The Garden, a planetary governance research project.

Given text from a web page listing events, extract ALL events you can find.
For each event, extract as much as possible:

Return a JSON array (no markdown fences). Each object:
{
  "name": "Event Name",
  "type": "Conference|Summit|Workshop|Festival|Assembly|Symposium|LARP|Convention|Forum|Prize|Campaign|Webinar|Other",
  "series": "Recurring series name or null",
  "edition": "Specific edition label or null",
  "location": "City, Country or null",
  "date_start": "ISO partial date like 2026-04-16 or 2026-04 or 2026, or null",
  "date_end": "ISO partial date or null",
  "recurrence": "one-off|annual|biennial|irregular|ongoing or null",
  "website": "URL or null",
  "description": "1-2 sentence description or null",
  "relevance_note": "Why relevant to planetary governance, regenerative systems, participatory democracy, or transformative experiences. null if unclear."
}

Rules:
- Only include events from 2025 onwards (skip past events before 2025)
- Include the event website URL when available
- For recurring series (e.g. "COP", "Knutepunkt"), include both series name and edition
- Use ISO date format: 2026-04-16 (full), 2026-04 (month), 2026 (year only)
- If no events found, return an empty array []
- Return ONLY the JSON array, no other text"""


def extract_events_with_claude(client, page_text, source_name, source_url):
    """Use Claude to extract structured events from page text."""
    user_msg = f"""Source: {source_name}
URL: {source_url}

Page content:
{page_text}"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": user_msg},
            ],
            system=EXTRACTION_PROMPT,
        )
        text = response.content[0].text.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        events = json.loads(text)
        if not isinstance(events, list):
            print(f"    WARNING: Claude returned non-list: {type(events)}")
            return []
        return events
    except json.JSONDecodeError as e:
        print(f"    JSON PARSE ERROR: {e}")
        print(f"    Raw response: {text[:300]}")
        return []
    except Exception as e:
        print(f"    CLAUDE ERROR: {e}")
        return []


# ─── Database operations ─────────────────────────────────────────────────────

def load_existing_events(cur):
    """Load all existing events for dedup matching."""
    cur.execute("SELECT id, name, series, edition, date_start, location FROM events")
    return cur.fetchall()


def normalize_for_match(text):
    """Normalize text for fuzzy matching."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def find_existing_event(existing_events, evt):
    """Check if an event already exists. Returns event_id or None."""
    evt_name_norm = normalize_for_match(evt.get("name", ""))
    evt_series_norm = normalize_for_match(evt.get("series"))
    evt_edition_norm = normalize_for_match(evt.get("edition"))
    evt_date = evt.get("date_start", "")

    for eid, ename, eseries, eedition, edate, eloc in existing_events:
        # Exact name match
        if normalize_for_match(ename) == evt_name_norm and evt_name_norm:
            return eid

        # Series + edition match
        if evt_series_norm and evt_edition_norm:
            if (normalize_for_match(eseries) == evt_series_norm
                    and normalize_for_match(eedition) == evt_edition_norm):
                return eid

        # Series + same year
        if evt_series_norm and evt_date and edate:
            if (normalize_for_match(eseries) == evt_series_norm
                    and evt_date[:4] == (edate or "")[:4]):
                return eid

        # Name containment (one contains the other, both 8+ chars)
        ename_norm = normalize_for_match(ename)
        if len(evt_name_norm) >= 8 and len(ename_norm) >= 8:
            if evt_name_norm in ename_norm or ename_norm in evt_name_norm:
                return eid

        # Series match alone (e.g. "COP30" matches "UN Climate Change Conference COP30")
        if evt_series_norm:
            if normalize_for_match(eseries) == evt_series_norm:
                # Same series, check if same year or edition overlaps
                if evt_date and edate and evt_date[:4] == (edate or "")[:4]:
                    return eid
                if evt_edition_norm and normalize_for_match(eedition) == evt_edition_norm:
                    return eid

        # Cross-check: series name appears in the other event's name
        if evt_series_norm and len(evt_series_norm) >= 4:
            if evt_series_norm in ename_norm:
                if evt_date and edate and evt_date[:4] == (edate or "")[:4]:
                    return eid
        if eseries and len(normalize_for_match(eseries)) >= 4:
            if normalize_for_match(eseries) in evt_name_norm:
                if evt_date and edate and evt_date[:4] == (edate or "")[:4]:
                    return eid

    return None


def resolve_actor_id(cur, actor_name):
    """Fuzzy-match an actor name to an ID."""
    if not actor_name:
        return None
    cur.execute("SELECT id, name FROM actors WHERE canonical_id IS NULL")
    for aid, aname in cur.fetchall():
        if aname.lower() == actor_name.lower():
            return aid
        if aname.lower() in actor_name.lower() or actor_name.lower() in aname.lower():
            return aid
    return None


def insert_event(cur, evt, source_key):
    """Insert an event into the database. Returns event_id."""
    valid_types = {
        'Conference', 'Festival', 'Workshop', 'Assembly', 'Summit',
        'Symposium', 'Webinar', 'LARP', 'Convention', 'Forum', 'Prize',
        'Campaign', 'Other',
    }
    etype = evt.get("type", "Other")
    if etype not in valid_types:
        etype = "Other"

    valid_recurrence = {'one-off', 'annual', 'biennial', 'irregular', 'ongoing'}
    recurrence = evt.get("recurrence")
    if recurrence not in valid_recurrence:
        recurrence = None

    cur.execute("""
        INSERT INTO events (name, type, series, edition, location,
                            date_start, date_end, recurrence, website,
                            description, relevance_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        evt["name"], etype, evt.get("series"), evt.get("edition"),
        evt.get("location"), evt.get("date_start"), evt.get("date_end"),
        recurrence, evt.get("website"), evt.get("description"),
        evt.get("relevance_note"),
    ))
    return cur.lastrowid


def register_source(cur, source_key, source_cfg):
    """Register event source in sources table. Returns source_id."""
    url = source_cfg["urls"][0]
    cur.execute("SELECT id FROM sources WHERE url = ?", (url,))
    row = cur.fetchone()
    if row:
        # Update last_fetch
        cur.execute("UPDATE sources SET last_fetch = datetime('now') WHERE id = ?", (row[0],))
        return row[0]

    cur.execute("""
        INSERT INTO sources (url, title, description, last_fetch, monitor)
        VALUES (?, ?, ?, datetime('now'), 1)
    """, (url, f"Event Source: {source_cfg['name']}", source_cfg["description"]))
    return cur.lastrowid


# ─── Crawl orchestration ─────────────────────────────────────────────────────

def crawl_source(client, cur, source_key, source_cfg, existing_events, dry_run=False):
    """Crawl a single event source. Returns (new_count, skip_count, error_count)."""
    print(f"\n{'='*60}")
    print(f"  {source_cfg['name']}")
    print(f"  Orientation: {source_cfg['orientation']}")
    print(f"{'='*60}")

    all_extracted = []

    for url in source_cfg["urls"]:
        print(f"\n  Fetching: {url}")
        html = fetch_url(url)
        if not html:
            print(f"    SKIP (fetch failed)")
            continue

        page_text = html_to_text(html)
        if len(page_text) < 100:
            print(f"    SKIP (page too short: {len(page_text)} chars)")
            continue

        print(f"    Extracted {len(page_text)} chars of text")
        print(f"    Sending to Claude for event extraction...")

        events = extract_events_with_claude(client, page_text, source_cfg["name"], url)
        print(f"    Claude found {len(events)} events")
        all_extracted.extend(events)

        # Rate limit between API calls
        time.sleep(1)

    if not all_extracted:
        print(f"\n  No events extracted from {source_cfg['name']}")
        return 0, 0, 0

    # Dedup within this batch
    seen_names = set()
    deduped = []
    for evt in all_extracted:
        name_norm = normalize_for_match(evt.get("name", ""))
        if name_norm and name_norm not in seen_names:
            seen_names.add(name_norm)
            deduped.append(evt)

    new_count = 0
    skip_count = 0
    error_count = 0

    # Reload existing events to catch anything just inserted
    existing_events = load_existing_events(cur)

    for evt in deduped:
        name = evt.get("name", "").strip()
        if not name:
            continue

        existing_id = find_existing_event(existing_events, evt)
        if existing_id:
            print(f"    SKIP (exists): {name}")
            skip_count += 1
            continue

        if dry_run:
            print(f"    NEW: {name}")
            if evt.get("date_start"):
                print(f"         date: {evt['date_start']}")
            if evt.get("location"):
                print(f"         location: {evt['location']}")
            if evt.get("type"):
                print(f"         type: {evt['type']}")
            if evt.get("website"):
                print(f"         url: {evt['website']}")
            new_count += 1
            continue

        try:
            event_id = insert_event(cur, evt, source_key)
            new_count += 1
            print(f"    INSERT [id={event_id}]: {name}")

            # Reload for next iteration
            existing_events = load_existing_events(cur)
        except Exception as e:
            print(f"    ERROR inserting {name}: {e}")
            error_count += 1

    return new_count, skip_count, error_count


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Crawl event sources for The Garden")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to database")
    parser.add_argument("--source", default=None, help="Crawl a single source by key (e.g. 'garn')")
    parser.add_argument("--list-sources", action="store_true", help="List all configured sources")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip Claude extraction, just fetch and show page text length")
    args = parser.parse_args()

    if args.list_sources:
        print(f"{'Key':<20} {'Name':<45} {'Orientation':<12} URLs")
        print("-" * 110)
        for key, cfg in SOURCES.items():
            urls = ", ".join(cfg["urls"])
            print(f"{key:<20} {cfg['name']:<45} {cfg['orientation']:<12} {urls}")
        return

    # Select sources to crawl
    if args.source:
        if args.source not in SOURCES:
            print(f"ERROR: Unknown source '{args.source}'")
            print(f"Available: {', '.join(SOURCES.keys())}")
            sys.exit(1)
        sources_to_crawl = {args.source: SOURCES[args.source]}
    else:
        sources_to_crawl = SOURCES

    # Init
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    client = None
    if not args.no_ai:
        client = get_anthropic_client()

    existing_events = load_existing_events(cur)
    print(f"Existing events in DB: {len(existing_events)}")
    print(f"Sources to crawl: {len(sources_to_crawl)}")
    if args.dry_run:
        print("MODE: dry-run (no database writes)")

    total_new = 0
    total_skip = 0
    total_error = 0

    for source_key, source_cfg in sources_to_crawl.items():
        if args.no_ai:
            # Just fetch and show text length
            for url in source_cfg["urls"]:
                html = fetch_url(url)
                if html:
                    text = html_to_text(html)
                    print(f"  {source_cfg['name']} [{url}]: {len(text)} chars extracted")
                else:
                    print(f"  {source_cfg['name']} [{url}]: FETCH FAILED")
            continue

        # Register source in DB
        if not args.dry_run:
            register_source(cur, source_key, source_cfg)

        new, skip, err = crawl_source(
            client, cur, source_key, source_cfg, existing_events, args.dry_run
        )
        total_new += new
        total_skip += skip
        total_error += err

        # Commit after each source
        if not args.dry_run:
            conn.commit()

        # Reload existing events
        existing_events = load_existing_events(cur)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  New events:     {total_new}")
    print(f"  Skipped (dups): {total_skip}")
    print(f"  Errors:         {total_error}")
    print(f"  Total in DB:    {len(load_existing_events(cur))}")

    conn.close()


if __name__ == "__main__":
    main()
