#!/usr/bin/env python3
"""
Parse event_participation intel into structured events and event_actor rows.

Reads free-text event_participation values from the intel table,
extracts individual events with dates/locations/types, and populates
the events and event_actor tables.

Usage:
    python3 parse_events.py              # dry-run: show what would be inserted
    python3 parse_events.py --commit     # actually write to database
    python3 parse_events.py --seed-search  # also generate search phrases for events
"""
import argparse
import json
import os
import re
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")

# ── Event type classification keywords ──────────────────────────
TYPE_KEYWORDS = {
    "Conference": ["conference", "cop", "devcon", "congress"],
    "Summit": ["summit"],
    "Forum": ["forum"],
    "Workshop": ["workshop", "lab"],
    "Symposium": ["symposium", "symposia"],
    "Assembly": ["assembly", "assemblies", "agm"],
    "Festival": ["festival", "greenfest"],
    "LARP": ["larp", "larps"],
    "Convention": ["convention"],
    "Prize": ["prize", "award"],
    "Campaign": ["campaign", "week", "veckan"],
    "Webinar": ["webinar", "podcast", "virtual"],
}

# ── Month lookup ────────────────────────────────────────────────
MONTHS = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

# ── Series detection patterns ───────────────────────────────────
SERIES_PATTERNS = [
    (r"\bCOP\s*(\d+)\b", "UNFCCC COP", lambda m: m.group(1)),
    (r"\bIUCN\b.*?\bCongress\b", "IUCN World Conservation Congress", None),
    (r"\bWorld Social Forum\b", "World Social Forum", None),
    (r"\bFunding the Commons\b", "Funding the Commons", None),
    (r"\bDevcon\b", "Devcon", None),
    (r"\bDweb Camp\b", "Dweb Camp", None),
    (r"\bTEDx\b", "TEDx", None),
    (r"\bNew Shape Forum\b", "New Shape Forum", None),
]


def classify_type(text):
    """Guess event type from text."""
    lower = text.lower()
    for etype, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return etype
    return "Other"


def extract_date(text):
    """Extract date_start from parenthetical or inline references.
    Returns (date_start, date_end) as partial ISO strings or None."""
    # "May 2023" / "October 2024" — but not city names like "Marseille"
    month_pat = r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s,]+(\d{4})\b"
    m = re.search(month_pat, text)
    if m:
        month = MONTHS[m.group(1).lower()[:3]]
        return f"{m.group(2)}-{month}", None

    # "2021" standalone year
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return m.group(1), None

    # "Upcoming" → future, no date
    if "upcoming" in text.lower():
        return "upcoming", None

    return None, None


def extract_location(text):
    """Extract location from parenthetical hints like '(Marseille, 2021)' or '(Berkeley, Oct 2024)'."""
    # Look for parenthetical with a city/country name
    parens = re.findall(r"\(([^)]+)\)", text)
    for p in parens:
        # Skip if it's just a year or just a description
        parts = [s.strip() for s in p.split(",")]
        for part in parts:
            # If it's not a year and not a month, it might be a location
            if not re.match(r"^\d{4}$", part) and not re.match(
                r"^(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{0,4}$", part, re.I
            ):
                # Skip descriptive phrases
                if len(part.split()) <= 3 and not any(
                    kw in part.lower() for kw in [
                        "e.g.", "historic", "virtual", "panel", "covering",
                        "awarded", "curation", "think tank", "primarily",
                    ]
                ):
                    return part

    # Inline location patterns: "in Nepal", "in Berkeley"
    m = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
    if m:
        loc = m.group(1)
        # Filter out false positives
        if loc.lower() not in ("the",):
            return loc

    return None


def detect_series(text):
    """Detect if event is part of a known series. Returns (series_name, edition) or (None, None)."""
    for pattern, series_name, edition_fn in SERIES_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            edition = edition_fn(m) if edition_fn else None
            return series_name, edition
    return None, None


def infer_role(text, actor_name):
    """Infer the actor's role at the event."""
    lower = text.lower()
    if any(kw in lower for kw in ["host", "run ", "runs ", "organis", "organiz", "initiated"]):
        return "organizer"
    if any(kw in lower for kw in ["launched", "curati", "awarded"]):
        return "organizer"
    if any(kw in lower for kw in ["speak", "panel", "tedx", "present"]):
        return "speaker"
    if any(kw in lower for kw in ["sponsor", "fund"]):
        return "sponsor"
    return "attendee"


def split_events(value):
    """Split a semicolon-separated event_participation value into individual event texts.
    Respects parenthesised ranges like '(Berkeley, Oct 2024; Jan 2025)'."""
    parts = []
    current = ""
    depth = 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def parse_single_event(text):
    """Parse a single event text fragment into a structured dict."""
    name = text.strip()
    # Clean trailing/leading punctuation
    name = name.strip(" ,;-")

    date_start, date_end = extract_date(text)
    location = extract_location(text)
    series, edition = detect_series(text)
    etype = classify_type(text)

    # Clean the name: remove parenthetical details for a cleaner event name
    clean_name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    # Remove trailing dates from name
    clean_name = re.sub(r"\s*,?\s*\d{4}\s*$", "", clean_name).strip()
    # Remove "Upcoming" prefix
    clean_name = re.sub(r"^Upcoming\s+", "", clean_name, flags=re.I).strip()
    # Remove leading "Host" / "Speaking engagements at"
    clean_name = re.sub(r"^Host\s+", "", clean_name, flags=re.I).strip()
    clean_name = re.sub(r"^Speaking engagements at\s+", "", clean_name, flags=re.I).strip()
    # Collapse whitespace
    clean_name = re.sub(r"\s+", " ", clean_name).strip()

    if not clean_name:
        clean_name = name

    return {
        "name": clean_name,
        "type": etype,
        "series": series,
        "edition": edition,
        "location": location,
        "date_start": date_start,
        "date_end": date_end,
        "recurrence": "annual" if series else None,
        "raw_text": text,
    }


def deduplicate_events(events_with_actors):
    """Merge events that are clearly the same (same series+edition or very similar names)."""
    merged = {}
    for evt, actor_id, role in events_with_actors:
        # Build a dedup key
        if evt["series"] and evt["edition"]:
            key = f"{evt['series']}:{evt['edition']}"
        elif evt["series"]:
            key = f"{evt['series']}:{evt.get('date_start', 'unknown')}"
        else:
            # Normalize name for comparison
            key = re.sub(r"[^a-z0-9]", "", evt["name"].lower())

        if key in merged:
            # Add this actor to existing event
            merged[key]["actors"].append((actor_id, role))
            # Merge location/date if missing
            if not merged[key]["event"]["location"] and evt["location"]:
                merged[key]["event"]["location"] = evt["location"]
            if not merged[key]["event"]["date_start"] and evt["date_start"]:
                merged[key]["event"]["date_start"] = evt["date_start"]
        else:
            merged[key] = {"event": evt, "actors": [(actor_id, role)]}

    return list(merged.values())


def _maybe_split_series(text):
    """Split 'UNFCCC COP26, COP27' into individual events."""
    # Pattern: comma-separated items where each looks like a series edition
    parts = [p.strip() for p in text.split(",")]
    if len(parts) >= 2 and all(re.search(r"\b(?:COP|Devcon)\s*\d+\b", p, re.I) for p in parts):
        return parts
    return [text]


def parse_all_events(cur):
    """Parse all event_participation intel and return structured events."""
    cur.execute("""
        SELECT i.entity_id, a.name, i.value
        FROM intel i
        JOIN actors a ON i.entity_id = a.id
        WHERE i.field = 'event_participation'
        ORDER BY a.name
    """)
    rows = cur.fetchall()

    all_events = []
    for actor_id, actor_name, value in rows:
        fragments = split_events(value)
        for frag in fragments:
            # Handle "COP26, COP27" style comma-separated series editions
            sub_frags = _maybe_split_series(frag)
            for sf in sub_frags:
                evt = parse_single_event(sf)
                role = infer_role(frag, actor_name)
                all_events.append((evt, actor_id, role))

    return deduplicate_events(all_events)


def commit_events(cur, merged_events, dry_run=True):
    """Insert events and event_actor rows. Returns counts."""
    inserted_events = 0
    inserted_links = 0
    skipped = 0

    for entry in merged_events:
        evt = entry["event"]

        if dry_run:
            actors_str = ", ".join(
                f"actor_id={aid} ({role})" for aid, role in entry["actors"]
            )
            print(f"  EVENT: {evt['name']}")
            if evt["series"]:
                print(f"         series={evt['series']} edition={evt['edition']}")
            print(f"         type={evt['type']} loc={evt['location']} date={evt['date_start']}")
            print(f"         actors: {actors_str}")
            print()
            inserted_events += 1
            inserted_links += len(entry["actors"])
            continue

        # Check if event already exists
        cur.execute("SELECT id FROM events WHERE name = ?", (evt["name"],))
        existing = cur.fetchone()
        if existing:
            event_id = existing[0]
            skipped += 1
        else:
            cur.execute("""
                INSERT INTO events (name, type, series, edition, location,
                                    date_start, date_end, recurrence, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evt["name"], evt["type"], evt["series"], evt["edition"],
                evt["location"], evt["date_start"], evt["date_end"],
                evt["recurrence"], evt.get("raw_text"),
            ))
            event_id = cur.lastrowid
            inserted_events += 1

        # Link actors
        for actor_id, role in entry["actors"]:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO event_actor (event_id, actor_id, role)
                    VALUES (?, ?, ?)
                """, (event_id, actor_id, role))
                inserted_links += 1
            except sqlite3.IntegrityError:
                pass

    if not dry_run:
        cur.connection.commit()

    return inserted_events, inserted_links, skipped


def seed_search_phrases(cur, merged_events, dry_run=True):
    """Generate search phrases for event research."""
    phrases = set()

    # From known event series
    series_seen = set()
    for entry in merged_events:
        evt = entry["event"]
        if evt["series"] and evt["series"] not in series_seen:
            series_seen.add(evt["series"])
            phrases.add(f"{evt['series']} 2025 2026 schedule speakers")

    # Generic event discovery phrases per orientation
    orientation_phrases = [
        "planetary governance conference 2025 2026",
        "regenerative economics summit 2025",
        "rights of nature tribunal 2025 2026",
        "participatory democracy assembly 2025",
        "transformative games festival LARP 2025",
        "commons governance workshop 2025",
        "ecological resilience conference nordic 2025",
        "deliberative democracy symposium 2025",
        "alternative ownership conference cooperative 2025",
        "futures thinking festival experiential 2025",
    ]
    phrases.update(orientation_phrases)

    count = 0
    for phrase in sorted(phrases):
        if dry_run:
            print(f"  SEARCH: {phrase}")
        else:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO search_phrases (phrase, priority)
                    VALUES (?, 'medium')
                """, (phrase,))
                count += 1
            except sqlite3.IntegrityError:
                pass

    if not dry_run:
        cur.connection.commit()

    return len(phrases) if dry_run else count


def main():
    parser = argparse.ArgumentParser(description="Parse event_participation intel into structured events")
    parser.add_argument("--commit", action="store_true", help="Write to database (default: dry-run)")
    parser.add_argument("--seed-search", action="store_true", help="Also generate event search phrases")
    args = parser.parse_args()

    dry_run = not args.commit

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    print("Parsing event_participation intel...\n")
    merged = parse_all_events(cur)
    print(f"Found {len(merged)} unique events from 13 intel records\n")

    if dry_run:
        print("── DRY RUN (use --commit to write) ──\n")

    evt_count, link_count, skip_count = commit_events(cur, merged, dry_run)

    print(f"\n{'Would insert' if dry_run else 'Inserted'}: {evt_count} events, {link_count} actor links")
    if skip_count:
        print(f"Skipped (already exist): {skip_count}")

    if args.seed_search:
        print(f"\n── Search Phrases ──\n")
        phrase_count = seed_search_phrases(cur, merged, dry_run)
        print(f"\n{'Would insert' if dry_run else 'Inserted'}: {phrase_count} search phrases")

    conn.close()


if __name__ == "__main__":
    main()
