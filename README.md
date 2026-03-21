# Garden Crawler — Landscape Research Pipeline

Automated landscape research pipeline for **The Garden**: a project to prototype planetary governance through play, simulation, and embodied experience.

Maps organisations, companies, networks, research groups, movements, and initiatives worldwide across four orientations:

- **Garden of Eden** — Living systems, ecology, land stewardship, regenerative economics
- **Spaceship Earth** — Technology, infrastructure, governance tools, alternative ownership
- **Eleusinian Mysteries** — Transformative games, LARP, ritual, experiential futures
- **General Assembly of Earth** — Global governance innovation, participatory democracy, rights of nature

Adapted from the [Voysys](https://voysys.se) lead generation machine.

## Folder Structure

```
garden-crawler/
├── inbox/              # Drop reports, lists, docs, raw ideas here
│   └── handled/        # Processed files get moved here
├── chunks/             # Chunked documents for Step B processing
│   └── <doc_name>/     # Per-document: chunk_*.json, extraction_*.json, manifest.json
├── briefs/             # Generated research prompts (Step 0 output)
├── garden.db           # SQLite database (created by seed_from_excel.py)
├── garden_landscape_map.xlsx  # Source Excel with categories, seed actors, people map
├── .env.local          # BRAVE_API_KEY, GEMINI_API_KEY (not in git)
├── schema.sql          # DB schema reference
├── seed_from_excel.py  # Seed DB from Excel (run once)
├── research.py         # Step 0: generate research briefs from DB gaps
├── chunker.py          # Split documents into overlapping chunks
├── extract_chunk.py    # Generate extraction template for a single chunk
├── merge_chunks.py     # Deduplicate + commit chunk extractions to DB
├── step_c_search.py    # Step C: search phrases via brave-cli
├── step_c_evaluate.py  # Step C: evaluate + commit search results
└── README.md
```

## Setup

```bash
# Install dependencies
pip3 install openpyxl google-genai

# Seed the database from the Excel landscape map
python3 seed_from_excel.py

# Verify
sqlite3 garden.db "SELECT code, name FROM orientations"
sqlite3 garden.db "SELECT COUNT(*) FROM categories"
sqlite3 garden.db "SELECT COUNT(*) FROM actors"
sqlite3 garden.db "SELECT COUNT(*) FROM search_phrases"
```

## Tools

- **brave-cli** — Brave Search API client (`cargo install --git https://github.com/thesurlydev/brave-cli`). API key in `.env.local` as `BRAVE_API_KEY`.
- **agent-browser** — Browser automation for Step D source fetching
- **Gemini Deep Research** — Automated web research via API. Key in `.env.local` as `GEMINI_API_KEY`.

## Database Schema

### Hierarchical Taxonomy

**orientations** — The four lenses of The Garden (4 rows).

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK |
| code | TEXT | UNIQUE: GARDEN, SPACESHIP, TEMPLE, ASSEMBLY |
| name | TEXT | Full name, e.g. "Garden of Eden" |
| description | TEXT | What this orientation covers |

**categories** — 30 research categories, each under one orientation.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK |
| orientation_id | INTEGER | FK → orientations.id |
| name | TEXT | UNIQUE, e.g. "Regenerative Agriculture" |
| description | TEXT | What this category covers |
| search_terms | JSON | Array of 4-6 search phrases |
| actor_types | JSON | Expected actor types in this category |

### Actors

Organisations, companies, networks, movements, people — the entities being mapped.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK |
| name | TEXT | NOT NULL |
| type | TEXT | NGO, Company, Research, Government, Network, Movement, Person |
| primary_orientation_id | INTEGER | FK → orientations.id |
| secondary_orientation_id | INTEGER | FK → orientations.id (nullable) |
| description | TEXT | 1-2 sentences |
| website | TEXT | Main URL |
| domain | TEXT | Normalized domain for dedup |
| location | TEXT | Country or region |
| scale | TEXT | Local, National, Regional, Global |
| maturity | TEXT | Idea, Early, Active, Established |
| relevance_score | INTEGER | 1-5 (how relevant to The Garden's vision) |
| connection | TEXT | How we found them |
| contact_pathway | TEXT | Do we know someone who knows them? |
| canonical_id | INTEGER | Self-ref for dedup/merge |
| notes | TEXT | |

**actor_category** — Junction: actors ↔ categories (many-to-many).

### People Map

Individuals connected to actors and The Garden network.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK |
| first_name, last_name | TEXT | |
| email, phone | TEXT | |
| job_title, linkedin_url | TEXT | |
| primary_orientation_id | INTEGER | FK → orientations.id |
| skills | TEXT | What they bring |
| relationship_tier | TEXT | Core team candidate, Strategic advisor, etc. |
| status | TEXT | Freeform status |

**person_actor** — Junction: people ↔ actors (with role).

### Projects, Intel, Sources, Search Phrases

These tables work identically to the Voysys pipeline but with `entity_type = 'actor'` instead of `'company'` in the intel table.

### Flags

High-value signals on actors:

| Flag Type | Meaning |
|-----------|---------|
| `network_connected` | Already connected to someone in our network |
| `close_vision` | Doing something very close to The Garden's vision |
| `event_opportunity` | Running events where Garden could be presented |
| `funding_source` | Offers funding or grants relevant to our work |
| `nordic_based` | Based in Sweden or the Nordics |

## Workflow

### Step 0 — Research Brief

Generate a targeted research prompt based on DB coverage gaps:

```bash
python3 research.py --focus gaps                              # High-relevance actors with thin coverage
python3 research.py --focus deepen                            # Go deeper on known actors
python3 research.py --focus expand --orientation GARDEN        # Scan for new Garden of Eden actors
python3 research.py --focus expand --category "Ritual & Ceremony Design"  # Scan specific category
python3 research.py --focus gaps --run                        # Auto-research via Gemini Deep Research
```

**Focus modes:**

| Mode | What it does |
|------|-------------|
| `gaps` | Finds high-relevance actors with thin coverage. Generates a deep-dive prompt. |
| `deepen` | Picks actors with existing intel, asks for people, collaborators, events, Nordic links. |
| `expand` | Landscape scan for new actors in underrepresented orientations/categories. |

### Step A — Ingest

Drop any file into `inbox/`: reports, lists, articles, notes, raw ideas.

### Step B — Parse & Seed (Chunked)

```bash
python3 chunker.py inbox/<file>                                      # B.1: Chunk
# AI agent processes each chunk_*.json → extraction_*.json            # B.2: Extract
python3 merge_chunks.py chunks/<doc_name>/ --source-file inbox/<file> # B.3: Merge
```

The extraction template (from `extract_chunk.py`) captures actors, projects, people, sources, and search phrases. Actors include orientation, category, type, scale, maturity, and relevance score.

### Step C — Search Expansion

```bash
python3 step_c_search.py high    # Search high-priority phrases
# AI evaluates step_c_results.json, edits step_c_evaluate.py
python3 step_c_evaluate.py       # Commit curated results
```

### Step D — Source Processing

For each source where `last_fetch IS NULL`: fetch URL, extract actors/projects/people, record relationships, flag high-value connections.

### Step E — Monitor (Budgeted)

Re-search stale phrases, re-fetch monitored sources, flow new findings back through Steps C/D.

## Orientation Classification Guide

- **If they primarily work with land, ecosystems, food, water, biodiversity, or indigenous knowledge → Garden of Eden**
- **If they primarily build technology, platforms, data systems, governance tools, economic infrastructure → Spaceship Earth**
- **If they primarily create experiences, games, rituals, art, performance, festivals → Eleusinian Mysteries**
- **If they primarily work on global governance, democracy innovation, rights frameworks, climate justice → General Assembly of Earth**
- **If they do two of these equally → list both, primary first**

## Inclusion Criteria

**Include if:** actively doing something, work connects to at least one orientation, real outputs (projects, publications, events, products, communities), could plausibly participate in a governance LARP/simulation/assembly.

**Exclude if:** purely commercial with no governance/ecological/social dimension, defunct (2+ years inactive), a single blog post not an org, purely AI safety debate without governance application.

## Invariants

### Website Resolution

Every actor **must** have a `website` at insert time. If none found, set `website = 'UNKNOWN'` and add a search phrase `"{Actor Name} official website"` at high priority.

### Source URI Conventions

| Prefix | Meaning |
|--------|---------|
| `https://` / `http://` | Web URL — fetchable by `agent-browser` |
| `file://inbox/...` | Local file dropped into inbox |
