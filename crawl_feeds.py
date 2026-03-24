#!/usr/bin/env python3
"""
Feed Crawler for Garden Crawler

Crawls RSS/Atom feeds linked to tracked actors and projects,
then uses Claude Sonnet to extract, format, and enrich news articles.

Saves articles as Astro-compatible markdown in web/src/content/news/.

Usage:
    python3 crawl_feeds.py                    # Discover feeds + crawl + extract
    python3 crawl_feeds.py --discover-only    # Only discover and register RSS feeds
    python3 crawl_feeds.py --crawl-only       # Only crawl already-registered feeds
    python3 crawl_feeds.py --limit 5          # Limit to N feeds
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import anthropic
import feedparser
import httpx
from bs4 import BeautifulSoup

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "garden.db")
NEWS_DIR = os.path.join(BASE_DIR, "web", "src", "content", "news")
IMAGES_DIR = os.path.join(BASE_DIR, "web", "public", "images", "news")
ENV_FILE = os.path.join(BASE_DIR, ".env.local")

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
HTTP_TIMEOUT = 15
MAX_ARTICLES_PER_FEED = 10
ARTICLE_MAX_CHARS = 12000  # max chars of page content sent to Claude


# ─── Env ──────────────────────────────────────────────────────────────────────

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


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def fetch_url(url, timeout=HTTP_TIMEOUT):
    """Fetch URL with error handling. Returns (content, content_type) or (None, None)."""
    headers = {
        "User-Agent": "GardenCrawler/1.0 (news feed aggregator; +https://github.com/garden-crawler)"
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text, resp.headers.get("content-type", "")
    except Exception as e:
        print(f"    FETCH ERROR {url}: {e}")
        return None, None


def download_image(url, slug, min_bytes=5000):
    """Download image and save to public/images/news/. Returns relative path or None.
    Rejects images smaller than min_bytes (likely placeholders/icons)."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    try:
        headers = {
            "User-Agent": "GardenCrawler/1.0 (news feed aggregator)"
        }
        with httpx.Client(follow_redirects=True, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "image" not in ct:
                return None
            if len(resp.content) < min_bytes:
                return None  # Too small — likely icon/placeholder
            ext = ".jpg"
            if "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            elif "gif" in ct:
                ext = ".gif"
            filename = f"{slug}{ext}"
            filepath = os.path.join(IMAGES_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return f"/images/news/{filename}"
    except Exception as e:
        print(f"    IMAGE ERROR {url}: {e}")
        return None


def extract_page_images(url, html):
    """Extract candidate hero images from an article page. Returns list of absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    images = []
    seen = set()

    # 1. og:image — usually the editorial pick
    og_tag = soup.find("meta", property="og:image")
    if og_tag and og_tag.get("content"):
        img_url = urljoin(url, og_tag["content"])
        if img_url not in seen:
            images.append(img_url)
            seen.add(img_url)

    # 2. twitter:image
    tw_tag = soup.find("meta", attrs={"name": "twitter:image"})
    if tw_tag and tw_tag.get("content"):
        img_url = urljoin(url, tw_tag["content"])
        if img_url not in seen:
            images.append(img_url)
            seen.add(img_url)

    # 3. Images from article/main content area
    main = soup.find("article") or soup.find("main") or soup.find("body")
    if main:
        for img in main.find_all("img", src=True):
            src = img.get("src", "")
            if not src:
                continue
            img_url = urljoin(url, src)
            # Skip tiny icons, tracking pixels, avatars, logos
            skip_patterns = ["logo", "icon", "avatar", "pixel", "tracking", "badge", "button",
                             "spinner", "loader", "1x1", "spacer", "ad-", "banner-ad"]
            if any(p in img_url.lower() for p in skip_patterns):
                continue
            if img_url not in seen:
                images.append(img_url)
                seen.add(img_url)

    return images[:8]  # Cap at 8 candidates


# ─── Feed discovery ───────────────────────────────────────────────────────────

COMMON_FEED_PATHS = ["/feed", "/feed/", "/rss", "/atom.xml", "/feed.xml", "/blog/feed"]


def discover_feeds_from_html(url, html):
    """Extract RSS/Atom feed URLs from HTML link tags."""
    feeds = []
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("link", type=True):
        link_type = link.get("type", "")
        if "rss" in link_type or "atom" in link_type:
            href = link.get("href", "")
            if href and "oembed" not in href and "xmlrpc" not in href:
                feeds.append(urljoin(url, href))
    return feeds


def _is_feed_content(content, ct):
    """Check if response looks like an RSS/Atom feed."""
    if ct and ("xml" in ct or "rss" in ct or "atom" in ct):
        return True
    if content:
        start = content.strip()[:500]
        if start.startswith("<?xml") or "<rss" in start or "<feed" in start:
            return True
    return False


def discover_feeds_for_url(base_url):
    """Try to find RSS/Atom feeds for a website. HTML link discovery first, then probe a few paths."""
    if not base_url:
        return []

    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    base_url = base_url.rstrip("/")

    feeds = []

    # 1. Check HTML for <link> tags — this is the most reliable method
    html, ct = fetch_url(base_url)
    if html and "html" in (ct or ""):
        feeds.extend(discover_feeds_from_html(base_url, html))

    # 2. If HTML link discovery found feeds, skip probing
    if feeds:
        return list(dict.fromkeys(feeds))

    # 3. Probe only a few common paths (quietly, suppress errors)
    for path in COMMON_FEED_PATHS:
        probe_url = f"{base_url}{path}"
        try:
            with httpx.Client(follow_redirects=True, timeout=6) as client:
                resp = client.get(probe_url, headers={
                    "User-Agent": "GardenCrawler/1.0 (news feed aggregator)"
                })
                if resp.status_code == 200 and _is_feed_content(resp.text, resp.headers.get("content-type", "")):
                    feeds.append(probe_url)
                    break  # Found one, stop probing
        except Exception:
            continue

    return list(dict.fromkeys(feeds))


# ─── Database helpers ─────────────────────────────────────────────────────────

def ensure_feeds_table(conn):
    """Create feeds table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER REFERENCES sources(id),
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            feed_type TEXT,
            last_crawled DATETIME,
            entry_count INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feeds_source ON feeds(source_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feeds_active ON feeds(active)")
    conn.commit()


def get_monitored_sources(cur):
    """Get sources marked for monitoring, with linked actor/project IDs."""
    cur.execute("""
        SELECT s.id, s.url, s.title
        FROM sources s
        WHERE s.monitor = 1
    """)
    sources = []
    for row in cur.fetchall():
        sid, url, title = row
        # Get linked actors
        cur.execute("SELECT actor_id FROM source_actor WHERE source_id = ?", (sid,))
        actor_ids = [r[0] for r in cur.fetchall()]
        # Get linked projects
        cur.execute("SELECT project_id FROM source_project WHERE source_id = ?", (sid,))
        project_ids = [r[0] for r in cur.fetchall()]
        sources.append({
            "id": sid,
            "url": url,
            "title": title,
            "actor_ids": actor_ids,
            "project_ids": project_ids,
        })
    return sources


def get_all_actor_websites(cur):
    """Get websites of high-relevance actors for feed discovery."""
    cur.execute("""
        SELECT a.id, a.name, a.website
        FROM actors a
        WHERE a.relevance_score >= 3 AND a.canonical_id IS NULL AND a.website IS NOT NULL
        ORDER BY a.relevance_score DESC
    """)
    return [{"id": r[0], "name": r[1], "website": r[2]} for r in cur.fetchall()]


def register_feed(conn, cur, feed_url, source_id=None, title=None, feed_type=None):
    """Register a discovered feed in the database."""
    try:
        cur.execute(
            "INSERT OR IGNORE INTO feeds (url, source_id, title, feed_type) VALUES (?, ?, ?, ?)",
            (feed_url, source_id, title, feed_type),
        )
        conn.commit()
        if cur.rowcount > 0:
            return cur.lastrowid
    except Exception:
        pass
    return None


def get_active_feeds(cur):
    """Get all active feeds with their linked actors/projects."""
    cur.execute("""
        SELECT f.id, f.url, f.title, f.source_id, f.last_crawled
        FROM feeds f
        WHERE f.active = 1
    """)
    feeds = []
    for row in cur.fetchall():
        fid, url, title, source_id, last_crawled = row
        actor_ids = []
        project_ids = []
        if source_id:
            cur.execute("SELECT actor_id FROM source_actor WHERE source_id = ?", (source_id,))
            actor_ids = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT project_id FROM source_project WHERE source_id = ?", (source_id,))
            project_ids = [r[0] for r in cur.fetchall()]
        feeds.append({
            "id": fid,
            "url": url,
            "title": title,
            "source_id": source_id,
            "last_crawled": last_crawled,
            "actor_ids": actor_ids,
            "project_ids": project_ids,
        })
    return feeds


# ─── Feed parsing ─────────────────────────────────────────────────────────────

def parse_feed(feed_url):
    """Parse RSS/Atom feed and return entries."""
    feed = feedparser.parse(feed_url)
    if feed.bozo and not feed.entries:
        return None, []

    title = feed.feed.get("title", "Unknown Feed")
    entries = []

    for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d")

        # Get best content
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary or ""

        # Extract image from content or media
        image_url = None
        if hasattr(entry, "media_content") and entry.media_content:
            for media in entry.media_content:
                if media.get("medium") == "image" or "image" in media.get("type", ""):
                    image_url = media.get("url")
                    break
        if not image_url and hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get("url")
        if not image_url and content:
            soup = BeautifulSoup(content, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                image_url = img["src"]

        # Clean HTML from content for text extraction
        if content:
            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text(separator="\n", strip=True)

        entries.append({
            "title": entry.get("title", "Untitled"),
            "url": entry.get("link", ""),
            "date": pub_date,
            "content": content[:ARTICLE_MAX_CHARS],
            "image_url": image_url,
        })

    return title, entries


def fetch_article_page(url):
    """Fetch full article page. Returns (text_content, [image_urls]) or (None, [])."""
    html, ct = fetch_url(url)
    if not html:
        return None, []

    # Extract candidate images before we strip the HTML
    page_images = extract_page_images(url, html)

    soup = BeautifulSoup(html, "html.parser")

    # Extract main content - try article, main, then body
    main = soup.find("article") or soup.find("main") or soup.find("body")
    if not main:
        return None, page_images

    # Remove nav, footer, scripts, styles
    for tag in main.find_all(["nav", "footer", "script", "style", "aside", "header"]):
        tag.decompose()

    text = main.get_text(separator="\n", strip=True)
    return text[:ARTICLE_MAX_CHARS], page_images


# ─── Claude extraction ───────────────────────────────────────────────────────

TONE_GUIDE = """
TONE & STYLE (match these reference articles exactly):
- Analytical but warm, never corporate. Write like an informed colleague sharing what matters.
- Use em dashes for parenthetical asides — they're part of the voice.
- Always connect the news to broader themes: planetary governance, ecological stewardship, democratic innovation, transformative practice.
- Where relevant, note connections to The Overview's thesis: that governance systems must be felt and tested, not merely debated.
- Be concise: 2-4 paragraphs, no filler. Every sentence should earn its place.
- Name specific facts, numbers, places. Avoid vague generalities.
- Do NOT be promotional or breathless. Maintain critical distance while showing genuine interest.

Example tone:
"The tribunal, which operates as a form of governance performance — part legal proceeding, part public ritual — heard cases involving deep-sea mining in the Pacific, algorithmic water allocation in the Colorado Basin, and satellite-detected deforestation in the Congo."
""".strip()


def extract_article_with_claude(client, entry, feed_title, actor_ids, project_ids, actor_names_map):
    """Use Claude Sonnet to extract, rewrite, and pick the best image from a news article."""

    # Build actor context
    actor_context = ""
    if actor_ids:
        names = [actor_names_map.get(aid, f"Actor #{aid}") for aid in actor_ids]
        actor_context = f"This feed is linked to: {', '.join(names)}"

    # Fetch full article page — get text AND all candidate images
    full_text = entry["content"]
    page_images = []
    if entry["url"]:
        page_text, page_images = fetch_article_page(entry["url"])
        if page_text and len(page_text) > len(full_text):
            full_text = page_text

    # Also include any image from the RSS entry itself
    if entry.get("image_url") and entry["image_url"] not in page_images:
        page_images.insert(0, entry["image_url"])

    # Build the message content — text + images for vision
    content_blocks = []

    # Filter images to ones we can verify are fetchable (skip data: URIs, etc)
    valid_images = [u for u in page_images if u.startswith("http")]

    # Add images via URL for Claude vision to evaluate
    image_list_text = ""
    if valid_images:
        for i, img_url in enumerate(valid_images):
            content_blocks.append({
                "type": "image",
                "source": {"type": "url", "url": img_url},
            })
        image_list_text = f"""

CANDIDATE IMAGES: {len(valid_images)} images are attached above (numbered 1-{len(valid_images)}).
Pick the single best image for a hero/cover photo. Choose the most visually striking,
editorially relevant photograph — landscapes, people, nature, events.
AVOID logos, infographics, headshots, screenshots, charts, or generic stock imagery.
If none of the images are suitable as hero photography, set "bestImageIndex" to null."""
        page_images = valid_images  # use filtered list for index resolution

    prompt = f"""You are a news editor for a planetary governance research project called "The Overview".
Rewrite this news article in The Overview's editorial voice and pick the best hero image.

{TONE_GUIDE}

FEED: {feed_title}
ARTICLE TITLE: {entry['title']}
ARTICLE URL: {entry['url']}
PUBLISHED: {entry.get('date', 'Unknown')}
{actor_context}

ARTICLE CONTENT:
{full_text}
{image_list_text}

Return a JSON object with these fields:
- "title": A clear, concise headline in The Overview's voice (max 100 chars)
- "date": Publication date as YYYY-MM-DD (use {datetime.now().strftime('%Y-%m-%d')} if unknown)
- "summary": 2-3 sentence summary connecting this to planetary governance themes (max 300 chars)
- "whyItMatters": One sentence (max 200 chars) connecting this story to the larger pattern of planetary governance. This is the editorial voice of The Overview — the thing that turns a news aggregator into a publication with a perspective. Examples: "Regenerative agriculture only scales when the financial architecture supports the people doing the work." or "Governance that shows up in a shopping mall becomes culture."
- "body": 2-4 paragraphs rewritten in The Overview's editorial voice. Not a summary — a proper rewrite. Include key facts, quotes if notable, and connect to broader themes.
- "tags": Array of 2-5 lowercase keyword tags (e.g. governance, climate, funding, nordic, research, democratic-innovation, governance-tech, rights-of-nature)
- "imageAlt": Descriptive alt text for the chosen hero image (max 120 chars)
- "bestImageIndex": 1-based index of the best hero image from the candidates, or null if none are suitable
- "relevant": Boolean - is this relevant to planetary governance, ecological stewardship, democratic innovation, or transformative practice?

Return ONLY valid JSON, no markdown fences."""

    content_blocks.append({"type": "text", "text": prompt})

    def _strip_markdown_fences(text):
        """Strip markdown code fences wrapping JSON, handling multiline cases."""
        # Match ```json or ``` at start, with optional whitespace/newlines, and ``` at end
        stripped = re.sub(r"^\s*```(?:json)?\s*\n?", "", text)
        stripped = re.sub(r"\n?\s*```\s*$", "", stripped)
        return stripped.strip()

    def _call_claude(blocks):
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": blocks}],
        )
        if not response.content:
            raise ValueError("Empty response from Claude")
        text = response.content[0].text.strip()
        text = _strip_markdown_fences(text)
        return json.loads(text)

    def _call_claude_with_retry(blocks):
        """Call Claude, retrying once with corrective instruction on JSON parse failure."""
        try:
            return _call_claude(blocks)
        except json.JSONDecodeError as e:
            print(f"      JSON parse error, retrying with correction prompt: {e}")
            # Build retry messages: original user message + assistant's bad response + correction
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": blocks},
                    {"role": "assistant", "content": "(invalid JSON response)"},
                    {"role": "user", "content": "Your previous response was not valid JSON. Return ONLY a valid JSON object, no extra text."},
                ],
            )
            retry_text = response.content[0].text.strip()
            retry_text = _strip_markdown_fences(retry_text)
            return json.loads(retry_text)

    try:
        result = _call_claude_with_retry(content_blocks)
    except (anthropic.APIError, ValueError) as e:
        # Likely an image URL Claude couldn't fetch or empty response — retry without images
        if valid_images:
            print(f"      Retrying without images ({e})")
            text_only = [b for b in content_blocks if b.get("type") == "text"]
            try:
                result = _call_claude_with_retry(text_only)
                result["bestImageIndex"] = None
            except (anthropic.APIError, ValueError, json.JSONDecodeError) as e2:
                print(f"    CLAUDE ERROR (retry): {e2}")
                return None
        else:
            print(f"    CLAUDE ERROR: {e}")
            return None
    except json.JSONDecodeError as e:
        print(f"    JSON PARSE ERROR (after retry): {e}")
        return None

    # Resolve the chosen image — fall back to first candidate (og:image) if Claude rejects all
    best_idx = result.get("bestImageIndex")
    if best_idx and isinstance(best_idx, int) and 1 <= best_idx <= len(page_images):
        result["image_url"] = page_images[best_idx - 1]
    elif page_images:
        result["image_url"] = page_images[0]  # og:image fallback
    else:
        result["image_url"] = None

    result["source_url"] = entry["url"]
    result["source_title"] = feed_title
    result["_client"] = client  # pass through for featured judgment
    return result


# ─── Featured judgment ────────────────────────────────────────────────────────

def judge_featured(client, article, image_path):
    """Second-pass: send the actual downloaded image to Claude to judge if featured-worthy."""
    import base64

    filepath = os.path.join(BASE_DIR, "web", "public", image_path.lstrip("/"))
    if not os.path.exists(filepath):
        return False

    # Read image and encode as base64
    with open(filepath, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(filepath)[1].lower()
    media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")

    prompt = f"""You are the visual editor for The Overview, a planetary governance research publication.

ARTICLE TITLE: {article.get('title', '')}
ARTICLE SUMMARY: {article.get('summary', '')}

The image above is the hero image for this article on our front page.

Should this article be FEATURED on the front page? Both conditions must be met:

1. VISUAL QUALITY: Is this image visually stunning? Lush nature photography, powerful documentary images, dramatic landscapes, compelling human moments in nature or governance — the kind of image that makes someone stop scrolling. NOT: logos, infographics, conference group photos, headshots, screenshots, promotional graphics, small/blurry images, or generic stock.

2. EDITORIAL SIGNIFICANCE: Is the article substantive for the planetary governance landscape? Major policy shifts, landmark reports, new governance experiments, legal precedents, significant ecological developments. NOT: routine announcements, job postings, minor updates, or promotional content.

Reply with ONLY a JSON object: {{"featured": true}} or {{"featured": false}}"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_data}},
                {"type": "text", "text": prompt},
            ]}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        return bool(result.get("featured", False))
    except Exception as e:
        print(f"      Featured judge error: {e}")
        return False


# ─── Markdown output ──────────────────────────────────────────────────────────

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].rstrip("-")


def existing_news_slugs():
    os.makedirs(NEWS_DIR, exist_ok=True)
    return {f.replace(".md", "") for f in os.listdir(NEWS_DIR) if f.endswith(".md")}


def save_article(article, actor_ids, project_ids):
    """Save extracted article as Astro-compatible markdown."""
    os.makedirs(NEWS_DIR, exist_ok=True)

    slug = slugify(article["title"])
    existing = existing_news_slugs()
    if slug in existing:
        slug = f"{slug}-{article.get('date', 'new')}"
    if slug in existing:
        print(f"    SKIP duplicate: {slug}")
        return None

    # Download the image Claude picked from the article page
    image_path = ""
    if article.get("image_url"):
        downloaded = download_image(article["image_url"], slug)
        if downloaded:
            image_path = downloaded
            print(f"      Image: {downloaded}")

    # Judge featured: send the downloaded image to Claude for visual quality assessment
    featured = False
    if image_path and article.get("_client"):
        featured = judge_featured(article["_client"], article, image_path)
        print(f"      Featured: {featured}")

    # Build frontmatter
    title_escaped = (article.get("title") or "").replace('"', "'")
    summary_escaped = (article.get("summary") or "").replace('"', "'")
    image_alt = (article.get("imageAlt") or "").replace('"', "'")
    tags = article.get("tags", ["landscape"])
    sources = []
    if article.get("source_url"):
        sources.append({
            "title": article.get("source_title", "Source"),
            "url": article["source_url"],
        })

    why_it_matters = (article.get("whyItMatters") or "").replace('"', "'")

    lines = [
        "---",
        f'title: "{title_escaped}"',
        f"date: {article.get('date', datetime.now().strftime('%Y-%m-%d'))}",
        f'summary: "{summary_escaped}"',
        f"featured: {'true' if featured else 'false'}",
    ]
    if why_it_matters:
        lines.append(f'whyItMatters: "{why_it_matters}"')
    if image_path:
        lines.append(f"image: {image_path}")
    if image_alt:
        lines.append(f'imageAlt: "{image_alt}"')
    lines.append(f"actors: [{', '.join(str(i) for i in actor_ids)}]")
    lines.append(f"projects: [{', '.join(str(i) for i in project_ids)}]")
    lines.append(f"tags: [{', '.join(tags)}]")

    if sources:
        lines.append("sources:")
        for s in sources:
            lines.append(f'  - title: "{s["title"]}"')
            lines.append(f'    url: "{s["url"]}"')

    lines.append("---")
    lines.append("")

    body = article.get("body", "")
    if body:
        lines.append(body)
        lines.append("")

    filepath = os.path.join(NEWS_DIR, f"{slug}.md")
    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    print(f"    SAVED: {slug}.md")
    return filepath


# ─── Main pipeline ────────────────────────────────────────────────────────────

def discover_feeds(conn, cur):
    """Discover RSS/Atom feeds from actor websites and monitored sources."""
    ensure_feeds_table(conn)

    print("\n=== Feed Discovery ===\n")

    # 1. Actor websites
    actors = get_all_actor_websites(cur)
    print(f"Checking {len(actors)} actor websites for feeds...\n")

    discovered = 0
    for actor in actors:
        website = actor["website"]
        if not website or website == "UNKNOWN":
            continue
        print(f"  {actor['name']} ({website})")
        feeds = discover_feeds_for_url(website)
        for feed_url in feeds:
            # Find or create source
            cur.execute("SELECT id FROM sources WHERE url = ?", (website,))
            row = cur.fetchone()
            source_id = row[0] if row else None

            fid = register_feed(conn, cur, feed_url, source_id=source_id, title=f"{actor['name']} Feed")
            if fid:
                print(f"    + {feed_url}")
                discovered += 1
                # Link actor to source if not already linked
                if source_id:
                    cur.execute(
                        "INSERT OR IGNORE INTO source_actor (source_id, actor_id) VALUES (?, ?)",
                        (source_id, actor["id"]),
                    )
                    conn.commit()

    # 2. Monitored sources (that might be feeds themselves)
    sources = get_monitored_sources(cur)
    print(f"\nChecking {len(sources)} monitored sources...\n")

    for source in sources:
        url = source["url"]
        print(f"  {source['title']} ({url})")

        # Check if the URL itself is a feed
        content, ct = fetch_url(url, timeout=8)
        if content:
            is_feed = False
            if ct and ("xml" in ct or "rss" in ct or "atom" in ct):
                is_feed = True
            elif content.strip().startswith("<?xml") or "<rss" in content[:500] or "<feed" in content[:500]:
                is_feed = True

            if is_feed:
                fid = register_feed(conn, cur, url, source_id=source["id"], title=source["title"])
                if fid:
                    print(f"    + Direct feed: {url}")
                    discovered += 1
                continue

            # Try discovering feeds from the page
            if "html" in (ct or ""):
                feeds = discover_feeds_for_url(url)
                for feed_url in feeds:
                    fid = register_feed(conn, cur, feed_url, source_id=source["id"], title=source["title"])
                    if fid:
                        print(f"    + {feed_url}")
                        discovered += 1

    print(f"\nDiscovered {discovered} new feeds")
    cur.execute("SELECT COUNT(*) FROM feeds WHERE active = 1")
    total = cur.fetchone()[0]
    print(f"Total active feeds: {total}")
    return discovered


def crawl_feeds(conn, cur, limit=None):
    """Crawl active feeds and extract articles with Claude."""
    ensure_feeds_table(conn)
    client = get_anthropic_client()

    # Build actor name lookup
    cur.execute("SELECT id, name FROM actors WHERE canonical_id IS NULL")
    actor_names_map = {r[0]: r[1] for r in cur.fetchall()}

    feeds = get_active_feeds(cur)
    if limit:
        feeds = feeds[:limit]

    print(f"\n=== Crawling {len(feeds)} feeds ===\n")

    total_saved = 0
    existing = existing_news_slugs()

    # Build set of source URLs already in existing articles to prevent re-crawling
    existing_source_urls = set()
    for slug in existing:
        md_path = os.path.join(NEWS_DIR, f"{slug}.md")
        try:
            with open(md_path) as f:
                for line in f:
                    if line.strip().startswith("url:"):
                        url_val = line.split("url:", 1)[1].strip().strip('"').strip("'")
                        if url_val:
                            existing_source_urls.add(url_val)
                    if line.strip() == "---" and existing_source_urls:
                        break  # past frontmatter
        except Exception:
            pass

    for feed_info in feeds:
        print(f"\n  [{feed_info['title'] or feed_info['url']}]")
        feed_title, entries = parse_feed(feed_info["url"])

        if not entries:
            print("    No entries found")
            # Mark inactive if consistently empty
            cur.execute("UPDATE feeds SET last_crawled = datetime('now') WHERE id = ?", (feed_info["id"],))
            conn.commit()
            continue

        print(f"    {len(entries)} entries from: {feed_title}")

        # Filter to recent entries (last 90 days)
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        recent = [e for e in entries if not e["date"] or e["date"] >= cutoff]
        if not recent:
            print("    No recent entries (90 days)")
            cur.execute(
                "UPDATE feeds SET last_crawled = datetime('now'), entry_count = ? WHERE id = ?",
                (len(entries), feed_info["id"]),
            )
            conn.commit()
            continue

        print(f"    {len(recent)} recent entries, extracting with Claude...")

        for entry in recent:
            # Duplicate check: source URL
            if entry.get("url") and entry["url"] in existing_source_urls:
                print(f"    SKIP (source URL exists): {entry['title'][:60]}")
                continue

            # Duplicate check: slug
            slug = slugify(entry["title"])
            if slug in existing:
                print(f"    SKIP (slug exists): {slug}")
                continue

            print(f"    > {entry['title'][:70]}")

            article = extract_article_with_claude(
                client, entry, feed_title,
                feed_info["actor_ids"], feed_info["project_ids"],
                actor_names_map,
            )

            if not article:
                continue

            # Skip irrelevant articles
            if not article.get("relevant", True):
                print(f"      Not relevant, skipping")
                continue

            filepath = save_article(article, feed_info["actor_ids"], feed_info["project_ids"])
            if filepath:
                total_saved += 1
                existing.add(slugify(article["title"]))
                if entry.get("url"):
                    existing_source_urls.add(entry["url"])

            # Rate limit: be kind to the API
            time.sleep(1)

        # Update feed metadata
        cur.execute(
            "UPDATE feeds SET last_crawled = datetime('now'), entry_count = ? WHERE id = ?",
            (len(entries), feed_info["id"]),
        )
        conn.commit()

    print(f"\n=== Done: {total_saved} articles saved ===")
    if total_saved > 0:
        print(f"Rebuild web: cd web && bun run build")
    return total_saved


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Crawl news feeds for the Garden landscape")
    parser.add_argument("--discover-only", action="store_true", help="Only discover feeds, don't crawl")
    parser.add_argument("--crawl-only", action="store_true", help="Only crawl existing feeds")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of feeds to crawl")
    args = parser.parse_args()

    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    try:
        if args.crawl_only:
            crawl_feeds(conn, cur, limit=args.limit)
        elif args.discover_only:
            discover_feeds(conn, cur)
        else:
            # Full pipeline: discover then crawl
            discover_feeds(conn, cur)
            crawl_feeds(conn, cur, limit=args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
