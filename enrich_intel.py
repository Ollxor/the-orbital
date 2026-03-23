#!/usr/bin/env python3
"""
Extract intel from a Gemini Deep Research markdown file and insert it into
garden.db's intel table.

Usage:
    python enrich_intel.py
    python enrich_intel.py --file inbox/some_other_file.md
    python enrich_intel.py --dry-run
"""
import argparse
import os
import re
import sqlite3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRIPT_DIR, "garden.db")
DEFAULT_MD = os.path.join(SCRIPT_DIR, "inbox", "gemini_2026-03-21_gaps_garden.md")
CAMPAIGN_NAME = "garden-landscape"

# Maps intel field names to the bold-header labels found in the markdown.
FIELD_HEADERS = {
    "funding_sources": "Funding sources:",
    "key_projects": "Key projects:",
    "partner_orgs": "Partners and collaborators:",
    "event_participation": "Events they run or attend:",
    "publications": "Publications, reports, or open-source tools:",
    "nordic_connection": "Nordic connection:",
    "collaboration_potential": "Collaboration potential:",
    "governance_model": "Governance model:",
    "open_source_tools": "Publications, reports, or open-source tools:",
    "community_size": "Community size:",
}

# Headers that mark the start of a recognised section (used to detect where
# one section ends and the next begins).
ALL_SECTION_HEADERS = {
    "What they do:",
    "Key people:",
    "Partners and collaborators:",
    "Events they run or attend:",
    "Publications, reports, or open-source tools:",
    "Funding sources:",
    "Key projects:",
    "Community size:",
    "Collaboration potential:",
    "Governance model:",
    "Nordic connection:",
}


def strip_citations(text: str) -> str:
    """Remove [cite: N] and [cite: N, M, ...] and [cite: N; M] references."""
    return re.sub(r"\s*\[cite:\s*[\d,;\s]+\]", "", text)


def strip_markdown_formatting(text: str) -> str:
    """Remove **bold** and *italic* markdown markers, keeping the inner text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text


def clean_value(text: str) -> str:
    """Strip citations, bold markers, collapse whitespace, and trim."""
    text = strip_citations(text)
    text = strip_markdown_formatting(text)
    # Remove leading bullet markers
    text = re.sub(r"^\s*[*\-]\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    # Remove trailing markdown horizontal rules that leaked in
    text = re.sub(r"\s*-{3,}\s*$", "", text)
    return text.strip()


def parse_section_body(lines: list[str]) -> str:
    """
    Given the lines under a **Header:** section, join bullet items with '; '
    and collapse prose paragraphs into a single string.
    """
    items: list[str] = []
    current_item = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line ends current item
            if current_item:
                items.append(current_item)
                current_item = ""
            continue
        # Skip markdown horizontal rules
        if re.match(r"^-{3,}$", stripped):
            continue

        # Bullet line (starts with * or -)
        bullet_match = re.match(r"^[*\-]\s+(.+)", stripped)
        if bullet_match:
            if current_item:
                items.append(current_item)
            current_item = bullet_match.group(1).strip()
        else:
            # Continuation or prose line
            if current_item:
                current_item += " " + stripped
            else:
                current_item = stripped

    if current_item:
        items.append(current_item)

    joined = "; ".join(clean_value(item) for item in items if clean_value(item))
    return joined


def extract_open_source_tools(section_lines: list[str]) -> str:
    """
    From the publications section, extract lines mentioning open-source tools
    or platforms specifically.
    """
    items: list[str] = []
    current_item = ""
    in_tools_area = False

    for line in section_lines:
        stripped = line.strip()
        lower = stripped.lower()

        # Detect sub-headers like **Open-source tools:**
        if "open-source tool" in lower or "open source tool" in lower or "platform" in lower:
            in_tools_area = True
            # Check if there is content after the sub-header on the same line
            colon_match = re.search(r"\*\*[^*]+\*\*\s*(.+)", stripped)
            if colon_match:
                rest = colon_match.group(1).strip()
                if rest:
                    current_item = rest
            continue

        if in_tools_area:
            # A new bold sub-header means we left the tools area
            if re.match(r"\*\*[A-Z]", stripped):
                in_tools_area = False
                if current_item:
                    items.append(current_item)
                    current_item = ""
                continue

            bullet_match = re.match(r"^[*\-]\s+(.+)", stripped)
            if bullet_match:
                if current_item:
                    items.append(current_item)
                current_item = bullet_match.group(1).strip()
            elif stripped:
                if current_item:
                    current_item += " " + stripped
                else:
                    current_item = stripped

    if current_item:
        items.append(current_item)

    # If no explicit sub-section was found, try to extract tool/platform names
    # from the entire publications section by looking for known patterns.
    # Require "open-source" or "open source" qualifier to avoid matching
    # generic uses of the word "tool".
    if not items:
        full_text = " ".join(line.strip() for line in section_lines)
        tool_match = re.search(
            r"(?:open[- ]source)\s+(?:tools?|platforms?|software)[:\s]+([^.]+)",
            full_text,
            re.IGNORECASE,
        )
        if tool_match:
            raw = tool_match.group(1)
            for part in re.split(r"[;,]", raw):
                part = clean_value(part)
                if part and len(part) > 2:
                    items.append(part)

    return "; ".join(clean_value(item) for item in items if clean_value(item))


def extract_nordic_connection(section_lines: list[str], full_actor_text: str) -> str:
    """
    Extract Nordic connection from a dedicated section, or fall back to
    scanning the full actor text for Sweden/Nordic mentions.
    """
    # If there is a dedicated section, use it
    body = parse_section_body(section_lines)
    if body:
        return body

    # Fallback: scan individual lines of the actor text for Nordic/Sweden
    # mentions.  We work line-by-line to avoid sentence-splitter artefacts
    # that merge unrelated content.
    nordic_keywords = [
        "Sweden", "Swedish", "Nordic", "Nordics", "Scandinavia",
        "Scandinavian", "Norway", "Norwegian", "Denmark", "Danish",
        "Finland", "Finnish", "Iceland", "Icelandic", "Stockholm",
        "Gothenburg", "Malmö", "Uppsala", "Linköping",
    ]
    # Skip metadata header lines
    skip_re = re.compile(
        r"^\*\*(Name|Type|Orientation|Website|Location|Scale|Maturity|Flags):\*\*"
    )

    mentions: list[str] = []
    for line in full_actor_text.splitlines():
        stripped = line.strip()
        if not stripped or skip_re.match(stripped):
            continue
        # Skip pure section headers
        if re.match(r"^\*\*[^*]+:\*\*\s*$", stripped):
            continue
        for kw in nordic_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", stripped, re.IGNORECASE):
                cleaned = clean_value(stripped)
                if cleaned and cleaned not in mentions:
                    mentions.append(cleaned)
                break
    return "; ".join(mentions)


def parse_actor_sections(md_text: str) -> list[dict]:
    """
    Split a markdown document into actor sections by ## headers.
    Returns a list of dicts with 'name' and 'raw_lines'.
    """
    actors = []
    current_name = None
    current_lines: list[str] = []

    for line in md_text.splitlines():
        header_match = re.match(r"^##\s+(.+)$", line)
        if header_match:
            if current_name is not None:
                actors.append({
                    "name": current_name.strip(),
                    "raw_lines": current_lines,
                })
            current_name = header_match.group(1).strip()
            current_lines = []
        else:
            if current_name is not None:
                current_lines.append(line)

    # Flush last actor
    if current_name is not None:
        actors.append({
            "name": current_name.strip(),
            "raw_lines": current_lines,
        })

    return actors


def extract_sections(raw_lines: list[str]) -> dict[str, list[str]]:
    """
    Given the raw lines of an actor section, split them into named sub-sections
    keyed by the bold header text (e.g. "Funding sources:").
    """
    sections: dict[str, list[str]] = {}
    current_header = None
    current_body: list[str] = []

    for line in raw_lines:
        stripped = line.strip()
        # Detect **Header:** pattern
        header_match = re.match(r"^\*\*(.+?)\*\*\s*$", stripped)
        if not header_match:
            # Also match **Header:** with content on the same line
            header_match = re.match(r"^\*\*(.+?)\*\*\s*(.*)", stripped)

        if header_match:
            candidate = header_match.group(1).strip()
            if candidate in ALL_SECTION_HEADERS:
                # Save previous section
                if current_header is not None:
                    sections[current_header] = current_body
                current_header = candidate
                current_body = []
                # If there was trailing content on the header line, include it
                rest = header_match.group(2).strip() if header_match.lastindex and header_match.lastindex >= 2 else ""
                if rest:
                    current_body.append(rest)
                continue

        if current_header is not None:
            current_body.append(line)

    # Flush last section
    if current_header is not None:
        sections[current_header] = current_body

    return sections


def fuzzy_match_actor(actor_name: str, db_actors: list[dict]) -> dict | None:
    """
    Match a markdown actor name to a DB actor. Tries:
    1. Exact case-insensitive match
    2. DB name contained in markdown name (or vice versa)
    3. First significant word match (for names like 'Naturskyddsföreningen')
    """
    name_lower = actor_name.lower().strip()

    # Pass 1: exact match
    for a in db_actors:
        if a["name"].lower().strip() == name_lower:
            return a

    # Pass 2: containment (either direction)
    for a in db_actors:
        db_lower = a["name"].lower().strip()
        if db_lower in name_lower or name_lower in db_lower:
            return a

    # Pass 3: match on the primary name part (before any parenthetical)
    primary = re.split(r"\s*[\(/]", actor_name)[0].strip().lower()
    for a in db_actors:
        db_primary = re.split(r"\s*[\(/]", a["name"])[0].strip().lower()
        if primary == db_primary:
            return a

    # Pass 4: significant word overlap (at least 2 words of 4+ chars)
    name_words = set(
        w for w in re.findall(r"[a-zà-öø-ÿ]+", name_lower) if len(w) >= 4
    )
    best_match = None
    best_overlap = 0
    for a in db_actors:
        db_words = set(
            w for w in re.findall(r"[a-zà-öø-ÿ]+", a["name"].lower()) if len(w) >= 4
        )
        overlap = len(name_words & db_words)
        if overlap > best_overlap and overlap >= 2:
            best_overlap = overlap
            best_match = a

    return best_match


def main():
    parser = argparse.ArgumentParser(
        description="Extract intel from Gemini Deep Research markdown into garden.db"
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_MD,
        help="Path to the markdown file (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview extractions without writing to the database",
    )
    args = parser.parse_args()

    md_path = args.file
    if not os.path.isabs(md_path):
        md_path = os.path.join(SCRIPT_DIR, md_path)

    if not os.path.exists(md_path):
        print(f"ERROR: File not found: {md_path}")
        sys.exit(1)

    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    # Connect to DB
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Look up campaign
    cur.execute("SELECT id FROM campaigns WHERE name = ?", (CAMPAIGN_NAME,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: Campaign '{CAMPAIGN_NAME}' not found in database.")
        conn.close()
        sys.exit(1)
    campaign_id = row["id"]

    # Load all actors
    cur.execute("SELECT id, name FROM actors")
    db_actors = [dict(r) for r in cur.fetchall()]

    # Register source file
    source_url = f"file://{md_path}"
    source_title = os.path.basename(md_path)
    source_id = None

    if not args.dry_run:
        cur.execute(
            "INSERT OR IGNORE INTO sources (url, title, description) VALUES (?, ?, ?)",
            (source_url, source_title, f"Gemini Deep Research brief: {source_title}"),
        )
        cur.execute("SELECT id FROM sources WHERE url = ?", (source_url,))
        source_id = cur.fetchone()["id"]

    # Parse markdown
    actor_sections = parse_actor_sections(md_text)
    print(f"Found {len(actor_sections)} actor sections in {source_title}")
    print(f"Campaign: {CAMPAIGN_NAME} (id={campaign_id})")
    print(f"Dry run: {args.dry_run}")
    print(f"{'=' * 60}\n")

    stats = {
        "actors_matched": 0,
        "actors_unmatched": 0,
        "intel_inserted": 0,
        "intel_skipped": 0,
        "source_actor_links": 0,
    }

    for actor_sec in actor_sections:
        md_name = actor_sec["name"]
        raw_lines = actor_sec["raw_lines"]
        full_actor_text = "\n".join(raw_lines)

        matched = fuzzy_match_actor(md_name, db_actors)
        if not matched:
            print(f"  SKIP  {md_name} — no matching actor in DB")
            stats["actors_unmatched"] += 1
            continue

        actor_id = matched["id"]
        db_name = matched["name"]
        stats["actors_matched"] += 1

        if md_name != db_name:
            print(f"  MATCH {md_name}  ->  {db_name} (id={actor_id})")
        else:
            print(f"  MATCH {db_name} (id={actor_id})")

        # Parse sub-sections
        sections = extract_sections(raw_lines)

        # Extract each intel field
        for field, header in FIELD_HEADERS.items():
            value = ""

            if field == "open_source_tools":
                # Special extraction from the publications section
                pub_lines = sections.get(header, [])
                if pub_lines:
                    value = extract_open_source_tools(pub_lines)
            elif field == "nordic_connection":
                # Use dedicated section or fall back to full-text scan
                nordic_lines = sections.get("Nordic connection:", [])
                value = extract_nordic_connection(nordic_lines, full_actor_text)
            else:
                section_lines = sections.get(header, [])
                if section_lines:
                    value = parse_section_body(section_lines)

            if not value:
                continue

            print(f"    {field}: {value[:100]}{'...' if len(value) > 100 else ''}")

            if not args.dry_run:
                try:
                    cur.execute(
                        """INSERT OR IGNORE INTO intel
                           (entity_type, entity_id, field, value, source_id,
                            confidence, campaign_id)
                           VALUES ('actor', ?, ?, ?, ?, 'extracted', ?)""",
                        (actor_id, field, value, source_id, campaign_id),
                    )
                    if cur.rowcount > 0:
                        stats["intel_inserted"] += 1
                    else:
                        stats["intel_skipped"] += 1
                except sqlite3.IntegrityError as e:
                    print(f"    WARNING: {e}")
                    stats["intel_skipped"] += 1

        # Link source to actor
        if not args.dry_run and source_id is not None:
            cur.execute(
                "INSERT OR IGNORE INTO source_actor (source_id, actor_id) VALUES (?, ?)",
                (source_id, actor_id),
            )
            if cur.rowcount > 0:
                stats["source_actor_links"] += 1

        print()

    if not args.dry_run:
        conn.commit()

    conn.close()

    # Summary
    print(f"{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Actors matched:      {stats['actors_matched']}")
    print(f"  Actors unmatched:    {stats['actors_unmatched']}")
    if not args.dry_run:
        print(f"  Intel rows inserted: {stats['intel_inserted']}")
        print(f"  Intel rows skipped:  {stats['intel_skipped']} (duplicates)")
        print(f"  Source-actor links:  {stats['source_actor_links']}")
    else:
        print(f"  (dry run — no database changes)")


if __name__ == "__main__":
    main()
