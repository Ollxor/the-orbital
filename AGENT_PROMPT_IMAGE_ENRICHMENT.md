# Agent Prompt: Image Enrichment for Garden Crawler

## Mission

Enrich every actor and project in the Garden Crawler database with high-quality photography. No placeholders, no shortcuts. Visit every website, explore subpages, find the richest visual content available, download it, process it, and register it in the database.

## Context

The Garden Crawler is a planetary governance research landscape database. It tracks actors (organisations, companies, networks, movements), projects, and people. The web frontend at `web/` is built with Astro and displays image galleries on actor and project detail pages.

### Current state
- **Database**: `garden.db` (SQLite) at project root
- **Images table**: `images` with columns `(id, entity_type, entity_id, filename, alt_text, caption, sort_order, created_at)`
- **Actor images**: stored in `web/public/images/actors/`
- **Project images**: stored in `web/public/images/projects/`
- **Already enriched**: ~26 actors and ~15 projects have gallery images
- **Remaining**: ~49 actors and ~8 projects still need images

### Quality bar
We want RICH, LUSH photography. Not OG image thumbnails. Not logos. Not icons. We want:
- Event photography (people gathered, workshops, assemblies)
- Landscape and nature photography (for environmental orgs)
- Installation and exhibition photos (for arts/design orgs)
- Project screenshots and data visualizations (for tech orgs)
- Team photos and portraits (when high quality)
- Report covers and publication imagery
- Architectural/space photography

**Target: 2-5 images per entity.** More for visually rich organizations. Minimum 1 for every entity that has a website.

## Workflow per entity

### 1. Scrape the website
Use WebFetch on the entity's main URL. Extract ALL image URLs from the page.

If the main page is JS-rendered (yields no images), try:
- Subpages: `/about`, `/gallery`, `/projects`, `/events`, `/media`, `/press`, `/team`
- The organization's blog or news section
- Their social media links (especially if they link to photo-heavy platforms)

If the website is completely inaccessible or yields nothing, try:
- Web search for `"organization name" site:flickr.com OR site:unsplash.com` for CC-licensed photos
- Their annual reports or publications (often have cover images)
- Conference/event pages where they appeared

### 2. Select the best images
From the scraped URLs, choose 2-5 images that are:
- High resolution (at least 400px wide after the URL suggests it)
- Actual photographs or rich illustrations (not logos, not icons, not tracking pixels)
- Representative of what the organization does
- Visually diverse (don't pick 5 similar headshots — mix landscapes, events, products, people)

Remove size suffixes from URLs to get full-size images when possible (e.g., `-300x200.jpg` → `.jpg`, `?w=300` → `?w=1200`).

### 3. Download
```bash
curl -sL -o "web/public/images/{actors|projects}/filename.jpg" "URL"
```

Use descriptive filenames: `{org-slug}-{content}.jpg` (e.g., `c40-cities-summit.jpg`, `rfcx-rainforest-device.jpg`)

### 4. Process with ImageMagick
```bash
magick input.jpg -resize '800x600>' -background '#f5f0e8' -flatten -quality 80 output.jpg
```

- Max 800px wide, maintain aspect ratio
- Flatten transparency with cream background (#f5f0e8)
- JPEG quality 80
- Remove any raw/tmp files after processing
- **Validate**: file size > 2KB, width > 200px. Delete failures.

### 5. Insert into database
```sql
INSERT INTO images (entity_type, entity_id, filename, alt_text, caption, sort_order)
VALUES ('actor', {id}, '{filename}', '{alt_text}', '{caption}', {n});
```

- `entity_type`: 'actor' or 'project'
- `alt_text`: Descriptive text for accessibility (what's literally in the image)
- `caption`: Editorial caption explaining significance (one sentence, what it means for The Garden's research)
- `sort_order`: 1 for hero image, 2+ for additional gallery images

### 6. Rebuild the site
After inserting a batch of images:
```bash
cd web && bun run build
```
Verify with `curl -s http://localhost:4321/actors/{id}/ | grep -c gallery__item`

## Remaining entities

### Actors without images (49)

| ID | Name | Website | Type |
|----|------|---------|------|
| 2 | Planetary Guardians / SpiralWeb | https://www.planetaryguardians.org | NGO |
| 3 | ÆRTH | https://www.aerth.live | Company |
| 5 | Climate TRACE | https://climatetrace.org | NGO |
| 6 | Rainforest Connection (RFCx) | https://rfcx.org | Company |
| 7 | Naturskyddsföreningen | https://www.naturskyddsforeningen.se | NGO |
| 10 | Spatial Web Foundation / Verses AI | https://thespatialweb.org | Company |
| 13 | Hypha DAO | https://dao.hypha.earth | Company |
| 17 | Transformative Play Initiative (Uppsala) | https://www.uu.se | Research |
| 18 | Fabel | https://www.fabelentertainment.com | Company |
| 19 | Electionville | https://sharingsweden.se | Company |
| 21 | The Borderland | https://borderlands.2k.com | Movement |
| 24 | Martin Ericsson | https://martineriksson.com | Person |
| 26 | Global Sustainability Jam | https://www.globaljams.org | Network |
| 27 | Earth System Governance Project | https://www.earthsystemgovernance.org | Research |
| 28 | World Social Forum | https://www.foranewwsf.org | Movement |
| 29 | C40 Cities | https://www.c40.org | Government |
| 30 | Polis | https://pol.is | Company |
| 31 | Pro-Human AI Declaration | https://humanstatement.org | Movement |
| 33 | Viable Cities | https://www.viablecities.se/ | Government |
| 34 | Curve Labs | https://www.curvelabs.eu/ | Company |
| 35 | Agenda Gotsch | https://agendagotsch.com | NGO |
| 36 | Kiss the Ground | https://kisstheground.com | NGO |
| 37 | Agroecology Europe | https://www.agroecology-europe.org | Network |
| 38 | Agroecology Coalition | https://agroecology-coalition.org | Network |
| 40 | Global Rewilding Alliance | https://globalrewilding.earth | Network |
| 41 | Ecosystem Restoration Communities | https://www.ecosystemrestorationcommunities.org | Movement |
| 42 | IIED Biocultural Heritage | https://biocultural.iied.org | Research |
| 43 | Grounded Solutions Network | https://groundedsolutions.org | Network |
| 44 | Alliance for Water Stewardship | https://a4ws.org | Network |
| 47 | Earth Law Center | https://www.earthlawcenter.org | NGO |
| 48 | Gaia Foundation | https://gaiafoundation.org | NGO |
| 49 | Open Data Cube | https://www.opendatacube.org | Research |
| 50 | Single.Earth | https://www.single.earth | Company |
| 51 | Toucan Protocol | https://blog.toucan.earth | Company |
| 52 | Liquid Democracy e.V. | https://liqd.net | NGO |
| 53 | Participatory Budgeting Project | https://www.participatorybudgeting.org | NGO |
| 55 | Gaia AI | https://www.gaia-ai.eco | Company |
| 56 | Steward Ownership | https://steward-ownership.com | Network |
| 58 | Megagame Assembly | https://www.megagameassembly.com | Network |
| 59 | Megagame Coalition | https://megagamecoalition.com | Network |
| 61 | Ritual Design Lab | https://www.ritualdesignlab.org | Research |
| 62 | Beckley Foundation | https://www.beckleyfoundation.org | Research |
| 64 | Institute for the Future | https://www.iftf.org | Research |
| 65 | Theatre of the Oppressed NYC | https://www.tonyc.nyc | NGO |
| 66 | Global Governance Innovation Network | https://ggin.stimson.org | Research |
| 67 | Centre for International Governance Innovation | https://www.cigionline.org | Research |
| 69 | People Powered | https://www.peoplepowered.org | Network |
| 73 | Planetary Health Alliance | https://planetaryhealthalliance.org | Network |
| 74 | Climate Justice Alliance | https://climatejusticealliance.org | Network |

### Projects without images (8)

| ID | Name | Website |
|----|------|---------|
| 3 | Planetary Guardians Protocol | https://spiralweb.earth/ |
| 4 | AERTH Planetary AI | https://www.aerth.live/ |
| 5 | Ningaloo Reef Digital Twin | https://www.aerth.live/ |
| 8 | RFCx Guardian System | https://rfcx.org/ |
| 9 | RFCx Arbimon Platform | https://rfcx.org/ |
| 15 | IEEE P2874 Spatial Web Standards | https://www.verses.ai/ |
| 17 | Self-Owning Nature Trusts | https://darkmatterlabs.property/ |
| 19 | SEEDS Regenerative Currency | https://hypha.earth/ |

## Batching strategy

Process in batches of 8-10 entities:
1. WebFetch 4 websites in parallel
2. Download images in parallel (curl with `&` and `wait`)
3. Process all with ImageMagick
4. Batch INSERT into database
5. Rebuild site
6. Verify galleries render

## Known difficult sites

These are JS-heavy and may need subpage scraping or alternative approaches:
- **climatetrace.org** — React SPA, try `/about` or press kit
- **rfcx.org** — Framer site, try `/our-work` or `/guardian`
- **pol.is** — Cloudflare protected, try searching for screenshots
- **aerth.live** — Wix site, images loaded dynamically
- **dao.hypha.earth** — Minimal content
- **borderlands.2k.com** — This might be the wrong URL (video game). The Borderland is a burn/festival, try `theborderland.se`

## After completion

1. Run `cd web && bun run build` for final build
2. Verify total image count: `sqlite3 garden.db "SELECT COUNT(*) FROM images"`
3. Spot-check 5 random actor galleries in browser
4. Check that no broken image links exist: `grep -r 'gallery__item' web/dist/ | wc -l` should match expected count
