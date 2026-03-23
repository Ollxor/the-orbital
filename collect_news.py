#!/usr/bin/env python3
"""
News Collector for Garden Crawler

Generates news research briefs and collects landscape news stories.
Stories are saved as Astro-compatible markdown files in web/src/content/news/.

Usage:
    python3 collect_news.py                      # Generate news research brief
    python3 collect_news.py --run                # Brief + auto-research via Gemini
    python3 collect_news.py --save --title "..." # Manually save a news story
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")
NEWS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "src", "content", "news")
BRIEFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefs")
INBOX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")

DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"


def load_env():
    """Load environment variables from .env.local."""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_tracked_actors(cur):
    """Return high-relevance actors for news monitoring."""
    cur.execute("""
        SELECT a.id, a.name, a.type, a.website, a.domain,
               o.code as orientation
        FROM actors a
        LEFT JOIN orientations o ON o.id = a.primary_orientation_id
        WHERE a.relevance_score >= 3 AND a.canonical_id IS NULL
        ORDER BY a.relevance_score DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_tracked_projects(cur):
    """Return projects for news monitoring."""
    cur.execute("""
        SELECT id, name, website, geography, stage
        FROM projects
        ORDER BY name
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def existing_news_slugs():
    """Return set of existing news file slugs to avoid duplicates."""
    os.makedirs(NEWS_DIR, exist_ok=True)
    return {f.replace('.md', '') for f in os.listdir(NEWS_DIR) if f.endswith('.md')}


def generate_brief(cur):
    """Generate a news research brief for Gemini Deep Research."""
    actors = get_tracked_actors(cur)
    projects = get_tracked_projects(cur)

    lines = [
        "# News Research Brief: Garden Landscape\n",
        "## Objective\n",
        "Find recent news, announcements, publications, and developments (last 3 months)",
        "related to the following organisations and projects in the planetary governance landscape.\n",
        "For each news item found, provide:",
        "- **Title**: A clear, descriptive headline",
        "- **Date**: Publication date (YYYY-MM-DD)",
        "- **Summary**: 2-3 sentence summary of why this matters for planetary governance",
        "- **Source URL**: Where you found it",
        "- **Related actors**: Which tracked organisations are involved (use exact names below)",
        "- **Related projects**: Which tracked projects are involved (use exact names below)",
        "- **Tags**: 2-4 keyword tags (e.g., governance, funding, research, nordic, climate, democracy)\n",
        "## Quality Criteria\n",
        "- Prioritise substantive developments: new publications, policy changes, funding rounds,",
        "  major events, partnerships, governance experiments",
        "- Skip routine social media posts, minor blog updates, or promotional content",
        "- Focus on items relevant to planetary governance, democratic innovation,",
        "  ecological stewardship, or transformative practice",
        "- If an actor has been quiet, note that rather than fabricating news\n",
        "## Tracked Actors\n",
    ]

    for a in actors:
        website = f" ({a['website']})" if a['website'] and a['website'] != 'UNKNOWN' else ''
        lines.append(f"- **{a['name']}** [{a['type']}, {a['orientation'] or '?'}]{website}")

    lines.append("\n## Tracked Projects\n")
    for p in projects:
        website = f" ({p['website']})" if p.get('website') else ''
        lines.append(f"- **{p['name']}**{website}")

    lines.extend([
        "\n## Output Format\n",
        "Structure each news item as a separate section:\n",
        "```",
        "## [Title]",
        "- Date: YYYY-MM-DD",
        "- Actors: Actor Name 1, Actor Name 2",
        "- Projects: Project Name 1",
        "- Tags: tag1, tag2, tag3",
        "- Source: https://...",
        "",
        "Summary paragraph here.",
        "```\n",
        "Find 10-20 news items. Focus on quality over quantity.",
        "If you find fewer than 5 items, note which actors/areas had no recent news.",
    ])

    return "\n".join(lines)


def slugify(text):
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def resolve_actor_ids(cur, names):
    """Resolve actor names to IDs, fuzzy matching."""
    ids = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        cur.execute(
            "SELECT id FROM actors WHERE name = ? AND canonical_id IS NULL",
            (name,)
        )
        row = cur.fetchone()
        if row:
            ids.append(row[0])
        else:
            # Fuzzy: try LIKE
            cur.execute(
                "SELECT id FROM actors WHERE name LIKE ? AND canonical_id IS NULL LIMIT 1",
                (f"%{name}%",)
            )
            row = cur.fetchone()
            if row:
                ids.append(row[0])
    return ids


def resolve_project_ids(cur, names):
    """Resolve project names to IDs."""
    ids = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            ids.append(row[0])
        else:
            cur.execute("SELECT id FROM projects WHERE name LIKE ? LIMIT 1", (f"%{name}%",))
            row = cur.fetchone()
            if row:
                ids.append(row[0])
    return ids


def save_news_story(title, date_str, summary, body, actor_ids, project_ids, tags):
    """Save a news story as an Astro markdown file."""
    os.makedirs(NEWS_DIR, exist_ok=True)

    slug = slugify(title)
    existing = existing_news_slugs()
    if slug in existing:
        slug = f"{slug}-{date_str}"
    if slug in existing:
        print(f"  Skipping duplicate: {slug}")
        return None

    frontmatter = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"date: {date_str}",
        f'summary: "{summary.replace(chr(34), chr(39))}"',
        f"actors: [{', '.join(str(i) for i in actor_ids)}]",
        f"projects: [{', '.join(str(i) for i in project_ids)}]",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]

    filepath = os.path.join(NEWS_DIR, f"{slug}.md")
    with open(filepath, "w") as f:
        f.write("\n".join(frontmatter))
        if body:
            f.write(body)
            f.write("\n")

    print(f"  Saved: {filepath}")
    return filepath


def parse_research_result(cur, result_text):
    """Parse Gemini research result into individual news stories."""
    stories = []
    # Split on ## headings
    sections = re.split(r'\n##\s+', result_text)

    for section in sections[1:]:  # Skip preamble
        lines = section.strip().split('\n')
        if not lines:
            continue

        title = lines[0].strip().strip('#').strip()
        if not title or len(title) < 10:
            continue

        date_str = datetime.now().strftime("%Y-%m-%d")
        actor_names = []
        project_names = []
        tags = []
        summary = ""
        body_lines = []
        parsing_body = False

        for line in lines[1:]:
            line_lower = line.strip().lower()
            if line_lower.startswith('- date:') or line_lower.startswith('date:'):
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    date_str = date_match.group(1)
            elif line_lower.startswith('- actors:') or line_lower.startswith('actors:'):
                names = line.split(':', 1)[1].strip()
                actor_names = [n.strip() for n in names.split(',')]
            elif line_lower.startswith('- projects:') or line_lower.startswith('projects:'):
                names = line.split(':', 1)[1].strip()
                project_names = [n.strip() for n in names.split(',')]
            elif line_lower.startswith('- tags:') or line_lower.startswith('tags:'):
                tag_str = line.split(':', 1)[1].strip()
                tags = [t.strip().lower() for t in tag_str.split(',')]
            elif line_lower.startswith('- source:') or line_lower.startswith('source:'):
                continue  # Skip source URLs for now
            elif line.strip():
                if not summary:
                    summary = line.strip()
                else:
                    body_lines.append(line)

        if not summary:
            summary = title

        actor_ids = resolve_actor_ids(cur, actor_names)
        project_ids = resolve_project_ids(cur, project_names)

        stories.append({
            'title': title,
            'date': date_str,
            'summary': summary[:300],
            'body': '\n'.join(body_lines).strip(),
            'actor_ids': actor_ids,
            'project_ids': project_ids,
            'tags': tags[:5] if tags else ['landscape'],
        })

    return stories


def run_deep_research(prompt_text):
    """Send prompt to Gemini Deep Research, return result text."""
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

    start_time = time.time()
    ts = lambda: int(time.time() - start_time)

    print(f"\n{'='*60}")
    print(f"  News Collection via Gemini Deep Research")
    print(f"{'='*60}")

    interaction_id = None
    last_event_id = None
    result_text = ""
    is_complete = False

    def process_stream(event_stream):
        nonlocal interaction_id, last_event_id, result_text, is_complete
        for chunk in event_stream:
            if chunk.event_type == "interaction.start":
                interaction_id = chunk.interaction.id
                print(f"[{ts():3d}s] Connected — {interaction_id}")
            if chunk.event_id:
                last_event_id = chunk.event_id
            if chunk.event_type == "content.delta":
                if chunk.delta.type == "text":
                    result_text += chunk.delta.text
                    print(chunk.delta.text, end="", flush=True)
                elif chunk.delta.type == "thought_summary":
                    print(f"\n[{ts():3d}s] Thinking: {chunk.delta.content.text}", flush=True)
            elif chunk.event_type == "interaction.complete":
                is_complete = True
                print(f"\n\n[{ts():3d}s] Research complete")
            elif chunk.event_type == "error":
                is_complete = True
                print(f"\n[{ts():3d}s] ERROR: {getattr(chunk, 'error', 'unknown')}")

    print(f"[{ts():3d}s] Connecting...")
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

    # Reconnection loop
    reconnect_attempts = 0
    while not is_complete and interaction_id:
        reconnect_attempts += 1
        if reconnect_attempts > 10:
            break
        print(f"\n[{ts():3d}s] Reconnecting ({reconnect_attempts})...")
        time.sleep(2)
        try:
            resume = client.interactions.get(
                id=interaction_id, stream=True, last_event_id=last_event_id,
            )
            process_stream(resume)
        except Exception as e:
            print(f"[{ts():3d}s] Reconnection failed: {e}")

    if not result_text and interaction_id:
        print(f"[{ts():3d}s] Fetching via fallback...")
        interaction = client.interactions.get(interaction_id)
        if interaction.status == "completed" and interaction.outputs:
            result_text = interaction.outputs[-1].text

    return result_text


def main():
    parser = argparse.ArgumentParser(description="Collect news for the Garden landscape")
    parser.add_argument("--run", action="store_true",
                        help="Auto-research via Gemini Deep Research")
    parser.add_argument("--save", action="store_true",
                        help="Manually save a single news story")
    parser.add_argument("--title", default=None, help="Story title (with --save)")
    parser.add_argument("--date", default=None, help="Story date YYYY-MM-DD (with --save)")
    parser.add_argument("--summary", default=None, help="Story summary (with --save)")
    parser.add_argument("--actors", default="", help="Comma-separated actor names (with --save)")
    parser.add_argument("--projects", default="", help="Comma-separated project names (with --save)")
    parser.add_argument("--tags", default="", help="Comma-separated tags (with --save)")
    parser.add_argument("--parse", default=None,
                        help="Parse an existing inbox file into news stories")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    if args.save:
        if not args.title:
            print("ERROR: --title required with --save")
            sys.exit(1)
        date_str = args.date or datetime.now().strftime("%Y-%m-%d")
        summary = args.summary or args.title
        actor_ids = resolve_actor_ids(cur, args.actors.split(',')) if args.actors else []
        project_ids = resolve_project_ids(cur, args.projects.split(',')) if args.projects else []
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else ['landscape']
        save_news_story(args.title, date_str, summary, "", actor_ids, project_ids, tags)
        conn.close()
        return

    if args.parse:
        if not os.path.exists(args.parse):
            print(f"ERROR: File not found: {args.parse}")
            sys.exit(1)
        with open(args.parse) as f:
            result_text = f.read()
        stories = parse_research_result(cur, result_text)
        print(f"\nParsed {len(stories)} news stories")
        for story in stories:
            save_news_story(
                story['title'], story['date'], story['summary'], story['body'],
                story['actor_ids'], story['project_ids'], story['tags'],
            )
        print(f"\nDone. Rebuild web: cd web && bun run build")
        conn.close()
        return

    # Generate brief
    brief_text = generate_brief(cur)
    os.makedirs(BRIEFS_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    brief_path = os.path.join(BRIEFS_DIR, f"{date_str}_news_landscape.md")
    with open(brief_path, "w") as f:
        f.write(brief_text)
    print(f"Brief saved: {brief_path}")

    if args.run:
        result_text = run_deep_research(brief_text)
        if not result_text:
            print("ERROR: No result received.")
            sys.exit(1)

        # Save raw result
        os.makedirs(INBOX_DIR, exist_ok=True)
        inbox_path = os.path.join(INBOX_DIR, f"gemini_{date_str}_news_landscape.md")
        with open(inbox_path, "w") as f:
            f.write(result_text)
        print(f"\nRaw result saved: {inbox_path}")

        # Parse into news stories
        stories = parse_research_result(cur, result_text)
        print(f"\nParsed {len(stories)} news stories")
        for story in stories:
            save_news_story(
                story['title'], story['date'], story['summary'], story['body'],
                story['actor_ids'], story['project_ids'], story['tags'],
            )
        print(f"\nDone. Rebuild web: cd web && bun run build")
    else:
        print(f"\nPaste this brief into a web-grounded LLM, save response to inbox/.")
        print(f"Then: python3 collect_news.py --parse inbox/your_result.md")
        print(f"Or: python3 collect_news.py --run  (auto-research via Gemini)")

    conn.close()


if __name__ == "__main__":
    main()
