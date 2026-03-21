#!/usr/bin/env python3
"""
Step 0 — Research Brief Generator for Garden Crawler

Generates a targeted research prompt based on DB coverage gaps.
Optionally sends it to Gemini Deep Research for automated web-grounded research.

Usage:
    python3 research.py [--campaign garden-landscape] [--focus gaps|deepen|expand]
    python3 research.py --focus expand --orientation GARDEN
    python3 research.py --focus expand --category "Regenerative Agriculture"
    python3 research.py --focus gaps --run    # Auto-research via Gemini Deep Research
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefs")
INBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")

DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"
POLL_INTERVAL = 15  # seconds


def load_env():
    """Load environment variables from .env.local."""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_campaign(cur, name):
    """Load campaign row by name."""
    cur.execute("SELECT id, name, description, intel_fields, scoring_prompt FROM campaigns WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: Campaign '{name}' not found in database.")
        cur.execute("SELECT name FROM campaigns")
        names = [r[0] for r in cur.fetchall()]
        if names:
            print(f"Available campaigns: {', '.join(names)}")
        sys.exit(1)
    return {
        "id": row[0], "name": row[1], "description": row[2],
        "intel_fields": json.loads(row[3]) if row[3] else [],
        "scoring_prompt": row[4] or "",
    }


def query_coverage(cur, orientation_filter=None, category_filter=None):
    """Return actors with coverage stats, ordered by relevance desc, coverage asc."""
    query = """
        SELECT a.id, a.name, a.relevance_score, a.type, a.website, a.description,
               a.location, a.scale, a.maturity,
               o.code as orientation,
               COUNT(DISTINCT i.id) as intel_count,
               COUNT(DISTINCT sa.source_id) as source_count
        FROM actors a
        LEFT JOIN orientations o ON o.id = a.primary_orientation_id
        LEFT JOIN intel i ON i.entity_type='actor' AND i.entity_id=a.id
        LEFT JOIN source_actor sa ON sa.actor_id=a.id
        WHERE a.relevance_score >= 3 AND a.canonical_id IS NULL
    """
    params = []
    if orientation_filter:
        query += " AND o.code = ?"
        params.append(orientation_filter.upper())
    if category_filter:
        query += """ AND a.id IN (
            SELECT ac.actor_id FROM actor_category ac
            JOIN categories c ON c.id = ac.category_id
            WHERE c.name = ?
        )"""
        params.append(category_filter)
    query += " GROUP BY a.id ORDER BY a.relevance_score DESC, intel_count ASC"
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_intel_fields(cur, actor_id):
    """Return existing intel fields for an actor."""
    cur.execute("SELECT field, value FROM intel WHERE entity_type='actor' AND entity_id=?", (actor_id,))
    return {row[0]: row[1] for row in cur.fetchall()}


def brief_gaps(cur, campaign, out_dir, orientation=None, category=None):
    """Generate a brief targeting high-relevance actors with thin coverage."""
    actors = query_coverage(cur, orientation, category)
    targets = [a for a in actors if a["intel_count"] <= 2 or a["source_count"] <= 1]
    if not targets:
        print("No coverage gaps found — all relevant actors have intel and sources.")
        return None
    targets = targets[:15]

    lines = _build_header(campaign, "gaps")
    lines.append("## Objective\n")
    lines.append("Deep-dive the following high-priority actors in The Garden landscape. For each, provide:")
    lines.append("- What they do (core mission, primary activities)")
    lines.append("- Their orientation alignment (Garden of Eden / Spaceship Earth / Eleusinian Mysteries / General Assembly)")
    lines.append("- Key people: founders, directors, advisors (names, roles, any public contact info)")
    lines.append("- Partners and collaborators (other organisations they work with)")
    lines.append("- Events they run or attend")
    lines.append("- Publications, reports, or open-source tools they've produced")
    lines.append("- Any Nordic/Swedish connections")
    lines.append("- Why they matter for planetary governance prototyping\n")

    lines.append("## Target Actors\n")
    for a in targets:
        intel = query_intel_fields(cur, a["id"])
        lines.append(f"### {a['name']} ({a['type']}, relevance: {a['relevance_score']}/5)")
        if a["description"]:
            lines.append(f"Known: {a['description']}")
        if a["website"] and a["website"] != "UNKNOWN":
            lines.append(f"Website: {a['website']}")
        if a["orientation"]:
            lines.append(f"Orientation: {a['orientation']}")
        if a["location"]:
            lines.append(f"Location: {a['location']}")
        gaps = []
        if a["intel_count"] == 0:
            gaps.append("no intel on file")
        if a["source_count"] <= 1:
            gaps.append("only 1 source")
        if gaps:
            lines.append(f"Gaps: {', '.join(gaps)}")
        if intel:
            lines.append(f"Existing intel: {json.dumps(intel)}")
        lines.append("")

    lines += _build_intel_fields(campaign)
    lines += _build_format_instructions()

    return _finalize(lines, "gaps", campaign, targets, out_dir, cur)


def brief_deepen(cur, campaign, out_dir, orientation=None, category=None):
    """Generate a brief to deepen coverage on actors that already have some intel."""
    actors = query_coverage(cur, orientation, category)
    targets = [a for a in actors if a["intel_count"] >= 2 and a["source_count"] <= 2]
    if not targets:
        targets = [a for a in actors if a["intel_count"] >= 1]
    targets = targets[:10]

    if not targets:
        print("No actors to deepen — database is empty.")
        return None

    lines = _build_header(campaign, "deepen")
    lines.append("## Objective\n")
    lines.append("These actors already have basic coverage. Go deeper:")
    lines.append("- **People**: Find key individuals — founders, directors, researchers, advisors")
    lines.append("  Include full name, role, and any public contact pathway")
    lines.append("- **Collaborations**: Who do they partner with? Co-publish? Share board members?")
    lines.append("- **Events**: Conferences, festivals, assemblies they organise or attend")
    lines.append("- **Recent developments**: New projects, funding, publications (last 12 months)")
    lines.append("- **Governance approach**: How are they structured? (cooperative, foundation, DAO, etc.)")
    lines.append("- **Nordic links**: Any connections to Sweden, Denmark, Finland, Norway, Iceland?\n")

    lines.append("## Target Actors\n")
    for a in targets:
        intel = query_intel_fields(cur, a["id"])
        lines.append(f"### {a['name']} ({a['type']}, relevance: {a['relevance_score']}/5)")
        if a["description"]:
            lines.append(f"Known: {a['description']}")
        if a["website"] and a["website"] != "UNKNOWN":
            lines.append(f"Website: {a['website']}")
        if intel:
            lines.append("Already known:")
            for field, value in intel.items():
                lines.append(f"  - {field}: {value}")
        lines.append("")

    lines += _build_intel_fields(campaign)
    lines += _build_format_instructions()

    return _finalize(lines, "deepen", campaign, targets, out_dir, cur)


def brief_expand(cur, campaign, out_dir, orientation=None, category=None):
    """Generate a landscape scan brief for discovering new actors."""
    # Get current coverage by orientation
    cur.execute("""
        SELECT o.code, o.name, COUNT(a.id) as actor_count
        FROM orientations o
        LEFT JOIN actors a ON a.primary_orientation_id = o.id AND a.canonical_id IS NULL
        GROUP BY o.id
        ORDER BY actor_count ASC
    """)
    orient_counts = [(row[0], row[1], row[2]) for row in cur.fetchall()]

    # Get current coverage by category
    cur.execute("""
        SELECT c.name, o.code, COUNT(ac.actor_id) as actor_count
        FROM categories c
        JOIN orientations o ON o.id = c.orientation_id
        LEFT JOIN actor_category ac ON ac.category_id = c.id
        GROUP BY c.id
        ORDER BY actor_count ASC
    """)
    cat_counts = [(row[0], row[1], row[2]) for row in cur.fetchall()]

    lines = _build_header(campaign, "expand")
    lines.append("## Objective\n")
    if orientation:
        orient_name = {"GARDEN": "Garden of Eden", "SPACESHIP": "Spaceship Earth",
                       "TEMPLE": "Eleusinian Mysteries", "ASSEMBLY": "General Assembly of Earth"}.get(
                           orientation.upper(), orientation)
        lines.append(f"Conduct a landscape scan for **{orient_name}** actors we may be missing.")
        lines.append(f"Focus on the {orient_name} orientation: organisations, networks, movements, and initiatives.\n")
    elif category:
        lines.append(f"Conduct a focused scan for actors in the **{category}** category.")
        lines.append(f"Find organisations, companies, networks, and movements working in this area.\n")
    else:
        lines.append("Conduct a broad landscape scan for actors we may be missing.")
        lines.append("Focus on orientations and categories that are underrepresented.\n")

    lines.append("## Current Coverage\n")
    lines.append("### By Orientation:")
    for code, name, count in orient_counts:
        lines.append(f"  - {name} ({code}): {count} actors")
    lines.append("")
    lines.append("### By Category (showing underrepresented):")
    for cat_name, orient_code, count in cat_counts[:15]:
        lines.append(f"  - {cat_name} ({orient_code}): {count} actors")
    lines.append("")

    # List known actors (don't repeat)
    cur.execute("""
        SELECT a.name FROM actors a
        WHERE a.relevance_score >= 3 AND a.canonical_id IS NULL
        ORDER BY a.relevance_score DESC
        LIMIT 50
    """)
    known = [row[0] for row in cur.fetchall()]
    if known:
        lines.append("## Actors We Already Track (do NOT repeat these)\n")
        lines.append(", ".join(known))
        lines.append("")

    lines.append("## What We Need\n")
    lines.append("For each new actor discovered, provide:")
    lines.append("- Name and website")
    lines.append("- Type: NGO, Company, Research, Government, Network, Movement")
    lines.append("- Which orientation(s) they align with")
    lines.append("- What they do (1-2 sentences)")
    lines.append("- Location and scale (Local / National / Regional / Global)")
    lines.append("- Maturity: Idea / Early / Active / Established")
    lines.append("- Relevance score (1-5) to The Garden's vision")
    lines.append("- Key person (name, role) if readily available")
    lines.append("- Why they're relevant — what makes them interesting for planetary governance prototyping")
    lines.append("")

    # Add category-specific search suggestions
    if category:
        cur.execute("SELECT search_terms FROM categories WHERE name = ?", (category,))
        row = cur.fetchone()
        if row and row[0]:
            terms = json.loads(row[0])
            lines.append(f"## Suggested search terms for {category}:\n")
            for term in terms:
                lines.append(f"- {term}")
            lines.append("")

    lines += _build_intel_fields(campaign)
    lines += _build_format_instructions()

    return _finalize(lines, "expand", campaign, [], out_dir, cur,
                     vertical=orientation or category)


def _build_header(campaign, focus):
    """Build the common header for a brief."""
    lines = [f"# Research Brief: Garden Landscape — {focus}\n"]
    lines.append("## The Garden — Context\n")
    if campaign["scoring_prompt"]:
        lines.append(campaign["scoring_prompt"])
        lines.append("")
    if campaign["description"]:
        lines.append(f"Campaign: {campaign['description']}\n")
    return lines


def _build_intel_fields(campaign):
    """Build the intel fields hints section."""
    lines = []
    if campaign["intel_fields"]:
        lines.append("## Domain-Specific Fields\n")
        lines.append("When you find information about these fields, include them explicitly:")
        for field in campaign["intel_fields"]:
            lines.append(f"- **{field}**")
        lines.append("")
    return lines


def _build_format_instructions():
    """Build output format instructions optimized for pipeline consumption."""
    return [
        "## Output Format Instructions\n",
        "Structure your response for optimal data extraction:\n",
        "- Use `## Actor Name` headers (one section per actor)",
        "- Include a structured summary per actor: name, type, orientation, website, location, scale, maturity",
        "- List key people with: full name, role, any public contact info (each on its own line)",
        "- List partners and collaborators as separate entries",
        "- Use consistent field names matching the domain-specific fields above",
        "- Avoid burying entity names in the middle of paragraphs",
        "- Prefer short, fact-dense paragraphs over long flowing prose",
        "- For each fact, cite the source URL where you found it",
        "- If you cannot find information for a field, omit it rather than guessing",
        "- Flag actors that are based in Sweden or the Nordics",
        "- Flag actors that could be direct collaborators for The Garden",
        "",
    ]


def _finalize(lines, focus, campaign, targets, out_dir, cur, vertical=None):
    """Write the brief file and record in DB. Returns (filepath, brief_db_id)."""
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_{vertical}" if vertical else ""
    filename = f"{date_str}_{focus}_garden{suffix}.md"
    filepath = os.path.join(out_dir, filename)

    prompt_text = "\n".join(lines)
    with open(filepath, "w") as f:
        f.write(prompt_text)

    # Record in briefs table
    target_names = json.dumps([t["name"] for t in targets]) if targets else "[]"
    brief_id = None
    try:
        cur.execute("""INSERT INTO briefs (filename, focus, campaign_id, actor_targets, prompt_text)
                       VALUES (?, ?, ?, ?, ?)""",
                    (filename, focus, campaign["id"], target_names, prompt_text))
        cur.connection.commit()
        brief_id = cur.lastrowid
    except sqlite3.OperationalError:
        print("WARNING: briefs table not found — run schema.sql to create it.")

    print(f"Brief saved: {filepath}")
    return filepath, prompt_text, brief_id


def run_deep_research(prompt_text, brief_filepath, brief_id, cur):
    """Send prompt to Gemini Deep Research with streaming, save result to inbox/."""
    load_env()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Add it to .env.local")
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai not installed. Run: pip3 install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    brief_basename = os.path.basename(brief_filepath)
    prompt_words = len(prompt_text.split())
    print(f"\n{'='*60}")
    print(f"  Gemini Deep Research")
    print(f"{'='*60}")
    print(f"  Agent:    {DEEP_RESEARCH_AGENT}")
    print(f"  Brief:    {brief_basename}")
    print(f"  Prompt:   {prompt_words} words")
    print(f"  Expect:   2-10 minutes")
    print(f"{'='*60}\n")

    start_time = time.time()
    interaction_id = None
    last_event_id = None
    result_text = ""
    is_complete = False
    event_count = 0
    thought_count = 0

    def ts():
        return int(time.time() - start_time)

    def process_stream(event_stream):
        nonlocal interaction_id, last_event_id, result_text, is_complete
        nonlocal event_count, thought_count
        for chunk in event_stream:
            event_count += 1

            if chunk.event_type == "interaction.start":
                interaction_id = chunk.interaction.id
                print(f"[{ts():3d}s] Connected — interaction {interaction_id}")

            if chunk.event_id:
                last_event_id = chunk.event_id

            if chunk.event_type == "content.delta":
                if chunk.delta.type == "text":
                    result_text += chunk.delta.text
                    print(chunk.delta.text, end="", flush=True)
                elif chunk.delta.type == "thought_summary":
                    thought_count += 1
                    print(f"\n[{ts():3d}s] Thinking ({thought_count}): {chunk.delta.content.text}", flush=True)

            elif chunk.event_type == "interaction.complete":
                is_complete = True
                print(f"\n\n{'='*60}")
                print(f"  Research complete  ({ts()}s, {event_count} events, {thought_count} thoughts)")
                print(f"  Result: {len(result_text)} chars, {len(result_text.split())} words")
                print(f"{'='*60}")

            elif chunk.event_type == "interaction.status_update":
                status = getattr(chunk, 'status', None)
                print(f"[{ts():3d}s] Status: {status or 'unknown'}", flush=True)

            elif chunk.event_type in ("content.start", "content.stop"):
                pass

            elif chunk.event_type == "error":
                is_complete = True
                error_msg = getattr(chunk, 'error', 'unknown')
                print(f"\n[{ts():3d}s] ERROR: {error_msg}")

            else:
                try:
                    attrs = {k: v for k, v in vars(chunk).items()
                             if v is not None and k not in ('event_id', 'event_type')}
                    if attrs:
                        print(f"\n[{ts():3d}s] {chunk.event_type}: {json.dumps(attrs, default=str)}", flush=True)
                except Exception:
                    print(f"\n[{ts():3d}s] {chunk.event_type}: {chunk}", flush=True)

    # Initial streaming request
    print(f"[{ts():3d}s] Connecting to Gemini Deep Research...")
    try:
        stream = client.interactions.create(
            input=prompt_text,
            agent=DEEP_RESEARCH_AGENT,
            background=True,
            stream=True,
            agent_config={
                "type": "deep-research",
                "thinking_summaries": "auto",
            },
        )
        process_stream(stream)
    except Exception as e:
        print(f"\n[{ts():3d}s] Stream interrupted: {e}")

    # Reconnection loop if stream dropped before completion
    reconnect_attempts = 0
    while not is_complete and interaction_id:
        reconnect_attempts += 1
        print(f"\n[{ts():3d}s] Reconnecting (attempt {reconnect_attempts})...")
        time.sleep(2)
        try:
            resume_stream = client.interactions.get(
                id=interaction_id,
                stream=True,
                last_event_id=last_event_id,
            )
            process_stream(resume_stream)
        except Exception as e:
            print(f"[{ts():3d}s] Reconnection failed: {e}")
            if reconnect_attempts >= 10:
                print(f"[{ts():3d}s] Max reconnection attempts reached.")
                break

    if not result_text:
        if interaction_id:
            print(f"[{ts():3d}s] Fetching result via non-streaming fallback...")
            interaction = client.interactions.get(interaction_id)
            print(f"[{ts():3d}s] Interaction status: {interaction.status}")
            if interaction.status == "completed" and interaction.outputs:
                result_text = interaction.outputs[-1].text
                print(f"[{ts():3d}s] Got {len(result_text)} chars from fallback")

    if not result_text:
        print(f"\n[{ts():3d}s] ERROR: No result text received.")
        sys.exit(1)

    # Save to inbox/
    os.makedirs(INBOX_DIR, exist_ok=True)
    brief_stem = os.path.basename(brief_filepath).replace(".md", "")
    inbox_filename = f"gemini_{brief_stem}.md"
    inbox_path = os.path.join(INBOX_DIR, inbox_filename)
    with open(inbox_path, "w") as f:
        f.write(result_text)

    print(f"\nResult saved: {inbox_path}")
    print(f"Next: python3 chunker.py {inbox_path}")

    # Update brief record
    if brief_id:
        try:
            cur.execute("UPDATE briefs SET result_file = ?, model = ? WHERE id = ?",
                        (inbox_filename, DEEP_RESEARCH_AGENT, brief_id))
            cur.connection.commit()
        except sqlite3.OperationalError:
            pass

    return inbox_path


def main():
    parser = argparse.ArgumentParser(description="Generate a research brief for the Garden landscape")
    parser.add_argument("--campaign", default="garden-landscape", help="Campaign name (default: garden-landscape)")
    parser.add_argument("--focus", default="gaps", choices=["gaps", "deepen", "expand"],
                        help="Brief focus: gaps (default), deepen, or expand")
    parser.add_argument("--orientation", default=None,
                        help="Filter by orientation: GARDEN, SPACESHIP, TEMPLE, ASSEMBLY")
    parser.add_argument("--category", default=None,
                        help="Filter by category name (e.g. 'Regenerative Agriculture')")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory (default: briefs/)")
    parser.add_argument("--run", action="store_true",
                        help="Send brief to Gemini Deep Research and save result to inbox/")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    campaign = get_campaign(cur, args.campaign)

    if args.focus == "gaps":
        result = brief_gaps(cur, campaign, args.out, args.orientation, args.category)
    elif args.focus == "deepen":
        result = brief_deepen(cur, campaign, args.out, args.orientation, args.category)
    elif args.focus == "expand":
        result = brief_expand(cur, campaign, args.out, args.orientation, args.category)

    if not result:
        conn.close()
        return

    filepath, prompt_text, brief_id = result

    if args.run:
        run_deep_research(prompt_text, filepath, brief_id, cur)
    else:
        print(f"\nPaste this prompt into a web-grounded LLM, save the response to inbox/.")
        print(f"Or re-run with --run to auto-research via Gemini Deep Research.")

    conn.close()


if __name__ == "__main__":
    main()
