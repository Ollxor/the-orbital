# Garden Crawler

Landscape research pipeline + news feed for The Garden, a planetary governance research project.

## Key Commands

```bash
./crawl.sh                      # Crawl RSS feeds, extract with Claude Sonnet
./crawl.sh --discover --limit 5 # Discover new feeds + crawl
./deploy.sh                     # Build Astro site + deploy to Cloudflare Pages
```

## Architecture

- **garden.db** — SQLite database with actors, projects, people, sources, feeds, orientations
- **crawl_feeds.py** — RSS crawler. Discovers feeds, parses entries, sends article pages + images to Claude Sonnet vision for editorial rewrite and image selection. Two-pass: first call extracts/rewrites, second call judges `featured` using the actual downloaded image.
- **collect_news.py** — Older news pipeline using Gemini Deep Research (generates briefs, parses results)
- **web/** — Astro 6 static site (BAAHM/P stack: Bun, Astro, Alpine, HTMX, Markdown, PostgreSQL). Reads SQLite at build time.

## News Articles

- Stored as markdown in `web/src/content/news/`
- Schema: title, date, summary, featured (bool), image, imageAlt, actors (IDs), projects (IDs), tags, sources
- `featured: true` articles appear on the front page; all articles appear at `/news/`
- Featured requires both editorial significance AND a visually stunning image
- The crawler's Claude prompt includes a tone guide — analytical but warm, uses em dashes, connects to planetary governance themes

## Deployment

- Cloudflare Pages project: `theoverview`
- URL: https://theoverview.pages.dev
- Build: `cd web && bun run build` (output in `web/dist/`)
- Deploy: `wrangler pages deploy dist --project-name theoverview`

## Env Vars (.env.local)

- `ANTHROPIC_API_KEY` — Claude Sonnet API (news crawler extraction + featured judgment)
- `BRAVE_API_KEY` — Brave Search API (feed discovery)
- `GEMINI_API_KEY` — Gemini API (collect_news.py deep research)

## Database Tables

Key tables: `actors`, `projects`, `people`, `sources`, `feeds`, `orientations`, `categories`. Feeds link to sources via `source_id`, sources link to actors/projects via junction tables `source_actor`/`source_project`.

## Conventions

- Python scripts at project root, web app in `web/`
- News images saved to `web/public/images/news/`
- SQLite DB is read-only during web build
- Feeds table tracks `last_crawled` to avoid re-processing
