#!/usr/bin/env python3
"""
The Orbital — Weekly digest generator
Runs Monday mornings (07:30 UTC via GitHub Actions, after the daily feed update).

Finds all stories published in the past 7 days, asks Claude to synthesise them
into a weekly "Orbital Dispatch" entry, and prepends it to news.json.

Behaviour:
  - Skips if a digest for the current week (same weekStarting) already exists.
  - Skips if fewer than 2 stories were published this week (nothing to summarise).
  - Writes one new entry of kind="digest" to news.json.

Cost: ~$0.002–0.005 per run (claude-haiku). Runs once a week.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

import anthropic

NEWS_JSON = "src/data/news.json"

# ── Week helpers ──────────────────────────────────────────────────────────────

def this_monday() -> date:
    """Return the Monday of the current week (ISO week)."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def week_end(monday: date) -> date:
    return monday + timedelta(days=6)


def format_range(monday: date) -> str:
    end = week_end(monday)
    if monday.month == end.month:
        return f"{monday.day}–{end.day} {monday.strftime('%B %Y')}"
    return f"{monday.strftime('%-d %B')} – {end.strftime('%-d %B %Y')}"


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_news() -> list:
    with open(NEWS_JSON, encoding="utf-8") as f:
        return json.load(f)


def save_news(data: list) -> None:
    with open(NEWS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)[:60].rstrip("-")


# ── Claude prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the editor of The Orbital (theorbital.net), a curated feed tracking the global shift toward regenerative, participatory, ecologically grounded planetary governance.

The feed uses four lenses:
- GARDEN: tending living systems — agroecology, rewilding, rights of nature, food sovereignty, indigenous land practice
- SPACESHIP: building and modelling systems — AI, digital twins, civic tech, satellite monitoring, systems thinking
- MYSTERIES: transforming culture and consciousness — experiential futures, ritual, theatre, narrative, inner work
- ASSEMBLY: deciding together — citizens assemblies, deliberative democracy, sortition, commons governance, global governance

You write one weekly digest ("Orbital Dispatch") synthesising the week's stories into a coherent movement narrative. Your writing is thoughtful, specific, and forward-looking — not a listicle, but a genuine editorial synthesis that reveals the patterns, tensions, and momentum across the stories.

Respond ONLY with valid JSON. No preamble."""


def build_prompt(stories: list, issue_number: int, week_range: str) -> str:
    story_lines = []
    for s in stories:
        orientations = ", ".join(s.get("orientations", []))
        story_lines.append(
            f"- [{orientations}] \"{s['title']}\"\n"
            f"  Summary: {s.get('summary', '')}\n"
            f"  Insight: {s.get('insight', '')}"
        )

    stories_block = "\n\n".join(story_lines)

    return f"""Write the weekly Orbital Dispatch (Issue #{issue_number}) for the week of {week_range}.

Stories published this week ({len(stories)} total):

{stories_block}

Produce a JSON object with these fields:

{{
  "title": "A punchy, editorial headline for this week (max 80 chars) — captures the dominant theme or tension, not a generic 'week in review'",
  "summary": "2 sentences (max 220 chars total). The lead paragraph — what was the defining movement or tension this week?",
  "body": "4–5 paragraphs of editorial synthesis separated by \\n\\n. Weave the stories into a coherent narrative. Identify patterns across orientations. Name what's converging, what's in tension, what's emerging. Be specific — cite real story content. End with a forward-looking sentence about what to watch next week. Do NOT use bullet points or headers in the body.",
  "insight": "One sentence on the movement-level significance of this week — what does it tell us about where the transition is heading?",
  "highlightedSlugs": ["list", "of", "3-5", "story", "slugs", "to", "feature", "prominently"],
  "tags": ["weekly-digest", "2-3 thematic tags from the week's content, kebab-case"]
}}

Rules:
- title: editorial and specific, not generic. Example: "Rights of nature hits legislatures on three continents" not "Week in Planetary Governance"
- body: write it as a real editor would — connect dots, name tensions, show momentum
- highlightedSlugs: choose 3–5 stories that best represent the week; use the exact slugs provided
- tags: start with "weekly-digest"; add 2-3 specific thematic tags

Available slugs (use ONLY these): {json.dumps([s['slug'] for s in stories])}"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    news = load_news()

    monday = this_monday()
    week_start_str = monday.isoformat()
    cutoff = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    week_end_dt = cutoff + timedelta(days=7)

    # Check if digest for this week already exists
    existing_digest = next(
        (s for s in news
         if s.get("kind") == "digest" and s.get("weekStarting") == week_start_str),
        None,
    )
    if existing_digest:
        print(f"Digest for week {week_start_str} already exists ({existing_digest['slug']}). Skipping.")
        sys.exit(0)

    # Find stories from this week (excluding previous digests)
    week_stories = [
        s for s in news
        if s.get("kind") != "digest"
        and cutoff <= datetime.fromisoformat(s["date"]).replace(tzinfo=timezone.utc) < week_end_dt
    ]

    if len(week_stories) < 2:
        print(f"Only {len(week_stories)} stories this week — not enough to generate a digest. Skipping.")
        sys.exit(0)

    print(f"Generating digest for week of {week_start_str} ({len(week_stories)} stories)...")

    # Count existing digests to get issue number
    issue_number = sum(1 for s in news if s.get("kind") == "digest") + 1
    week_range = format_range(monday)

    # Call Claude
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(week_stories, issue_number, week_range)}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        generated = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: Claude returned invalid JSON: {e}")
        print("Raw response:", raw[:500])
        sys.exit(1)

    # Validate highlighted slugs against available slugs
    available_slugs = {s["slug"] for s in week_stories}
    highlighted = [s for s in generated.get("highlightedSlugs", []) if s in available_slugs]
    if not highlighted:
        highlighted = [s["slug"] for s in week_stories[:4]]

    # Build the digest entry
    today_str = date.today().isoformat()
    slug = f"orbital-dispatch-{issue_number:03d}"

    entry = {
        "slug": slug,
        "kind": "digest",
        "issueNumber": issue_number,
        "weekStarting": week_start_str,
        "storyCount": len(week_stories),
        "title": generated["title"],
        "date": today_str,
        "image": "",
        "imageAlt": "",
        "summary": generated["summary"],
        "body": generated["body"],
        "insight": generated["insight"],
        "highlightedSlugs": highlighted,
        "actors": [],
        "tags": generated.get("tags", ["weekly-digest"]),
        "orientations": ["GARDEN", "SPACESHIP", "MYSTERIES", "ASSEMBLY"],
        "sourceUrl": "https://theorbital.net",
    }

    # Prepend to news list
    news.insert(0, entry)
    save_news(news)

    print(f"✓ Created digest: {slug}")
    print(f"  Title: {entry['title']}")
    print(f"  Stories covered: {len(week_stories)}")
    print(f"  Highlighted: {highlighted}")


if __name__ == "__main__":
    main()
