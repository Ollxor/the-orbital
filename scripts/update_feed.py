#!/usr/bin/env python3
"""
The Orbital — Automated feed updater
Fetches RSS feeds, filters for relevant articles, generates structured entries
via Claude Haiku, and prepends them to news.json.

Cost: ~$0.001 per article processed. Runs daily via GitHub Actions.
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

import feedparser
import requests
import anthropic

# ── Configuration ────────────────────────────────────────────────────────────

LOOKBACK_DAYS = 7       # How far back to look
MAX_CANDIDATES = 80     # Max articles to evaluate per run (was 30 — raised for the
                        # 38-source pipeline. ~$0.001 per eval, so up to ~$0.08/run)
MAX_NEW_ENTRIES = 25    # Max articles to actually add per run (was 8)
                        # Most go to "stream" tier; "main" stays selective
NEWS_JSON = "src/data/news.json"

# RSS feeds — all URLs verified live as of 2026-04-27.
# Organised by thematic cluster for easy maintenance.
RSS_FEEDS = [
    # ── Ecological / regenerative ──────────────────────────────────────────
    # High volume, consistently on-topic
    {"url": "https://www.resilience.org/feed/",
     "name": "Resilience.org"},
    # Post-growth, local economies, Slow Food adjacent
    {"url": "https://localfutures.org/feed/",
     "name": "Local Futures"},
    # Rights of nature legal news
    {"url": "https://www.garn.org/feed/",
     "name": "GARN"},
    # Global south environmental reporting
    {"url": "https://www.ipsnews.net/feed/",
     "name": "IPS News"},
    # Sharing economy, commons, community
    {"url": "https://www.shareable.net/feed/",
     "name": "Shareable"},
    # Justice / ecology / social movements
    {"url": "https://www.yesmagazine.org/feed",
     "name": "YES! Magazine"},

    # ── Deliberative democracy / participation ─────────────────────────────
    # Dedicated citizens-assembly outlet
    {"url": "https://democracynext.org/feed/",
     "name": "DemocracyNext"},
    # Democratic theory, global governance reform
    {"url": "https://www.opendemocracy.net/feed/",
     "name": "openDemocracy"},
    # Civil society, nonprofit governance
    {"url": "https://nonprofitquarterly.org/feed/",
     "name": "Nonprofit Quarterly"},
    # Commons practices and governance resources
    {"url": "https://commonslibrary.org/feed/",
     "name": "Commons Library"},

    # ── Systems / tech / civic innovation ─────────────────────────────────
    # Civic tech aggregator — tools, platforms, experiments
    {"url": "https://civictech.guide/feed/",
     "name": "Civic Tech Guide"},
    # Climate data and systems science journalism
    {"url": "https://www.carbonbrief.org/feed/",
     "name": "Carbon Brief"},
    # Climate investigation reporting
    {"url": "https://insideclimatenews.org/feed/",
     "name": "Inside Climate News"},

    # ── Economics / transition ─────────────────────────────────────────────
    # New Economics Foundation — wellbeing, post-growth policy
    {"url": "https://neweconomics.org/feed",
     "name": "New Economics Foundation"},
    # Existential risk / global governance think-tank
    {"url": "https://globalchallenges.org/feed/",
     "name": "Global Challenges Foundation"},

    # ── Broad academic / international ─────────────────────────────────────
    # Large quality academic feed — good signal when filtered
    {"url": "https://theconversation.com/articles.atom",
     "name": "The Conversation"},

    # ── Breakthrough science about life and Earth systems ──────────────────
    # Best biodiversity / conservation reporting on the planet
    {"url": "https://news.mongabay.com/feed/",
     "name": "Mongabay"},
    # Rigorous science explainers — naturally selects for breakthroughs
    {"url": "https://www.quantamagazine.org/feed/",
     "name": "Quanta Magazine"},
    # Essays on consciousness, more-than-human, deep ecology
    {"url": "https://aeon.co/feed.rss",
     "name": "Aeon"},
    # AI + animal communication — direct sensing-the-living-world work
    {"url": "https://www.earthspecies.org/blog?format=rss",
     "name": "Earth Species Project"},

    # ── Solutions journalism + planetary perspective ──────────────────────
    # Solutions science journalism — naturally selects for breakthroughs
    {"url": "https://www.anthropocenemagazine.org/feed/",
     "name": "Anthropocene Magazine"},
    # Deep ecology, more-than-human, indigenous wisdom — strong MYSTERIES
    {"url": "https://emergencemagazine.org/feed/",
     "name": "Emergence Magazine"},
    # Solutions-focused climate journalism
    {"url": "https://yaleclimateconnections.org/feed/",
     "name": "Yale Climate Connections"},
    # Solutions journalism flagship (broad)
    {"url": "https://reasonstobecheerful.world/feed/",
     "name": "Reasons to be Cheerful"},
    # Long-term thinking, planetary perspective, civilisation-scale
    {"url": "https://blog.longnow.org/feed/atom/",
     "name": "Long Now Foundation"},
    # Post-growth economics — small but high quality
    {"url": "https://centerforneweconomics.org/feed/",
     "name": "Schumacher Center"},
    # Meta — solutions journalism methodology + practitioner stories
    {"url": "https://www.solutionsjournalism.org/blog?format=rss",
     "name": "Solutions Journalism Network"},

    # ── Substack — individual writers with depth ───────────────────────────
    # The 3-tier system absorbs higher volume; main-tier filter still strict.
    # Volts — David Roberts on energy/climate policy
    {"url": "https://www.volts.wtf/feed",
     "name": "Volts"},
    # Andrew Dessler & Zeke Hausfather on climate science
    {"url": "https://www.theclimatebrink.com/feed",
     "name": "The Climate Brink"},
    # Emily Atkin on climate accountability
    {"url": "https://heated.world/feed",
     "name": "Heated"},
    # Bill McKibben on the climate movement
    {"url": "https://billmckibben.substack.com/feed",
     "name": "Crucial Years (Bill McKibben)"},

    # ── Substack — extended set across all four orientations ───────────────
    # GARDEN: small-farm + agroecology + post-growth ag
    {"url": "https://chrissmaje.substack.com/feed",
     "name": "Small Farm Future (Chris Smaje)"},
    # SPACESHIP + GARDEN: sustainability data, evidence-based
    {"url": "https://hannahritchie.substack.com/feed",
     "name": "By the Numbers (Hannah Ritchie)"},
    # SPACESHIP + MYSTERIES: civilisation-scale essays (Berggruen Institute)
    {"url": "https://noemamag.com/feed/",
     "name": "Noema Magazine"},
    # MYSTERIES: sacred economy, gift, more-than-human
    {"url": "https://charleseisenstein.substack.com/feed",
     "name": "Charles Eisenstein"},
    # MYSTERIES: Dark Mountain co-founder, deep ecology, narrative
    {"url": "https://dougald.substack.com/feed",
     "name": "Writing Home (Dougald Hine)"},
    # MYSTERIES: consciousness research, transformation
    {"url": "https://danielpinchbeck.substack.com/feed",
     "name": "Liminal News (Daniel Pinchbeck)"},
    # MYSTERIES: Ministry for the Future author
    {"url": "https://kim.substack.com/feed",
     "name": "Kim Stanley Robinson"},
    # MYSTERIES: Booker winner, planetary perspective from orbit
    {"url": "https://samanthaharvey.substack.com/feed",
     "name": "Samantha Harvey"},
    # ASSEMBLY + MYSTERIES: emergent strategy, Movement Generation
    {"url": "https://www.adriennemareebrown.net/feed",
     "name": "adrienne maree brown"},
    # ASSEMBLY + MYSTERIES: politics, architecture, decoloniality
    {"url": "https://thefunambulist.net/feed",
     "name": "The Funambulist"},
    # ASSEMBLY + GARDEN: post-growth movement
    {"url": "https://post-growth.substack.com/feed",
     "name": "Post-Growth Institute"},
    # ASSEMBLY: democracy theory and practice (podcast + blog)
    {"url": "https://www.democracyparadox.com/feed",
     "name": "Democracy Paradox"},

    # ── Additional culture / regenerative / indigenous / commons ──────────
    # Climate + culture intersection
    {"url": "https://atmos.earth/feed/",
     "name": "Atmos"},
    # Broad solutions-leaning climate
    {"url": "https://grist.org/feed/",
     "name": "Grist"},
    # DIY regenerative practice
    {"url": "https://www.lowimpact.org/feed/",
     "name": "Low Impact"},
    # Indigenous rights and biocultural heritage
    {"url": "https://www.culturalsurvival.org/rss.xml",
     "name": "Cultural Survival"},
    # Regenerative culture / biomimicry / environmental movement
    {"url": "https://www.bioneers.org/feed/",
     "name": "Bioneers"},
    # Commons governance and economy
    {"url": "https://commonsstrategies.org/feed/",
     "name": "Commons Strategies Group"},
    # Low-carbon living, slow-tech sensibility
    {"url": "https://earthbound.report/feed/",
     "name": "Earthbound Report"},
    # Regenerative innovation
    {"url": "https://transformatise.com/feed/",
     "name": "Transformatise"},

    # ── YouTube channels (kind="youtube" → entries become video items) ─────
    # The breakthrough rubric in SYSTEM_PROMPT still gates these. Most
    # videos from these channels will NOT qualify (cosmology, hardware
    # milestones, pop science). Only worldview-shifting / governance-
    # relevant ones should pass.
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCciQ8wFcVoIIMi-lfu8-cjQ",
     "name": "Anton Petrov", "kind": "youtube"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCOT2iLov0V7Re7ku_3UBtcQ",
     "name": "Hank Green", "kind": "youtube"},
    # Deep Look (PBS/KQED) — macro biology, sensing-the-living-world
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC-3SbfTPJsL8fJAPKiVqBLg",
     "name": "Deep Look", "kind": "youtube"},

    # ── Science / sensing the living world (expanded) ──────────────────────
    # Coastal + ocean science, marine ecosystems, rarely covered — GARDEN + SPACESHIP
    {"url": "https://hakaimagazine.com/feed/",
     "name": "Hakai Magazine"},
    # Interdisciplinary science — consciousness, biology, Earth systems
    {"url": "https://nautil.us/feed/",
     "name": "Nautilus Magazine"},
    # Neuroscience journalism — brain, consciousness, interspecies perception
    {"url": "https://www.thetransmitter.org/feed/",
     "name": "The Transmitter"},
    # Science journalism with social + ethical framing — SPACESHIP
    {"url": "https://undark.org/feed/",
     "name": "Undark"},
    # Animal cognition, sentience, food systems — GARDEN + SPACESHIP
    {"url": "https://sentientmedia.org/feed/",
     "name": "Sentient Media"},
    # Philosophy of mind, human nature — Aeon's sister publication — MYSTERIES
    {"url": "https://psyche.co/feed",
     "name": "Psyche"},
    # Independent ecology + politics magazine — GARDEN + ASSEMBLY
    {"url": "https://theecologist.org/feed",
     "name": "The Ecologist"},

    # ── Global majority / food sovereignty / decolonial ────────────────────
    # Tech + politics from Global South perspective — SPACESHIP + ASSEMBLY
    {"url": "https://restofworld.org/feed/",
     "name": "Rest of World"},
    # Pan-African political culture, decoloniality — MYSTERIES + ASSEMBLY
    {"url": "https://africasacountry.com/feed/",
     "name": "Africa Is A Country"},
    # Global peasant movement, food sovereignty — GARDEN + ASSEMBLY
    {"url": "https://viacampesina.org/en/feed/",
     "name": "La Via Campesina"},
    # Seed rights, land grabs, agroecology — GARDEN + ASSEMBLY
    {"url": "https://grain.org/e/feed",
     "name": "GRAIN"},
    # Citizen media worldwide, multilingual perspectives
    {"url": "https://globalvoices.org/feed/",
     "name": "Global Voices"},
    # Himalayan water, Asian ecology, glacier governance — GARDEN + ASSEMBLY
    {"url": "https://www.thethirdpole.net/feed/",
     "name": "The Third Pole"},
    # Social movement strategy, nonviolent action — ASSEMBLY
    {"url": "https://wagingnonviolence.org/feed/",
     "name": "Waging Nonviolence"},
    # Pan-African progressive media — ASSEMBLY + GARDEN
    {"url": "https://www.pambazuka.org/rss.xml",
     "name": "Pambazuka News"},

    # ── Democracy / governance depth ───────────────────────────────────────
    # Global open government initiative — ASSEMBLY + SPACESHIP
    {"url": "https://www.opengovpartnership.org/feed/",
     "name": "Open Government Partnership"},
    # Civic tech for democracy, digital tools — SPACESHIP + ASSEMBLY
    {"url": "https://www.mysociety.org/feed/",
     "name": "mySociety"},
    # Commons, peer production, distributed governance
    {"url": "https://blog.p2pfoundation.net/feed",
     "name": "P2P Foundation"},
    # Digital governance, DAOs, collective intelligence research
    {"url": "https://metagov.org/feed/",
     "name": "Metagov"},
    # UK participation + deliberation — ASSEMBLY
    {"url": "https://www.involve.org.uk/feed",
     "name": "Involve"},
    # Forest tenure, land rights for local + Indigenous peoples — GARDEN + ASSEMBLY
    {"url": "https://rightsandresources.org/feed/",
     "name": "Rights and Resources Initiative"},
    # Innovation + social change — SPACESHIP + ASSEMBLY
    {"url": "https://www.nesta.org.uk/feed/",
     "name": "Nesta"},

    # ── Culture / consciousness / MYSTERIES ────────────────────────────────
    # Deep ecology arts + writing — flagship MYSTERIES publication
    {"url": "https://dark-mountain.net/feed/",
     "name": "Dark Mountain"},
    # Inner + outer transformation, global consciousness — MYSTERIES + ASSEMBLY
    {"url": "https://www.kosmosjournal.org/feed/",
     "name": "Kosmos Journal"},
    # Ecology, spirituality, arts — GARDEN + MYSTERIES
    {"url": "https://www.resurgence.org/news/rss.xml",
     "name": "Resurgence & Ecologist"},
    # Buddhist ecology and social engagement — MYSTERIES + ASSEMBLY
    {"url": "https://tricycle.org/feed/",
     "name": "Tricycle"},
    # Joanna Macy tradition — grief, agency, ecological reconnection
    {"url": "https://workthatreconnects.org/feed/",
     "name": "Work That Reconnects"},

    # ── Post-growth / circular / commons economics ─────────────────────────
    # Circular economy research and case studies — SPACESHIP + ASSEMBLY
    {"url": "https://www.ellenmacarthurfoundation.org/articles/rss",
     "name": "Ellen MacArthur Foundation"},
    # Wellbeing economy policy + practice — ASSEMBLY + GARDEN
    {"url": "https://wellbeingeconomy.org/feed",
     "name": "Wellbeing Economy Alliance"},
    # Ecological / steady-state economics — ASSEMBLY + SPACESHIP
    {"url": "https://steadystate.org/feed/",
     "name": "Steady State Herald"},
    # Positive futures — curated breakthrough news — GARDEN + SPACESHIP
    {"url": "https://futurecrunch.com/feed/",
     "name": "Future Crunch"},
    # Global justice, commons, decolonisation — ASSEMBLY
    {"url": "https://www.tni.org/en/rss.xml",
     "name": "Transnational Institute"},

    # ── More quality outlets ────────────────────────────────────────────────
    # Stories proving rapid change is already happening — GARDEN + ASSEMBLY
    {"url": "https://rapidtransition.org/feed/",
     "name": "Rapid Transition Alliance"},
    # Climate movement, fossil fuel divestment — ASSEMBLY + GARDEN
    {"url": "https://350.org/feed/",
     "name": "350.org"},
    # Environmental law + litigation news — ASSEMBLY + GARDEN
    {"url": "https://earthjustice.org/feeds/blog",
     "name": "Earthjustice"},
    # Conservation science journalism (Center for Biological Diversity)
    {"url": "https://therevelator.org/feed/",
     "name": "The Revelator"},
    # Earth system science — Columbia Climate School
    {"url": "https://news.climate.columbia.edu/feed/",
     "name": "State of the Planet"},
    # Global environmental research and solutions — GARDEN + SPACESHIP
    {"url": "https://www.wri.org/feed",
     "name": "World Resources Institute"},

    # ── Substack — extended set (second wave) ──────────────────────────────
    # ASSEMBLY + GARDEN: degrowth economics
    {"url": "https://jasonhickel.substack.com/feed",
     "name": "Jason Hickel"},
    # MYSTERIES + SPACESHIP: worldview transformation — Patterning Instinct author
    {"url": "https://jeremylent.substack.com/feed",
     "name": "Jeremy Lent"},
    # SPACESHIP + ASSEMBLY: polycrisis political economy
    {"url": "https://adamtooze.substack.com/feed",
     "name": "Chartbook (Adam Tooze)"},
    # GARDEN + ASSEMBLY: ecology and politics — Guardian columnist
    {"url": "https://www.monbiot.com/feed/",
     "name": "George Monbiot"},
    # GARDEN + ASSEMBLY: transition towns movement blog
    {"url": "https://transitionnetwork.org/feed/",
     "name": "Transition Network"},
    # SPACESHIP + ASSEMBLY: systems analysis, polycrisis — Planet: Critical
    {"url": "https://racheldonaldwriter.substack.com/feed",
     "name": "Planet: Critical (Rachel Donald)"},
    # SPACESHIP + MYSTERIES: biophysical economics, energy limits
    {"url": "https://www.thegreatsimplification.com/feed",
     "name": "The Great Simplification (Nate Hagens)"},
    # MYSTERIES + GARDEN: Indigenous land songs, regeneration
    {"url": "https://lylajune.substack.com/feed",
     "name": "Lyla June Johnston"},
    # SPACESHIP + GARDEN: low-tech, pre-industrial solutions journalism
    {"url": "https://solar.lowtechmagazine.com/feeds/all-articles.html",
     "name": "Low-Tech Magazine"},

    # ── YouTube channels (expanded) ────────────────────────────────────────
    # Earth history, evolution, paleontology — worldview-shifting at planetary scale
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCzR-rom72CDW_8yKkAFuF3g",
     "name": "PBS Eons", "kind": "youtube"},
    # Animated science — passes breakthrough rubric rarely but memorably
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCsXVk37bltHxD1rDPwtNM8Q",
     "name": "Kurzgesagt", "kind": "youtube"},
]


# ── YouTube URL helper ───────────────────────────────────────────────────────

YOUTUBE_VIDEO_ID_RE = re.compile(
    r"(?:v=|/watch\?v=|youtu\.be/|/embed/|/v/)([A-Za-z0-9_-]{11})"
)

def youtube_video_id(url: str) -> str:
    """Extract the YouTube video ID from a watch/embed URL. Empty if none."""
    if not url:
        return ""
    m = YOUTUBE_VIDEO_ID_RE.search(url)
    return m.group(1) if m else ""

# Keyword pre-filter — only articles containing one of these strings
# (case-insensitive) pass to Claude. Keeps API cost minimal.
# Bias toward solution/practice/governance terms; avoid bare crisis terms
# (e.g. "biodiversity loss" or "climate crisis" without a response frame).
KEYWORDS = [
    # Ecological practice / transition
    "agroecology", "rewilding", "rights of nature", "rights of the",
    "food sovereignty", "planetary boundaries",
    "regenerative", "bioregion", "ecocide",
    "ecosystem restoration", "ecological restoration",
    "land rights", "ocean governance", "water governance",
    "seed sovereignty", "agroforestry", "permaculture",
    "community land trust", "biocultural", "nature-based solution",
    "indigenous land stewardship", "indigenous land management",
    "food system transition", "food system transformation",
    "marine protected", "ocean commons",
    # Governance / democracy
    "citizens assembly", "citizen assembly", "citizens' assembly",
    "deliberative democracy", "sortition", "digital democracy",
    "participatory budget", "participatory governance",
    "climate assembly", "global governance reform",
    "degrowth", "post-growth", "wellbeing economy",
    "commons governance", "metagovernance", "earth governance",
    "planetary governance", "collective intelligence",
    "cooperative governance", "commons-based",
    "just transition", "doughnut economics",
    "transition towns", "community resilience",
    # Systems / civic tech
    "civic tech", "open data", "digital twin",
    "satellite monitoring", "blockchain governance",
    # Cultural / futures
    "experiential futures", "futures literacy",
    # Indigenous arts / culture / embodied knowledge (MYSTERIES)
    "indigenous knowledge", "indigenous art", "indigenous music",
    "indigenous dance", "ceremonial", "ritual practice",
    "ancestral practice", "first nations", "traditional ecological",
    "biocultural heritage", "ethnobotany", "elders",
    # Sensing the living world (SPACESHIP + GARDEN)
    "animal communication", "interspecies communication",
    "biosemiotics", "biosignal", "bioacoustics",
    "ai for biodiversity", "ai for conservation",
    "ecosystem sensing", "environmental dna", "edna",
    "mycelial network", "mycorrhizal", "plant intelligence",
    "whale communication", "cetacean", "decoded",
    "deep sea discovery", "biosphere monitoring",
    # Breakthrough findings about life / consciousness / Earth systems
    "scientists discover", "researchers reveal", "breakthrough study",
    "first time", "previously unknown", "rewrites",
    "challenges assumption", "new evidence",
    "consciousness research", "more-than-human",
    "astrobiology", "biosignature", "earth system science",
]

# ── Prompts ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the curator of The Orbital (theorbital.net), a solutions-focused news feed tracking the planetary systems governance movement — the slow global shift toward regenerative, participatory, ecologically grounded governance.

CRITICAL EDITORIAL PRINCIPLE: The Orbital covers SOLUTIONS, RESPONSES, INITIATIVES, and BREAKTHROUGH KNOWLEDGE — not the crisis itself. An article about a new citizens assembly on biodiversity belongs here. An article reporting biodiversity loss statistics does not. When in doubt, ask: "Is this article primarily about something being built, practiced, decided, transformed, or genuinely newly understood?" If the primary angle is documenting damage, sounding an alarm, or reporting failure, exclude it.

TWO-TIER FEED: every relevant article is classified into one of two tiers.

- "main" → top-tier feature material. Use for articles that clearly meet at least one of: (a) a new governance initiative / legal ruling / institutional experiment with real actors; (b) a breakthrough discovery meeting the science rubric below; (c) a deliberative process with concrete outcomes; (d) a regenerative practice scaling visibly; (e) embodied indigenous knowledge presented as a way of knowing; (f) an article that genuinely changes how a reader would think about planetary governance.

- "stream" → relevant context. Use for articles that fit the planetary-governance theme but are not main-feed-tier: commentary, smaller-scale practice notes, niche policy detail, evergreen explainers, opinion pieces grounded in real practice, repackaging of ideas already in our feed. They show up on /stream but not on the homepage.

Be honest. Most relevant articles are stream-tier. Main is the highlight reel.

The feed uses four "orientations" as lenses:
- GARDEN: How do we tend living systems? (agroecology, rewilding, rights of nature, soil, food sovereignty, indigenous land stewardship, ocean commons, ecosystem restoration)
- SPACESHIP: How do we build, model, and SENSE the systems? (AI for governance, digital twins, satellite monitoring, open data protocols, civic tech, systems thinking, climate modelling tools — and now: tools/research that let us perceive ecosystems we couldn't before, e.g. animal communication AI, mycelial networks, bioacoustics, environmental DNA)
- MYSTERIES: How do we transform culture and consciousness? (LARP, megagames, ritual design, experiential futures, festival culture, theatre, ceremony, inner work, narrative — AND indigenous arts, music, dance, ceremonial practice, embodied knowledge transmission)
- ASSEMBLY: How do we decide together? (citizens assemblies, deliberative democracy, sortition, rights of nature legal frameworks, global governance reform, commons governance, participatory budgeting)

BREAKTHROUGH SCIENCE RUBRIC (when evaluating science articles):
Include a science article ONLY if at least one is true:
✓ NEW PERCEPTION: AI/sensors revealing something we couldn't see before (whale syntax decoded, mycelial signaling mapped, deep-sea community sequenced, plant electrical signaling)
✓ WORLDVIEW SHIFT: a finding that changes how we understand life or Earth systems — not "X is bigger than we thought" but "X turns out to communicate / be agentic / form a network / behave in a way we didn't know was possible"
✓ GOVERNANCE HOOK: a discovery that gives stewardship or rights-of-nature work a new lever (a species turns out to be a keystone, a forest turns out to predate a nation, a contested ecosystem proves to be communicating)

Exclude science articles that are:
✗ Routine "study finds X correlates with Y" papers
✗ Pure tech milestones with no biosphere/governance application (LLM benchmarks, quantum chips, rocket launches)
✗ Hard cosmology / particle physics with no ecological angle
✗ Climate damage reporting (separate "no problem-only" rule)

INDIGENOUS ARTS / EMBODIED KNOWLEDGE (MYSTERIES):
Include performance, music, dance, ceremony, oral tradition, or art when it is presented as a way of knowing or transmitting ecological/relational understanding. Examples: hoop dance preserving cosmology, song-lines encoding land knowledge, ceremonial practice tied to seasons or ecosystems. Exclude general arts coverage that doesn't connect to land, lineage, or worldview.

Orientation assignment rules:
- Rights of nature LEGAL work → GARDEN + ASSEMBLY
- Citizens assembly process → ASSEMBLY primary; add GARDEN if topic is ecological
- Regenerative farming → GARDEN only, unless policy angle (add ASSEMBLY)
- Indigenous knowledge holders → GARDEN + MYSTERIES (not ASSEMBLY unless doing governance advocacy)
- Indigenous arts / dance / song / ceremony → MYSTERIES primary; add GARDEN if land-relational
- Climate science research → SPACESHIP + GARDEN (not ASSEMBLY unless governance-focused)
- Animal communication AI / bioacoustics / sensing → SPACESHIP + GARDEN
- Mycelial networks / plant intelligence research → GARDEN + SPACESHIP (+ MYSTERIES if it shifts worldview)
- Consciousness research / more-than-human philosophy → MYSTERIES (+ SPACESHIP if it's instrumented research)
- Digital democracy tools → SPACESHIP + ASSEMBLY
- Polycrisis / systems collapse → SPACESHIP primary (only if solution-oriented, e.g. resilience design)
- Cultural/narrative/inner work around ecology → MYSTERIES + GARDEN

You respond ONLY with valid JSON. No preamble, no explanation outside the JSON."""

ENTRY_PROMPT = """Evaluate this article for The Orbital feed:

Title: {title}
Source: {source}
URL: {url}
Description: {description}

Respond with JSON in EXACTLY this format:

If RELEVANT (main-tier — strict, see system prompt):
{{
  "include": true,
  "tier": "main",
  "slug": "kebab-case-slug-max-60-chars",
  "summary": "1-2 sentence summary, 120-160 chars, factual and specific — what happened, what was decided, what was built, or what is being practiced",
  "insight": "One sentence: why this matters for planetary governance — specific implication, not a restatement of the summary",
  "orientations": ["GARDEN"],
  "tags": ["tag-1", "tag-2", "tag-3", "tag-4"]
}}

If RELEVANT but not main-tier (stream — context, commentary, smaller scope):
{{
  "include": true,
  "tier": "stream",
  "slug": "kebab-case-slug-max-60-chars",
  "summary": "...",
  "insight": "...",
  "orientations": ["..."],
  "tags": ["..."]
}}

If NOT relevant:
{{"include": false}}

INCLUSION TEST — include ONLY if the article is primarily about one of:
✓ A new governance initiative, policy, legal ruling, or institutional experiment
✓ A community, cooperative, or commons-based practice in action
✓ A deliberative or participatory process (assembly, sortition, co-design)
✓ A regenerative or ecological practice being adopted or scaled
✓ A tool, platform, or methodology for better collective decision-making
✓ Research on what works — evidence for transition pathways
✓ A rights-of-nature case, ruling, or advocacy campaign
✓ A BREAKTHROUGH discovery about life / Earth systems that meets the rubric in the system prompt: new perception capability, worldview shift, or governance hook (apply this filter strictly — most science papers do NOT qualify)
✓ Indigenous arts / music / dance / ceremony / oral tradition presented as embodied knowledge of land, lineage, or worldview

EXCLUSION TEST — exclude if the article is primarily about:
✗ Documenting ecological damage, species loss, or climate statistics without a response frame
✗ Reporting failure, rollback, or political obstruction without a constructive angle
✗ General alarm-raising or crisis framing with no concrete initiative
✗ Corporate greenwashing or PR without substantive governance/practice content
✗ Policy proposals that are purely speculative with no real actor behind them
✗ Routine science: incremental findings, "X correlates with Y", confirmatory studies
✗ Pure tech / physics / cosmology with no biosphere or governance application
✗ General arts/culture coverage that doesn't connect to land, lineage, or worldview

Other rules:
- slug: derived from title, lowercase, hyphens only, max 60 chars
- summary: what is concretely happening, not vague ("X community launched Y, which does Z")
- insight: forward-looking ("This shows that X is now possible at Y scale")
- orientations: 1-3 values from [GARDEN, SPACESHIP, MYSTERIES, ASSEMBLY]
- tags: 4-6 lowercase kebab-case strings, specific (prefer "rights-of-nature" over "environment")"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].rstrip("-")


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_og_image(url: str) -> str:
    """Fetch og:image from a URL. Returns empty string on failure."""
    try:
        headers = {
            "User-Agent": "TheOrbital/1.0 (https://theorbital.net)",
            "Accept": "text/html",
        }
        r = requests.get(url, timeout=12, headers=headers)
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r.text, re.IGNORECASE
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r.text, re.IGNORECASE
            )
        return match.group(1).strip() if match else ""
    except Exception:
        return ""


def is_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)


def load_news() -> tuple[list, set]:
    with open(NEWS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    slugs = {item["slug"] for item in data}
    return data, slugs


def load_existing_urls() -> set:
    with open(NEWS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {item.get("sourceUrl", "") for item in data}


# ── Main logic ───────────────────────────────────────────────────────────────

def _fetch_one_feed(feed_info: dict, cutoff: datetime) -> tuple:
    """Fetch and keyword-filter one feed. Returns ((name, total, matched), candidates).
    Designed to run in a thread; no shared mutable state.
    """
    feed_name = feed_info["name"]
    feed_kind = feed_info.get("kind", "article")
    candidates: list = []
    try:
        feed = feedparser.parse(feed_info["url"])
        if feed.bozo and not feed.entries:
            return ((feed_name, 0, 0, "parse error"), [])

        total_recent = 0
        matched = 0
        for entry in feed.entries:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if not pub:
                continue
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue

            total_recent += 1
            url = entry.get("link", "").strip()
            if not url:
                continue

            title = strip_html(entry.get("title", ""))
            description = strip_html(
                entry.get("summary", "") or entry.get("description", "")
            )[:600]

            if not is_relevant(f"{title} {description}"):
                continue

            candidates.append({
                "title": title,
                "url": url,
                "date": pub_dt.strftime("%Y-%m-%d"),
                "description": description,
                "source": feed_name,
                "kind": feed_kind,
            })
            matched += 1

        return ((feed_name, total_recent, matched, None), candidates)
    except Exception as e:
        return ((feed_name, 0, 0, str(e)), [])


def fetch_candidates(cutoff: datetime, existing_urls: set) -> list:
    """Fetch and keyword-filter new articles from all RSS feeds, in parallel.
    feedparser releases the GIL during network I/O so threads work well here.
    """
    # 16 workers ≈ all 100 feeds in 6-7 staggered batches; gentle on remote hosts.
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(lambda f: _fetch_one_feed(f, cutoff), RSS_FEEDS))

    # Dedupe candidates against existing URLs and across feeds (some feeds
    # republish each other's content)
    seen_urls = set(existing_urls)
    candidates: list = []
    for _, feed_candidates in results:
        for c in feed_candidates:
            if c["url"] in seen_urls:
                continue
            seen_urls.add(c["url"])
            candidates.append(c)

    # Per-feed summary (sorted by matched desc so the productive feeds surface first)
    feed_stats = sorted(
        (r[0] for r in results),
        key=lambda s: (-s[2], s[0])
    )
    print("\nFeed results (recent entries / keyword matches):")
    for name, total, matched, err in feed_stats:
        if err:
            print(f"  ✗ {name}: {err}")
        else:
            marker = "✓" if matched > 0 else "·"
            print(f"  {marker} {name}: {total} recent, {matched} matched")

    candidates.sort(key=lambda c: c["date"], reverse=True)
    return candidates


def generate_entry(client: anthropic.Anthropic, candidate: dict) -> dict | None:
    """Call Claude Haiku to evaluate and structure an article."""
    prompt = ENTRY_PROMPT.format(
        title=candidate["title"],
        source=candidate["source"],
        url=candidate["url"],
        description=candidate["description"],
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=450,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        text = re.sub(r"^```json?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  Claude API error: {e}")
        return None


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    print(f"The Orbital — feed updater")
    print(f"Lookback: {LOOKBACK_DAYS} days (since {cutoff.strftime('%Y-%m-%d')})")
    print(f"Sources:  {len(RSS_FEEDS)}")
    print(f"Max candidates: {MAX_CANDIDATES}, max new entries: {MAX_NEW_ENTRIES}\n")

    existing_news, existing_slugs = load_news()
    existing_urls = load_existing_urls()

    candidates = fetch_candidates(cutoff, existing_urls)
    print(f"\n{len(candidates)} keyword-matching candidates\n")

    if not candidates:
        print("Nothing new — done.")
        return 0

    candidates = candidates[:MAX_CANDIDATES]

    new_entries = []
    added_slugs = set(existing_slugs)

    for candidate in candidates:
        if len(new_entries) >= MAX_NEW_ENTRIES:
            break

        print(f"Evaluating: {candidate['title'][:65]}")
        result = generate_entry(client, candidate)
        if not result:
            print("  → skipped (API error)")
            continue
        if not result.get("include"):
            print("  → not relevant")
            continue

        slug = result.get("slug") or slugify(candidate["title"])
        base_slug = slug[:55]
        final_slug = base_slug
        suffix = 2
        while final_slug in added_slugs:
            final_slug = f"{base_slug}-{suffix}"
            suffix += 1

        is_youtube = candidate.get("kind") == "youtube"
        if is_youtube:
            video_id = youtube_video_id(candidate["url"])
            if not video_id:
                print("  → skipped (no YouTube videoId in URL)")
                continue
            image = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        else:
            image = get_og_image(candidate["url"])

        tier = result.get("tier", "main")
        if tier not in ("main", "stream"):
            tier = "main"

        entry = {
            "slug": final_slug,
            "tier": tier,
            "title": candidate["title"],
            "date": candidate["date"],
            "image": image,
            "imageAlt": candidate["title"][:120],
            "summary": result.get("summary", ""),
            "body": "",
            "insight": result.get("insight", ""),
            "actors": [],
            "tags": result.get("tags", []),
            "orientations": result.get("orientations", ["GARDEN"]),
            "sourceUrl": candidate["url"],
            "source": candidate.get("source", ""),
        }
        if is_youtube:
            entry["kind"] = "video"
            entry["videoId"] = video_id

        new_entries.append(entry)
        added_slugs.add(final_slug)
        print(f"  → [{tier:>6}] [{', '.join(entry['orientations'])}] {final_slug}")

    if not new_entries:
        print("\nNo entries passed the relevance filter — done.")
        return 0

    # Combine, dedupe defensively by slug and sourceUrl, then sort
    # by date desc / slug so the feed is always chronological.
    combined = new_entries + existing_news
    seen_slugs = set()
    seen_urls = set()
    deduped = []
    for e in combined:
        slug = e.get("slug", "")
        url = e.get("sourceUrl", "")
        if slug and slug in seen_slugs:
            continue
        if url and url in seen_urls:
            continue
        if slug:
            seen_slugs.add(slug)
        if url:
            seen_urls.add(url)
        deduped.append(e)
    deduped.sort(key=lambda e: (e.get("date", ""), e.get("slug", "")), reverse=True)

    with open(NEWS_JSON, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Added {len(new_entries)} entries:")
    for e in new_entries:
        print(f"  {e['date']}  {e['slug']}")

    return len(new_entries)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
