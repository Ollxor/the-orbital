# The Orbital — Claude Working Instructions

This file tells Claude what this project is and how to perform recurring tasks
without needing to rediscover everything from scratch each session.

---

## What this project is

**The Orbital** is a curated news feed at theorbital.net tracking the planetary
systems governance movement — the slow global shift toward regenerative,
participatory, ecologically grounded governance. It is Olle's personal prototype
and public experiment, built with Astro + TypeScript, deployed to Cloudflare Pages
from the public GitHub repo `Ollxor/the-orbital`.

The Orbital is one public-facing piece of a larger unnamed project, of which
"Prototopia" (a funded application) and a future LARP/ARG called
"Planetary Assembly" are also parts. The endgame is a self-organised global
assembly where people collectively shape the future — gamified, pervasive,
real.

### Four orientations (lenses on content)

Assign one or more. Most content has a primary orientation + 1 secondary. Rarely
three. Almost never all four — that's usually a sign of being too generous.

| Orientation | Core question | Examples |
|-------------|---------------|---------|
| **GARDEN** | How do we tend living systems? | Agroecology, rewilding, rights of nature, soil, food sovereignty, biodiversity, indigenous land practice |
| **SPACESHIP** | How do we build and model the systems? | AI, digital twins, satellite monitoring, blockchain governance, open data protocols, climate modelling, civic tech |
| **MYSTERIES** | How do we transform culture and consciousness? | LARP, megagames, ritual design, experiential futures, festival culture, theatre, ceremony, inner work |
| **ASSEMBLY** | How do we decide together? | Citizens assemblies, deliberative democracy, sortition, rights of nature legal frameworks, global governance, commons |

**Assignment rules:**
- An org doing satellite monitoring of forests → SPACESHIP primary, GARDEN secondary
- A citizens assembly process → ASSEMBLY primary; add GARDEN/SPACESHIP if the topic is ecological/tech
- A LARP about governance → MYSTERIES primary, ASSEMBLY secondary
- "Spaceship Earth" thinking (Buckminster Fuller, systems) → SPACESHIP, not MYSTERIES
- Climate science research → SPACESHIP, GARDEN (not ASSEMBLY unless it's governance-focused)
- Rights of nature legal work → GARDEN, ASSEMBLY (legal framework = Assembly)
- Regenerative farming → GARDEN only, unless it has policy angle (add ASSEMBLY)
- Digital democracy tools → SPACESHIP, ASSEMBLY
- Indigenous knowledge holders → GARDEN, MYSTERIES (not Assembly unless they're doing governance advocacy)

---

## Private documents

Sensitive project docs live at `site/docs/` (gitignored — never pushed to GitHub).
They can also be found at `D:/Dropbox/The Orbital/_extracted-text/` as a backup.
If you can't find them via relative path, ask Olle to confirm location or share
from Dropbox. Key files:

- `PROTOTOPIA - PROJECT BIBLE.txt` — org structure, people, NPCs, grant info
- `Prototopia - Core Design Philosophy.txt` — 12 biomimicry-rooted design principles
- `Manifesto V2.txt` — "THE GARDEN" manifesto (to be rewritten; currently placeholder only)
- `PROTOTOPIA - Governance Systems Library.txt` — ~40 governance tools tagged by scale/use-case
- `Prototopia - Chat contexts.txt` — three parallel Slack/chat streams
- `the_garden_project_brief.txt` — co-designer brief

---

## Data files

All content lives in `src/data/`:
- `news.json` — articles + videos (see schema below)
- `actors.json` — organisations, initiatives, people
- `projects.json` — active projects
- `events.json` — upcoming/recent events

---

## News/video schema

```json
{
  "slug": "unique-kebab-case-id",
  "kind": "article",           // "article" | "video" — omit means "article"
  "videoId": "",               // YouTube video ID, only if kind=video
  "title": "...",
  "date": "YYYY-MM-DD",
  "image": "https://...",      // og:image URL or YouTube thumbnail
  "imageAlt": "...",
  "summary": "1-2 sentence summary shown in feed (aim for 120-160 chars)",
  "body": "Full article text, multiple paragraphs",
  "insight": "One sentence on why this matters for planetary governance",
  "actors": ["slug-1"],        // actor slugs linked to this story
  "tags": ["tag-1", "tag-2"],
  "orientations": ["GARDEN"],  // one or more of the four orientations
  "sourceUrl": "https://..."
}
```

For **videos**: set `kind: "video"`, set `videoId` to the YouTube video ID
(the part after `?v=`), and set `image` to
`https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg`.

---

## How to update the feed

When Olle says "update the feed", do the following:

### 1. Find new articles (aim for 4–8 per update)

Search these sources for recent content (last 2–4 weeks):

**Regular sources:**
- resilience.org — degrowth, agroecology, energy transition
- globalchallenges.org — existential risk, global governance
- metagov.org — digital governance, DAOs, collective intelligence
- rightsofnaturetribunal.org / garn.org — rights of nature
- viablecities.se — sustainable urban transitions
- democracynext.org — citizens' assemblies
- involve.org.uk — participation, deliberation
- theconversation.com — with search terms below
- sciencedirect.com / scholar — academic governance research

**Search terms to use (rotate and combine):**
- "planetary governance" / "earth governance"
- "citizens assembly climate"
- "rights of nature 2025/2026"
- "ecological democracy"
- "degrowth policy"
- "metagovernance"
- "commons governance"
- "bioregional governance"

**For each candidate:** fetch the URL, extract title + og:image + summary,
write a 1-2 sentence summary and a "why this matters" insight sentence,
assign orientations, draft the slug from the title.

### 2. Find new YouTube videos

Search YouTube (via WebSearch with `site:youtube.com` or by constructing
YouTube search URLs) for videos posted in the last 2–4 weeks on the topics above.

**Include a video if:**
- 10,000+ views (check via YouTube page or search snippet), OR
- From a credible source regardless of view count: UN, TED/TEDx talks on
  governance topics, academic institutions, established orgs in actors.json

**Video entry:** set `kind: "video"`, grab the `videoId`, use the YouTube
thumbnail as `image`, write summary + insight describing what the video argues.

### 3. Find new actors / projects / events (opportunistically)

If a new org, initiative, or event comes up in the articles, consider adding
it to `actors.json` / `projects.json` / `events.json`.

### 4. Build and verify

```
powershell.exe -Command "$env:PATH = 'D:\Program Files\nodejs;' + $env:PATH; cd 'D:\Dropbox\The Orbital\site'; & 'D:\Program Files\nodejs\npm.cmd' run build 2>&1"
```

Check for TypeScript errors. Commit:
```
git -C 'D:/Dropbox/The Orbital/site' add src/data/
git -C 'D:/Dropbox/The Orbital/site' commit -m "feed: add N articles + M videos (YYYY-MM-DD)"
git -C 'D:/Dropbox/The Orbital/site' push origin main
```

---

## Tech notes

- **Node.js** lives at `D:\Program Files\nodejs\` — never in PATH; always use full path
- **Git** at `D:\Program Files\Git\cmd\git.exe`
- **Build** artifacts go to `dist/` (gitignored, EBUSY on Dropbox is harmless)
- **Cloudflare Pages** auto-deploys on push to main; takes ~60 seconds
- **YouTube thumbnails** are free: `https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg`
- Repo is **public** — never commit anything in `docs/`, credentials, or Olle's personal info

---

## Planned (not yet built)

### Geographic filter — advanced facets

The current filter bar has Continent, Scale, and Type. A second pass should add:

- **Subregion** drilldown — appears once a continent is selected; subregions grouped by continent if multiple selected. Reference data is in `src/data/regions.json` and `src/content/regions.yaml`.
- **Country** — searchable multi-select using ISO 3166-1 alpha-2 codes (now stored in `actor.country[]`).
- **Bioregion** — searchable multi-select, populated from `actor.bioregion[]` tags.
- **Tags** — existing freeform tags.

These are in the `actors.json` schema already (`subregion`, `country`, `bioregion`); only the UI is missing.

### Language filter

`actor.languages[]` exists in schema (ISO 639-1 codes) but is empty for all actors and has no UI. A future pass should:
- Backfill language data for existing actors
- Add a language facet to the advanced filter bar

### Regional scrapers — dedicated sub-phase

Expanding actor coverage from underrepresented regions requires scrapers for directories maintained by people and organisations in those regions. Different challenges from European/North American directories:

- Different naming conventions and transliteration (actors may appear under multiple names across languages and scripts)
- Different organisational forms (cooperatives, self-organised federations, kinship-based networks) that may not fit the current `type` enum — expect to extend it
- Different data quality (some directories are PDFs, wikis, social media networks)
- Greater risk of miscategorisation without local knowledge — lower confidence threshold and default imports to `status: pending_review`

**Initial source candidates** (verify before adding to any scraper):

Africa: African Climate Foundation, Allied Climate Partners Africa, Shack/Slum Dwellers International (SDI), The Green Institute (Nigeria)

Asia: Asia Foundation civil society mappings, ICSF (International Collective in Support of Fishworkers), SEWA (India) and affiliated networks, Grassroots Asia, Focus on the Global South

Latin America & Caribbean: Fundación Avina, CEPAL civil society registries, ALAMES, Global Greengrants regional hubs

Oceania & Pacific: Pacific Islands Climate Action Network (PICAN), Pacific Community (SPC), First Nations climate networks in Australia and Aotearoa

### Indigenous network handling

The `peoples` field enables Indigenous and First Nations networks to be indexed without forcing them into the nation-state `country` frame. A future editorial pass should:

- Develop guidelines for when to use `peoples` vs `country` vs both
- Consult with Indigenous contributors before publishing profiles of Indigenous networks (consent and framing matter; do not scrape these)
- Consider whether Indigenous actors warrant a dedicated editorial pathway separate from bulk scraping

### Filter URL compat

Old `/actors?r=nordic` links no longer resolve (the `r=` region param was replaced by `c=` continent and `s=` scale in the geographic taxonomy migration). If inbound links need support, add a redirect or param-mapping shim at the Cloudflare level.
