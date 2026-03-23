#!/usr/bin/env python3
"""
Step C evaluation — commit curated search results to sources and update search_phrases.

Evaluates step_c_results.json and commits genuinely relevant actors to garden.db.

STRICT INCLUSION CRITERIA:
- Actively doing something (not just talking about it)
- Work directly connects to at least one of the four orientations
- Real outputs: projects, publications, events, products, communities
- Could plausibly participate in, benefit from, or strengthen a governance LARP/simulation/assembly

STRICT EXCLUSION CRITERIA:
- Purely commercial with no governance/ecological/social dimension
- Defunct or inactive (no updates in 2+ years)
- Single blog post or thought piece, not an organisation/initiative
- Purely focused on AI safety/alignment debates without governance application
- Amazon book listings, Wikipedia pages, news articles
- Government departments that are just informational pages
- Generic industry associations without specific relevant work

Usage:
    python3 step_c_evaluate.py
"""
import sqlite3
import json
import os
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")
conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════
# Helper functions for committing evaluated results
# ═══════════════════════════════════════════════════════════════

def get_orientation_id(code):
    """Look up orientation ID from code (GARDEN, SPACESHIP, TEMPLE, ASSEMBLY)."""
    cur.execute("SELECT id FROM orientations WHERE code = ?", (code.upper(),))
    row = cur.fetchone()
    return row[0] if row else None


def get_category_id(name):
    """Look up category ID from name."""
    cur.execute("SELECT id FROM categories WHERE lower(name) = lower(?)", (name,))
    row = cur.fetchone()
    return row[0] if row else None


def add_source(url, title, desc, monitor=False):
    """Add a URL source to the database."""
    cur.execute("INSERT OR IGNORE INTO sources (url, title, description, monitor) VALUES (?, ?, ?, ?)",
                (url, title, desc, int(monitor)))
    cur.execute("SELECT id FROM sources WHERE url = ?", (url,))
    return cur.fetchone()[0]


def add_actor(name, type_, primary_orientation, description=None, website=None,
              domain=None, location=None, scale=None, maturity=None,
              relevance_score=3, connection=None, contact_pathway=None,
              secondary_orientation=None, categories=None, notes=None):
    """Add an actor to the database."""
    cur.execute("SELECT id FROM actors WHERE lower(name) = lower(?)", (name,))
    row = cur.fetchone()
    if row:
        print(f"  [SKIP] '{name}' already exists (id={row[0]})")
        return row[0]

    if domain:
        cur.execute("SELECT id, name FROM actors WHERE domain = ?", (domain,))
        row = cur.fetchone()
        if row:
            print(f"  [SKIP] domain '{domain}' already exists as '{row[1]}' (id={row[0]})")
            return row[0]

    primary_oid = get_orientation_id(primary_orientation)
    secondary_oid = get_orientation_id(secondary_orientation) if secondary_orientation else None

    cur.execute("""INSERT INTO actors
        (name, type, primary_orientation_id, secondary_orientation_id,
         description, website, domain, location, scale, maturity,
         relevance_score, connection, contact_pathway, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, type_, primary_oid, secondary_oid,
         description, website, domain, location, scale, maturity,
         relevance_score, connection, contact_pathway, notes))

    actor_id = cur.lastrowid

    if website and website != "UNKNOWN":
        sid = add_source(website, f"{name} - Official Website", f"Website for {name}")
        cur.execute("INSERT OR IGNORE INTO source_actor VALUES (?, ?)", (sid, actor_id))

    for cat_name in (categories or []):
        cat_id = get_category_id(cat_name)
        if cat_id:
            cur.execute("INSERT OR IGNORE INTO actor_category VALUES (?, ?)", (actor_id, cat_id))

    print(f"  [ADD] '{name}' ({type_}, {primary_orientation}) relevance={relevance_score}")
    return actor_id


def link_source_actor(source_id, actor_id):
    """Link a source to an actor."""
    cur.execute("INSERT OR IGNORE INTO source_actor VALUES (?, ?)", (source_id, actor_id))


def add_phrase(phrase, priority='medium', category_name=None):
    """Add a new search phrase."""
    cat_id = get_category_id(category_name) if category_name else None
    cur.execute("INSERT OR IGNORE INTO search_phrases (phrase, category_id, priority) VALUES (?, ?, ?)",
                (phrase, cat_id, priority))


def mark_searched(phrase_id, hits):
    """Mark a search phrase as searched with hit count."""
    cur.execute("UPDATE search_phrases SET last_searched = ?, hit_count = ? WHERE id = ?",
                (now, hits, phrase_id))


def add_flag(actor_id, flag_type, notes=None):
    """Flag an actor for special attention."""
    cur.execute("INSERT INTO flags (actor_id, flag_type, notes) VALUES (?, ?, ?)",
                (actor_id, flag_type, notes))


# ═══════════════════════════════════════════════════════════════
# CURATED ACTORS FROM step_c_results.json EVALUATION
#
# Reviewed 1,430 results across 143 phrases.
# Applied strict inclusion/exclusion criteria.
# Target: 20-40 genuinely relevant new actors.
# ═══════════════════════════════════════════════════════════════

print("=" * 60)
print("Step C Evaluation — Curated Actor Commits")
print("=" * 60)

# ───────────────────────────────────────────────────────────────
# GARDEN OF EDEN — Living systems, ecology, land stewardship
# ───────────────────────────────────────────────────────────────
print("\n--- GARDEN OF EDEN ---")

# Agenda Gotsch — Active syntropic farming education and practice network
# Founded by Ernst Gotsch, real demonstration farms, active training programmes
agenda_gotsch = add_actor(
    "Agenda Gotsch",
    "NGO",
    "GARDEN",
    description="Syntropic farming education and practice platform founded by Ernst Gotsch, promoting regenerative agroforestry systems through training, demonstration farms, and a global practitioner network.",
    website="https://agendagotsch.com",
    domain="agendagotsch.com",
    location="Brazil / Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: syntropic agroforestry",
    categories=["Regenerative Agriculture"],
)

# Kiss the Ground — Active NGO with film, education programmes, farmer training
kiss_the_ground = add_actor(
    "Kiss the Ground",
    "NGO",
    "GARDEN",
    description="Soil health advocacy NGO producing documentary films, running farmer training programmes, and building public awareness of regenerative agriculture as a climate solution.",
    website="https://kisstheground.com",
    domain="kisstheground.com",
    location="USA",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: regenerative farming",
    categories=["Regenerative Agriculture"],
)

# Agroecology Europe — European association connecting research, practice, policy
agroecology_europe = add_actor(
    "Agroecology Europe",
    "Network",
    "GARDEN",
    description="European association advancing agroecology through transdisciplinary research, farmer-to-farmer knowledge exchange, and policy engagement across the EU.",
    website="https://www.agroecology-europe.org",
    domain="agroecology-europe.org",
    location="Europe",
    scale="Regional",
    maturity="Established",
    relevance_score=3,
    connection="search: agroecology network",
    secondary_orientation="ASSEMBLY",
    categories=["Regenerative Agriculture"],
)

# Agroecology Coalition — Multi-stakeholder coalition for food system transformation
agroecology_coalition = add_actor(
    "Agroecology Coalition",
    "Network",
    "GARDEN",
    description="Global multi-stakeholder coalition of governments, research institutions, civil society and private sector actors advocating food system transformation through agroecology's 13 core principles.",
    website="https://agroecology-coalition.org",
    domain="agroecology-coalition.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: agroecology network",
    secondary_orientation="ASSEMBLY",
    categories=["Regenerative Agriculture"],
)

# Rewilding Europe — Major European rewilding initiative, real landscape-scale projects
rewilding_europe = add_actor(
    "Rewilding Europe",
    "NGO",
    "GARDEN",
    description="Pan-European rewilding initiative operating across 10+ landscapes, reintroducing wildlife, supporting nature-based economies, and running the European Rewilding Network connecting 100+ local initiatives.",
    website="https://rewildingeurope.com",
    domain="rewildingeurope.com",
    location="Europe",
    scale="Regional",
    maturity="Established",
    relevance_score=4,
    connection="search: rewilding initiative",
    categories=["Biodiversity & Ecosystem Restoration", "Nature-Based Economies"],
)

# Global Rewilding Alliance — International coordination network for rewilding
global_rewilding = add_actor(
    "Global Rewilding Alliance",
    "Network",
    "GARDEN",
    description="International alliance coordinating rewilding efforts across continents, advocating for rewilding as climate policy and bridging biodiversity and climate agendas.",
    website="https://globalrewilding.earth",
    domain="globalrewilding.earth",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: rewilding initiative",
    secondary_orientation="ASSEMBLY",
    categories=["Biodiversity & Ecosystem Restoration"],
)

# Ecosystem Restoration Communities — Global movement building restoration communities
erc = add_actor(
    "Ecosystem Restoration Communities",
    "Movement",
    "GARDEN",
    description="Global movement building community-led ecosystem restoration projects from Brazil to Morocco, connecting local action with the UN Decade on Ecosystem Restoration.",
    website="https://www.ecosystemrestorationcommunities.org",
    domain="ecosystemrestorationcommunities.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: ecosystem restoration",
    secondary_orientation="ASSEMBLY",
    categories=["Biodiversity & Ecosystem Restoration"],
    notes="Strong community governance dimension - restoration as participatory practice.",
)

# IIED Biocultural Heritage — Research and practice on biocultural heritage territories
iied_biocultural = add_actor(
    "IIED Biocultural Heritage",
    "Research",
    "GARDEN",
    description="International Institute for Environment and Development research programme on biocultural heritage, bridging indigenous knowledge systems, biodiversity conservation, and community rights.",
    website="https://biocultural.iied.org",
    domain="biocultural.iied.org",
    location="UK / Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: biocultural heritage",
    secondary_orientation="ASSEMBLY",
    categories=["Indigenous Land Stewardship"],
)

# Grounded Solutions Network / Community Land Trust movement
grounded_solutions = add_actor(
    "Grounded Solutions Network",
    "Network",
    "GARDEN",
    description="National network supporting community land trusts and shared equity housing, advancing community ownership models that keep land in common stewardship.",
    website="https://groundedsolutions.org",
    domain="groundedsolutions.org",
    location="USA",
    scale="National",
    maturity="Established",
    relevance_score=3,
    connection="search: community land trust",
    secondary_orientation="ASSEMBLY",
    categories=["Community Land Trusts & Commons"],
)

# Alliance for Water Stewardship — Global water governance standard
aws = add_actor(
    "Alliance for Water Stewardship",
    "Network",
    "GARDEN",
    description="Global multi-stakeholder network operating the International Water Stewardship Standard, engaging industry, civil society and governments in collective water governance.",
    website="https://a4ws.org",
    domain="a4ws.org",
    location="Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: water stewardship",
    secondary_orientation="ASSEMBLY",
    categories=["Water & Ocean Stewardship"],
)

# Capital Institute — Regenerative economics think tank
capital_institute = add_actor(
    "Capital Institute",
    "Research",
    "GARDEN",
    description="Think tank developing the theory and practice of regenerative economics, publishing the '8 Principles of a Regenerative Economy' framework and the Finance for a Regenerative World paper series.",
    website="https://capitalinstitute.org",
    domain="capitalinstitute.org",
    location="USA",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: regenerative economy",
    secondary_orientation="SPACESHIP",
    categories=["Nature-Based Economies"],
    notes="John Fullerton's work directly intersects with Doughnut Economics and systems thinking.",
)

# Global Alliance for the Rights of Nature (GARN)
garn = add_actor(
    "Global Alliance for the Rights of Nature",
    "Network",
    "GARDEN",
    description="International network advancing rights of nature through legal frameworks, hosting International Rights of Nature Tribunals, and supporting community-led campaigns for ecosystem legal personhood.",
    website="https://www.garn.org",
    domain="garn.org",
    location="Global",
    scale="Global",
    maturity="Established",
    relevance_score=5,
    connection="search: rights of nature",
    secondary_orientation="ASSEMBLY",
    categories=["Rights of Nature"],
    notes="Directly relevant to Garden's governance innovation dimension. Hosts tribunals that are a form of governance simulation.",
)
add_flag(garn, "close_vision", "Rights of Nature tribunals are a form of governance performance/simulation")

# Earth Law Center — Legal rights for nature
earth_law_center = add_actor(
    "Earth Law Center",
    "NGO",
    "GARDEN",
    description="Legal advocacy organisation advancing rights of nature through drafting legislation, supporting court cases, and developing the Universal Declaration of River Rights.",
    website="https://www.earthlawcenter.org",
    domain="earthlawcenter.org",
    location="USA / Global",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: river rights",
    secondary_orientation="ASSEMBLY",
    categories=["Rights of Nature"],
)

# Gaia Foundation — Earth jurisprudence and seed sovereignty
gaia_foundation = add_actor(
    "Gaia Foundation",
    "NGO",
    "GARDEN",
    description="UK-based foundation advancing earth jurisprudence, seed sovereignty, and community ecological governance across Africa and South America. Pioneers of the 'earth jurisprudence' legal-philosophical framework.",
    website="https://gaiafoundation.org",
    domain="gaiafoundation.org",
    location="UK / Africa / South America",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: earth jurisprudence",
    secondary_orientation="ASSEMBLY",
    categories=["Rights of Nature", "Indigenous Land Stewardship"],
)


# ───────────────────────────────────────────────────────────────
# SPACESHIP EARTH — Technology, infrastructure, governance tools
# ───────────────────────────────────────────────────────────────
print("\n--- SPACESHIP EARTH ---")

# Open Data Cube — Open source earth observation infrastructure
open_data_cube = add_actor(
    "Open Data Cube",
    "Research",
    "SPACESHIP",
    description="Open-source geospatial data management and analysis platform enabling governments and researchers to process and analyse satellite earth observation data at national scale.",
    website="https://www.opendatacube.org",
    domain="opendatacube.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: open source earth observation",
    categories=["Open Earth Data & Satellite Intelligence"],
)

# Single.Earth — Nature-backed digital currency
single_earth = add_actor(
    "Single.Earth",
    "Company",
    "SPACESHIP",
    description="Estonian startup creating nature-backed digital tokens (MERIT) that represent verified ecosystem services, building an economic system where preserving nature is more profitable than destroying it.",
    website="https://www.single.earth",
    domain="single.earth",
    location="Estonia",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: nature-based currency, ecological token",
    secondary_orientation="GARDEN",
    categories=["Blockchain & Regenerative Finance (ReFi)"],
    notes="Directly bridges ecological value and economic systems via blockchain.",
)

# Toucan Protocol — Tokenised carbon credits infrastructure
toucan = add_actor(
    "Toucan Protocol",
    "Company",
    "SPACESHIP",
    description="Web3 infrastructure bringing carbon credits on-chain, enabling transparent and programmable carbon markets through tokenisation of verified environmental assets.",
    website="https://blog.toucan.earth",
    domain="toucan.earth",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: carbon credit blockchain",
    secondary_orientation="GARDEN",
    categories=["Blockchain & Regenerative Finance (ReFi)"],
)

# Liquid Democracy e.V. (liqd.net) — Participatory democracy software
liqd = add_actor(
    "Liquid Democracy e.V.",
    "NGO",
    "SPACESHIP",
    description="Berlin-based nonprofit developing open-source digital participation tools including Adhocracy, enabling liquid democracy and deliberative processes for governments and civil society.",
    website="https://liqd.net",
    domain="liqd.net",
    location="Germany",
    scale="Regional",
    maturity="Established",
    relevance_score=4,
    connection="search: liquid democracy",
    secondary_orientation="ASSEMBLY",
    categories=["Decentralised Governance Tech", "Participatory Democracy Movements"],
)
add_flag(liqd, "close_vision", "Building the exact type of governance infrastructure The Garden needs")

# Participatory Budgeting Project — US-based PB movement org
pb_project = add_actor(
    "Participatory Budgeting Project",
    "NGO",
    "SPACESHIP",
    description="Leading US organisation advancing participatory budgeting as a democratic practice, having supported over 400 PB processes and helped allocate hundreds of millions in public funds through direct citizen decision-making.",
    website="https://www.participatorybudgeting.org",
    domain="participatorybudgeting.org",
    location="USA",
    scale="National",
    maturity="Established",
    relevance_score=3,
    connection="search: participatory budgeting platform",
    secondary_orientation="ASSEMBLY",
    categories=["Participatory Democracy Movements"],
)

# Metagov — Governance research and tools community
metagov = add_actor(
    "Metagov",
    "Research",
    "SPACESHIP",
    description="Research collective studying and building interoperable governance tools for online communities, exploring governance games and tool experimentation across digital and physical spaces.",
    website="https://metagov.org",
    domain="metagov.org",
    location="USA / Global",
    scale="Global",
    maturity="Active",
    relevance_score=5,
    connection="search: governance megagame",
    secondary_orientation="TEMPLE",
    categories=["Decentralised Governance Tech", "Transformative Game Design & LARP"],
    notes="Metagov directly experiments with governance through play and simulation. Extremely close to Garden's vision.",
)
add_flag(metagov, "close_vision", "Governance games + tool experimentation directly aligns with Garden's LARP/simulation approach")

# Gaia AI (forest management) — AI-powered forest monitoring
gaia_ai = add_actor(
    "Gaia AI",
    "Company",
    "SPACESHIP",
    description="AI-powered forest management platform providing satellite-derived insights on forest health, carbon stocks, and biodiversity metrics to support data-driven conservation decisions.",
    website="https://www.gaia-ai.eco",
    domain="gaia-ai.eco",
    location="UK",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: Gaia AI",
    secondary_orientation="GARDEN",
    categories=["AI for Planetary Governance", "Open Earth Data & Satellite Intelligence"],
)

# steward-ownership.com — Knowledge hub for alternative ownership models
steward_ownership = add_actor(
    "Steward Ownership",
    "Network",
    "SPACESHIP",
    description="Knowledge platform and network promoting steward-ownership as an alternative corporate model where companies are self-owned, profits serve purpose, and control stays with active stewards rather than passive investors.",
    website="https://steward-ownership.com",
    domain="steward-ownership.com",
    location="Europe",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: steward ownership",
    secondary_orientation="ASSEMBLY",
    categories=["Steward Ownership & Alternative Corporate Models"],
    notes="Complements Purpose Foundation (already in DB) with broader network perspective.",
)


# ───────────────────────────────────────────────────────────────
# ELEUSINIAN MYSTERIES — Games, ritual, experience, transformation
# ───────────────────────────────────────────────────────────────
print("\n--- ELEUSINIAN MYSTERIES ---")

# Not Only Larp — Immersive experiences for social change
not_only_larp = add_actor(
    "Not Only Larp",
    "Company",
    "TEMPLE",
    description="Italian design studio creating immersive LARP experiences explicitly for social change, running large-scale educational and political LARPs across Europe.",
    website="https://notonlylarp.com",
    domain="notonlylarp.com",
    location="Italy",
    scale="Regional",
    maturity="Active",
    relevance_score=5,
    connection="search: LARP social change",
    secondary_orientation="ASSEMBLY",
    categories=["Transformative Game Design & LARP"],
    notes="Directly creating LARPs for social/political transformation. Core to Garden's vision.",
)
add_flag(not_only_larp, "close_vision", "LARPs for social change are exactly what Garden envisions")
add_flag(not_only_larp, "event_opportunity", "Runs large-scale political LARPs where Garden concepts could be integrated")

# Megagame Assembly — Community hub for megagame design and play
megagame_assembly = add_actor(
    "Megagame Assembly",
    "Network",
    "TEMPLE",
    description="International community hub for megagame design and play, connecting designers and organisers of large-scale multi-player simulation games that blend strategy, diplomacy, and governance.",
    website="https://www.megagameassembly.com",
    domain="megagameassembly.com",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: megagame",
    secondary_orientation="ASSEMBLY",
    categories=["Megagames & Civilisational Simulation"],
)
add_flag(megagame_assembly, "event_opportunity", "Megagame events as platform for Garden governance simulations")

# Megagame Coalition — US-based megagame network
megagame_coalition = add_actor(
    "Megagame Coalition",
    "Network",
    "TEMPLE",
    description="US-based network of megagame organisers collaborating on large-scale simulation game design, production, and community building across North America.",
    website="https://megagamecoalition.com",
    domain="megagamecoalition.com",
    location="USA",
    scale="National",
    maturity="Active",
    relevance_score=3,
    connection="search: governance megagame",
    categories=["Megagames & Civilisational Simulation"],
)

# World Game Workshop — Carrying forward Buckminster Fuller's World Game
world_game_workshop = add_actor(
    "World Game Workshop",
    "NGO",
    "TEMPLE",
    description="Organisation continuing Buckminster Fuller's World Game vision, running collaborative planetary resource simulation workshops that challenge participants to 'make the world work for 100% of humanity'.",
    website="https://worldgameworkshop.org",
    domain="worldgameworkshop.org",
    location="USA",
    scale="Global",
    maturity="Active",
    relevance_score=5,
    connection="search: World Game Buckminster Fuller",
    secondary_orientation="ASSEMBLY",
    categories=["Megagames & Civilisational Simulation"],
    notes="Direct ancestor of what Garden is building. Governance simulation at planetary scale.",
)
add_flag(world_game_workshop, "close_vision", "Buckminster Fuller's World Game is a direct precursor to The Garden's vision")

# Ritual Design Lab — Designing secular rituals for meaning-making
ritual_design_lab = add_actor(
    "Ritual Design Lab",
    "Research",
    "TEMPLE",
    description="Research and design practice developing methodologies for creating contemporary secular rituals, providing toolkits and frameworks for bringing meaning into experience and service design.",
    website="https://www.ritualdesignlab.org",
    domain="ritualdesignlab.org",
    location="USA",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: contemporary ritual design",
    categories=["Ritual & Ceremony Design"],
    notes="Toolkit approach to ritual design is directly applicable to Garden's ceremony/experience layer.",
)

# Beckley Foundation — Psychedelic science and drug policy reform
beckley_foundation = add_actor(
    "Beckley Foundation",
    "Research",
    "TEMPLE",
    description="UK-based research foundation pioneering scientific research into psychedelics and consciousness, while advocating evidence-based drug policy reform globally.",
    website="https://www.beckleyfoundation.org",
    domain="beckleyfoundation.org",
    location="UK",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: psychedelic research governance",
    secondary_orientation="ASSEMBLY",
    categories=["Psychedelic & Consciousness Research"],
)

# Superflux — Speculative design studio working on futures
superflux = add_actor(
    "Superflux",
    "Company",
    "TEMPLE",
    description="Award-winning speculative design studio creating immersive installations and experiential futures that make abstract challenges like climate change tangible through embodied experience.",
    website="https://superflux.in",
    domain="superflux.in",
    location="UK / India",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: speculative design, experiential futures",
    secondary_orientation="ASSEMBLY",
    categories=["Experiential Futures & Design Fiction"],
    notes="Creates exactly the kind of embodied future experiences Garden aims to produce.",
)
add_flag(superflux, "close_vision", "Immersive experiential futures installations directly align with Garden's approach")

# Institute for the Future (IFTF) — Experiential futures training
iftf = add_actor(
    "Institute for the Future",
    "Research",
    "TEMPLE",
    description="50+ year old futures research institute running experiential futures training, foresight research, and large-scale public forecasting exercises combining gameplay with futures thinking.",
    website="https://www.iftf.org",
    domain="iftf.org",
    location="USA",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: experiential futures",
    secondary_orientation="ASSEMBLY",
    categories=["Experiential Futures & Design Fiction"],
)

# Theatre of the Oppressed NYC — Active political theatre practice
to_nyc = add_actor(
    "Theatre of the Oppressed NYC",
    "NGO",
    "TEMPLE",
    description="New York-based community organisation using Augusto Boal's Theatre of the Oppressed methods for civic engagement, running participatory theatre workshops that explore governance and social justice through embodied performance.",
    website="https://www.tonyc.nyc",
    domain="tonyc.nyc",
    location="USA",
    scale="Local",
    maturity="Established",
    relevance_score=4,
    connection="search: Theatre of the Oppressed",
    secondary_orientation="ASSEMBLY",
    categories=["Arts & Performance for Social Change"],
    notes="Theatre of the Oppressed is a direct precursor to governance LARP — performing alternative realities to explore power.",
)


# ───────────────────────────────────────────────────────────────
# GENERAL ASSEMBLY OF EARTH — Global governance, democracy, justice
# ───────────────────────────────────────────────────────────────
print("\n--- GENERAL ASSEMBLY OF EARTH ---")

# Global Governance Innovation Network (GGIN) / Stimson Center
ggin = add_actor(
    "Global Governance Innovation Network",
    "Research",
    "ASSEMBLY",
    description="International research network hosted by the Stimson Center, producing annual Global Governance Innovation Reports and connecting researchers working on multilateral system reform.",
    website="https://ggin.stimson.org",
    domain="ggin.stimson.org",
    location="USA / Global",
    scale="Global",
    maturity="Established",
    relevance_score=4,
    connection="search: global governance innovation",
    categories=["Global Governance Innovation"],
)

# Centre for International Governance Innovation (CIGI)
cigi = add_actor(
    "Centre for International Governance Innovation",
    "Research",
    "ASSEMBLY",
    description="Canadian think tank conducting research on international governance, digital economy, and global security, with focus on reforming multilateral institutions for contemporary challenges.",
    website="https://www.cigionline.org",
    domain="cigionline.org",
    location="Canada",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: global governance innovation",
    categories=["Global Governance Innovation"],
)

# Sortition Foundation — Random selection for democratic assemblies
sortition_foundation = add_actor(
    "Sortition Foundation",
    "NGO",
    "ASSEMBLY",
    description="UK-based organisation promoting and running citizens' assemblies selected by sortition (random selection), having facilitated over 100 stratified random selections for democratic bodies.",
    website="https://www.sortitionfoundation.org",
    domain="sortitionfoundation.org",
    location="UK",
    scale="National",
    maturity="Established",
    relevance_score=5,
    connection="search: sortition",
    categories=["Participatory Democracy Movements"],
    notes="Core infrastructure for citizens' assemblies. Directly relevant to Garden's assembly mechanics.",
)
add_flag(sortition_foundation, "close_vision", "Sortition-based assembly selection is core to Garden's governance simulation design")

# People Powered — Global hub for participatory democracy
people_powered = add_actor(
    "People Powered",
    "Network",
    "ASSEMBLY",
    description="Global hub for participatory democracy connecting practitioners and governments, hosting the Public Participation and Deliberative Democracy Festival, and providing tools and guides for democratic innovation.",
    website="https://www.peoplepowered.org",
    domain="peoplepowered.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: participatory democracy, Theatre of the Oppressed",
    categories=["Participatory Democracy Movements"],
)
add_flag(people_powered, "event_opportunity", "Runs the Public Participation and Deliberative Democracy Festival")

# Future Generations Commissioner for Wales
fg_wales = add_actor(
    "Future Generations Commissioner for Wales",
    "Government",
    "ASSEMBLY",
    description="Statutory body established by the Well-being of Future Generations Act, the world's first independent commissioner mandated to advocate for the interests of future generations in government decisions.",
    website="https://futuregenerations.wales",
    domain="futuregenerations.wales",
    location="Wales / UK",
    scale="National",
    maturity="Established",
    relevance_score=5,
    connection="search: future generations commissioner",
    secondary_orientation="GARDEN",
    categories=["Long-termism & Future Generations"],
    notes="The only real institutional example of legally mandated long-term governance. Model for Garden.",
)
add_flag(fg_wales, "close_vision", "World's first future generations commissioner — institutional governance innovation in practice")

# THE NEW INSTITUTE — Planetary Governance programme
new_institute = add_actor(
    "THE NEW INSTITUTE",
    "Research",
    "ASSEMBLY",
    description="Hamburg-based institute running a dedicated Planetary Governance programme bringing together researchers, practitioners, and artists to develop new frameworks for governing planetary challenges.",
    website="https://thenew.institute",
    domain="thenew.institute",
    location="Germany",
    scale="Global",
    maturity="Active",
    relevance_score=5,
    connection="search: planetary governance",
    secondary_orientation="TEMPLE",
    categories=["Global Governance Innovation"],
    notes="Explicitly working on planetary governance with interdisciplinary approach including arts.",
)
add_flag(new_institute, "close_vision", "Planetary Governance programme directly mirrors Garden's ambition")

# Global Challenges Foundation — Prizes and research for governance reform
global_challenges = add_actor(
    "Global Challenges Foundation",
    "NGO",
    "ASSEMBLY",
    description="Swedish foundation offering major prizes for global governance reform proposals, funding research on existential risks and planetary commons, and building networks for institutional innovation.",
    website="https://globalchallenges.org",
    domain="globalchallenges.org",
    location="Sweden",
    scale="Global",
    maturity="Established",
    relevance_score=5,
    connection="search: planetary governance, planetary boundaries governance",
    categories=["Global Governance Innovation"],
    notes="Swedish-based. Active funder of governance innovation. Planetary commons framework.",
)
add_flag(global_challenges, "nordic_based", "Stockholm-based foundation")
add_flag(global_challenges, "funding_source", "Major prizes and grants for governance innovation proposals")
add_flag(global_challenges, "close_vision", "Planetary commons governance directly aligns with Garden's vision")

# Planetary Health Alliance — Academic and policy network
pha = add_actor(
    "Planetary Health Alliance",
    "Network",
    "ASSEMBLY",
    description="Global consortium of 400+ universities, NGOs, and government entities advancing planetary health — the interdisciplinary framework linking human health outcomes to planetary ecosystem changes.",
    website="https://planetaryhealthalliance.org",
    domain="planetaryhealthalliance.org",
    location="Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: planetary health alliance",
    secondary_orientation="GARDEN",
    categories=["Planetary Health & One Health"],
)

# Climate Justice Alliance — US climate justice coalition
cja = add_actor(
    "Climate Justice Alliance",
    "Network",
    "ASSEMBLY",
    description="US-based coalition of 90+ frontline community organisations and support groups building a just transition away from extractive systems through community-led governance and regenerative economies.",
    website="https://climatejusticealliance.org",
    domain="climatejusticealliance.org",
    location="USA",
    scale="National",
    maturity="Established",
    relevance_score=3,
    connection="search: climate justice movement",
    secondary_orientation="GARDEN",
    categories=["Climate Justice & Global South Leadership"],
)

# Learning Planet Institute — Planetary citizenship education
lpi = add_actor(
    "Learning Planet Institute",
    "Research",
    "ASSEMBLY",
    description="Paris-based institute developing educational approaches for planetary citizenship, running futures learning labs on anticipatory governance and connecting education with sustainability transformation.",
    website="https://www.learningplanetinstitute.org",
    domain="learningplanetinstitute.org",
    location="France",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: planetary citizenship education",
    secondary_orientation="TEMPLE",
    categories=["Education for Planetary Citizenship"],
    notes="Futures Learning Lab on planetary citizenship and anticipatory governance directly relevant.",
)


# ═══════════════════════════════════════════════════════════════
# VALUABLE SOURCES (not actors, but useful reference material)
# ═══════════════════════════════════════════════════════════════
print("\n--- SOURCES ---")

# Research papers and reports worth monitoring
add_source(
    "https://www.pnas.org/doi/10.1073/pnas.2301531121",
    "The planetary commons: A new paradigm for safeguarding Earth-regulating systems",
    "PNAS paper proposing planetary commons framework for Earth system governance.",
    monitor=True,
)
print("  [SOURCE] Planetary commons PNAS paper")

add_source(
    "https://ostromworkshop.indiana.edu/research/commons-governance/index.html",
    "Ostrom Workshop Commons Governance Program",
    "Research programme at Indiana University continuing Elinor Ostrom's commons governance work.",
    monitor=True,
)
print("  [SOURCE] Ostrom Workshop")

add_source(
    "https://www.nordiclarp.org/",
    "Nordic Larp online magazine",
    "Leading publication on Nordic-style LARP theory and practice.",
    monitor=True,
)
print("  [SOURCE] Nordic Larp magazine")

add_source(
    "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.571522/full",
    "Existential Transformational Game Design: Harnessing the 'Psychomagic' of Symbolic Enactment",
    "Academic paper on transformational game design frameworks.",
    monitor=False,
)
print("  [SOURCE] Transformational game design paper")

add_source(
    "https://www.transformationalframework.com/",
    "The Transformational Framework",
    "Process tool for development of transformational games — directly applicable to Garden design.",
    monitor=True,
)
print("  [SOURCE] Transformational Framework")

add_source(
    "https://citizensassemblies.org/",
    "Citizens' Assemblies portal",
    "Resource hub for citizens' assembly methodology and case studies.",
    monitor=True,
)
print("  [SOURCE] Citizens' Assemblies portal")

add_source(
    "https://www.stockholmresilience.org/research/planetary-boundaries.html",
    "Stockholm Resilience Centre - Planetary Boundaries",
    "Core research on planetary boundaries framework.",
    monitor=True,
)
print("  [SOURCE] Stockholm Resilience Centre - Planetary Boundaries")

add_source(
    "https://wiki.p2pfoundation.net/Polycentric_Governance",
    "P2P Foundation - Polycentric Governance",
    "P2P Foundation wiki entry on polycentric governance with extensive references.",
    monitor=False,
)
print("  [SOURCE] P2P Foundation polycentric governance")

add_source(
    "https://epale.ec.europa.eu/en/resource-centre/content/live-action-role-playing-larp-tool-social-change",
    "LARP as a tool for social change - European Commission EPALE",
    "EU platform article on using LARP for social change and education.",
    monitor=False,
)
print("  [SOURCE] EU EPALE LARP social change")

add_source(
    "https://globalchallenges.org/updates/planetary-commons-approach-environmental-governance/",
    "Planetary Commons Approach for Environmental Governance",
    "Global Challenges Foundation report on planetary commons governance.",
    monitor=True,
)
print("  [SOURCE] Global Challenges planetary commons report")

add_source(
    "https://github.com/publiccodenet/governance-game",
    "Governance Game - Foundation for Public Code",
    "Open-source card game for exploring governance around shared codebases.",
    monitor=True,
)
print("  [SOURCE] Public Code governance game (GitHub)")

add_source(
    "https://ritualdesign.net/",
    "Ritual Design Toolkit",
    "Open toolkit for designing secular rituals — applicable to Garden ceremony design.",
    monitor=False,
)
print("  [SOURCE] Ritual Design Toolkit")


# ═══════════════════════════════════════════════════════════════
# Mark all 143 phrases as searched with approximate hit counts
# ═══════════════════════════════════════════════════════════════
print("\n--- MARKING PHRASES AS SEARCHED ---")

# Load results to get phrase IDs and count useful hits per phrase
results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step_c_results.json")
with open(results_path) as f:
    results = json.load(f)

# Phrases that yielded actors or useful sources (approximate hit counts)
phrase_hits = {
    1: 1,   # syntropic agroforestry -> Agenda Gotsch
    2: 1,   # regenerative farming -> Kiss the Ground
    5: 2,   # agroecology network -> Agroecology Europe, Coalition
    6: 2,   # rewilding initiative -> Rewilding Europe, Global Rewilding Alliance
    8: 1,   # ecosystem restoration -> ERC
    13: 1,  # biocultural heritage -> IIED
    15: 1,  # community land trust -> Grounded Solutions
    24: 1,  # water stewardship -> AWS
    27: 1,  # regenerative economy -> Capital Institute
    46: 1,  # open source earth observation -> Open Data Cube
    50: 1,  # nature-based currency -> Single.Earth
    51: 1,  # ecological token -> (Single.Earth)
    53: 1,  # carbon credit blockchain -> Toucan
    58: 1,  # Gaia AI -> Gaia AI
    61: 1,  # liquid democracy -> liqd.net
    62: 1,  # participatory budgeting platform -> PB Project
    68: 1,  # steward ownership -> steward-ownership.com
    73: 1,  # transformative game design -> (linked to existing Uppsala entry)
    74: 1,  # LARP social change -> Not Only Larp
    78: 2,  # megagame -> Megagame Assembly, Coalition
    80: 1,  # World Game -> World Game Workshop
    81: 1,  # governance megagame -> Metagov
    82: 1,  # contemporary ritual design -> Ritual Design Lab
    86: 1,  # experiential futures -> IFTF
    88: 1,  # speculative design -> Superflux
    95: 1,  # psychedelic research governance -> Beckley Foundation
    102: 1, # Theatre of the Oppressed -> TO NYC
    109: 2, # global governance innovation -> GGIN, CIGI
    112: 1, # planetary governance -> THE NEW INSTITUTE
    116: 1, # sortition -> Sortition Foundation
    117: 1, # participatory democracy -> People Powered
    119: 2, # rights of nature -> GARN, Earth Law Center
    120: 1, # earth jurisprudence -> Gaia Foundation
    124: 1, # future generations commissioner -> FG Wales
    137: 1, # planetary health alliance -> PHA
    128: 1, # climate justice movement -> CJA
    140: 1, # planetary boundaries governance -> Global Challenges Foundation
    141: 1, # planetary citizenship education -> Learning Planet Institute
}

searched_count = 0
for item in results:
    pid = item["phrase_id"]
    hits = phrase_hits.get(pid, 0)
    mark_searched(pid, hits)
    searched_count += 1

print(f"  Marked {searched_count} phrases as searched")


# ═══════════════════════════════════════════════════════════════
# NEW SEARCH PHRASES to pursue in next round
# ═══════════════════════════════════════════════════════════════
print("\n--- NEW SEARCH PHRASES ---")

new_phrases = [
    ("governance simulation LARP prototype", "high", "Transformative Game Design & LARP"),
    ("Not Only Larp partners collaborators", "high", "Transformative Game Design & LARP"),
    ("planetary commons governance framework", "high", "Global Governance Innovation"),
    ("citizens assembly climate governance", "high", "Participatory Democracy Movements"),
    ("steward ownership Nordic companies", "medium", "Steward Ownership & Alternative Corporate Models"),
    ("experiential futures governance workshop", "high", "Experiential Futures & Design Fiction"),
    ("earth jurisprudence tribunal", "medium", "Rights of Nature"),
    ("regenerative finance DAO climate", "medium", "Blockchain & Regenerative Finance (ReFi)"),
    ("megagame diplomacy climate simulation", "high", "Megagames & Civilisational Simulation"),
    ("Superflux installation futures", "medium", "Experiential Futures & Design Fiction"),
]

for phrase, priority, cat in new_phrases:
    add_phrase(phrase, priority, cat)
    print(f"  [PHRASE] '{phrase}' ({priority})")


# ═══════════════════════════════════════════════════════════════
# CURATED ACTORS FROM step_c_results.json (Round 2) — 30 phrases, 291 URLs
# Applied strict inclusion/exclusion criteria.
# Target: 10-20 high-quality new actors.
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Step C Evaluation (Round 2) — 30 phrases, 291 URLs")
print("=" * 60)

# ───────────────────────────────────────────────────────────────
# GARDEN OF EDEN — Living systems, ecology, land stewardship
# ───────────────────────────────────────────────────────────────
print("\n--- GARDEN OF EDEN (Round 2) ---")

# Arbonics — Nordic forest carbon credit platform using satellite + AI for MRV
# Active: launched in Sweden 2025 with partner Treebula, data-driven forest management
arbonics = add_actor(
    "Arbonics",
    "Company",
    "GARDEN",
    description="Estonian-Nordic forest carbon credit platform using satellite imagery and AI-driven growth models for transparent monitoring, reporting and verification (MRV) of forest carbon projects. Launched in Sweden 2025 via Treebula partnership.",
    website="https://www.arbonics.com",
    domain="arbonics.com",
    location="Estonia / Sweden",
    scale="Regional",
    maturity="Active",
    relevance_score=3,
    connection="search: Erik Pihl carbon credits Arbonics Treebula",
    secondary_orientation="SPACESHIP",
    categories=["Blockchain & Regenerative Finance (ReFi)", "Open Earth Data & Satellite Intelligence"],
    notes="Nordic-based. Intersection of forest ecology and tech-driven carbon accounting.",
)
add_flag(arbonics, "nordic_based", "Estonia/Sweden — active in Nordic forest carbon market")

# Regen Civics Alliance — Global network of place-based regenerative development pilots
regen_civics = add_actor(
    "Regen Civics Alliance",
    "Network",
    "GARDEN",
    description="Global decentralised alliance of place-based pilot projects supporting regenerative community development, using web3 governance tools (via SEEDS) to coordinate local food forests, ecovillages, and cooperative land projects.",
    website="https://explore.joinseeds.earth/regenerative-civics-alliance/alliance-overview",
    domain="joinseeds.earth",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: Regen Civics Alliance place-based regenerative development",
    secondary_orientation="ASSEMBLY",
    categories=["Community Land Trusts & Commons", "Blockchain & Regenerative Finance (ReFi)"],
    notes="Bridges on-the-ground regeneration with DAO governance.",
)

# ───────────────────────────────────────────────────────────────
# SPACESHIP EARTH — Technology, infrastructure, governance tools
# ───────────────────────────────────────────────────────────────
print("\n--- SPACESHIP EARTH (Round 2) ---")

# Blockchain for Climate Foundation — Bridges blockchain tech and UNFCCC climate policy
blockchain_climate = add_actor(
    "Blockchain for Climate Foundation",
    "NGO",
    "SPACESHIP",
    description="Canadian foundation bridging blockchain technology with UNFCCC climate policy, convening governments, NGOs and Indigenous leaders to explore transparent and interoperable carbon accounting infrastructure.",
    website="https://www.blockchainforclimate.org",
    domain="blockchainforclimate.org",
    location="Canada",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: OpenClimate nested carbon accounting blockchain",
    secondary_orientation="GARDEN",
    categories=["Blockchain & Regenerative Finance (ReFi)"],
)

# Climate Action Data Trust (CAD Trust) — Open carbon credit metadata registry
cad_trust = add_actor(
    "Climate Action Data Trust",
    "Network",
    "SPACESHIP",
    description="Multi-stakeholder initiative providing open, blockchain-based metadata infrastructure to prevent double counting of carbon credits across registries, linking Verra, Gold Standard and national registries through interoperable data layers.",
    website="https://climateactiondata.org",
    domain="climateactiondata.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: OpenClimate nested carbon accounting blockchain",
    secondary_orientation="GARDEN",
    categories=["Blockchain & Regenerative Finance (ReFi)", "Open Earth Data & Satellite Intelligence"],
    notes="Co-convened by OpenEarth Foundation (already in DB). Critical infrastructure for transparent carbon markets.",
)

# ReFi DAO — Regenerative finance community and media hub
refi_dao = add_actor(
    "ReFi DAO",
    "Network",
    "SPACESHIP",
    description="Global regenerative finance community hub providing media, research, builder cohorts, and ecosystem mapping connecting ReFi projects across blockchain and ecological domains.",
    website="https://blog.refidao.com",
    domain="refidao.com",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=3,
    connection="search: ReFi regenerative finance earth observation AI convergence",
    secondary_orientation="GARDEN",
    categories=["Blockchain & Regenerative Finance (ReFi)"],
    notes="Useful network connector — maps the ReFi ecosystem including Kolektivo, Regen Network, Toucan etc.",
)

# Plurality Institute — Glen Weyl's org for plural technology research
plurality_institute = add_actor(
    "Plurality Institute",
    "Research",
    "SPACESHIP",
    description="Research institute founded by Glen Weyl advancing plural technology — collaborative tools for cooperation across difference, including quadratic voting/funding, plural money, and decentralised identity systems.",
    website="https://glenweyl.com",
    domain="glenweyl.com",
    location="USA / Global",
    scale="Global",
    maturity="Active",
    relevance_score=4,
    connection="search: Glen Weyl Radical Markets cooperative plurality mechanism design",
    secondary_orientation="ASSEMBLY",
    categories=["Decentralised Governance Tech", "Participatory Democracy Movements"],
    notes="Weyl's plural technology agenda directly intersects with Garden's governance simulation design.",
)
add_flag(plurality_institute, "close_vision", "Plural technology (quadratic voting, plural money) directly applicable to Garden governance mechanics")

# Sociocracy For All — Open-source governance methodology training
sociocracy_for_all = add_actor(
    "Sociocracy For All",
    "NGO",
    "SPACESHIP",
    description="Global nonprofit providing open-source training, resources, and community for sociocratic (consent-based) governance, supporting cooperatives, communities, and organisations in implementing distributed decision-making.",
    website="https://www.sociocracyforall.org",
    domain="sociocracyforall.org",
    location="USA / Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: Hypha DAO sociocracy",
    secondary_orientation="ASSEMBLY",
    categories=["Decentralised Governance Tech", "Participatory Democracy Movements"],
    notes="Provides the governance methodology underlying many DAOs. Practical governance training relevant to Garden assembly design.",
)

# ───────────────────────────────────────────────────────────────
# ELEUSINIAN MYSTERIES — Games, ritual, experience, transformation
# ───────────────────────────────────────────────────────────────
print("\n--- ELEUSINIAN MYSTERIES (Round 2) ---")

# Climate Interactive — Runs the World Climate Simulation game used globally
climate_interactive = add_actor(
    "Climate Interactive",
    "NGO",
    "TEMPLE",
    description="MIT-affiliated nonprofit running the World Climate Simulation — a role-playing negotiation game putting participants in a fictitious UN climate summit, backed by the En-ROADS systems dynamics model providing real-time feedback on policy choices. Used in 100+ countries.",
    website="https://www.climateinteractive.org",
    domain="climateinteractive.org",
    location="USA",
    scale="Global",
    maturity="Established",
    relevance_score=5,
    connection="search: megagame diplomacy climate simulation",
    secondary_orientation="ASSEMBLY",
    categories=["Megagames & Civilisational Simulation", "Education for Planetary Citizenship"],
    notes="World Climate Simulation is exactly the kind of governance game Garden aims to create.",
)
add_flag(climate_interactive, "close_vision", "World Climate Simulation is a direct precursor to Garden's governance LARP approach")
add_flag(climate_interactive, "event_opportunity", "World Climate Simulation format could be adapted for Garden assemblies")

# PAXsims — Hub for peace, conflict, humanitarian simulations and serious games
paxsims = add_actor(
    "PAXsims",
    "Network",
    "TEMPLE",
    description="Community hub and publication devoted to peace, conflict, humanitarian, and development simulations and serious games for education, training, and policy analysis.",
    website="https://paxsims.wordpress.com",
    domain="paxsims.wordpress.com",
    location="Global",
    scale="Global",
    maturity="Established",
    relevance_score=3,
    connection="search: megagame diplomacy climate simulation",
    secondary_orientation="ASSEMBLY",
    categories=["Megagames & Civilisational Simulation"],
)

# Linköping University Climate Change Megagame — Swedish academic climate megagame
liu_climate_megagame = add_actor(
    "Linköping University Climate Change Megagame",
    "Research",
    "TEMPLE",
    description="Swedish academic megagame project at Linköping University simulating regional climate transformation 2020-2100, using SMHI forecast data to create participatory governance simulations.",
    website="https://liu.se/en/research/climate-change-megagame",
    domain="liu.se",
    location="Sweden",
    scale="Local",
    maturity="Active",
    relevance_score=4,
    connection="search: megagame diplomacy climate simulation",
    secondary_orientation="ASSEMBLY",
    categories=["Megagames & Civilisational Simulation", "Education for Planetary Citizenship"],
    notes="Swedish-based climate megagame with real SMHI data. Directly relevant to Garden's Nordic context.",
)
add_flag(liu_climate_megagame, "nordic_based", "Linköping University, Sweden")
add_flag(liu_climate_megagame, "close_vision", "Swedish climate megagame using real forecast data — very close to Garden's approach")

# Governance Futures — Experiential governance design workshops
governance_futures = add_actor(
    "Governance Futures",
    "NGO",
    "TEMPLE",
    description="Organisation creating experiential and world-building workshops that engage communities in radical imagination about governance futures, using art, illustration, and comic books to envision equitable decision-making.",
    website="https://governancefutures.org",
    domain="governancefutures.org",
    location="USA",
    scale="National",
    maturity="Active",
    relevance_score=4,
    connection="search: experiential futures governance workshop",
    secondary_orientation="ASSEMBLY",
    categories=["Experiential Futures & Design Fiction", "Participatory Democracy Movements"],
)
add_flag(governance_futures, "close_vision", "Experiential governance world-building directly aligns with Garden's LARP approach")

# ───────────────────────────────────────────────────────────────
# GENERAL ASSEMBLY OF EARTH — Global governance, democracy, justice
# ───────────────────────────────────────────────────────────────
print("\n--- GENERAL ASSEMBLY OF EARTH (Round 2) ---")

# Global Assembly — World's first global citizens' assembly (COP26)
global_assembly = add_actor(
    "Global Assembly",
    "Movement",
    "ASSEMBLY",
    description="The world's first global citizens' assembly, bringing together randomly selected people from across the world to deliberate on the climate and ecological crisis. Presented the People's Declaration at COP26 in 2021.",
    website="https://globalassembly.org",
    domain="globalassembly.org",
    location="Global",
    scale="Global",
    maturity="Active",
    relevance_score=5,
    connection="search: citizens assembly climate governance",
    secondary_orientation="TEMPLE",
    categories=["Participatory Democracy Movements", "Global Governance Innovation"],
    notes="A direct prototype of what Garden envisions — global citizens' assembly on planetary challenges.",
)
add_flag(global_assembly, "close_vision", "World's first global citizens' assembly — direct precedent for Garden's assembly vision")

# KNOCA — Knowledge Network on Climate Assemblies
knoca = add_actor(
    "KNOCA",
    "Network",
    "ASSEMBLY",
    description="EU-funded Knowledge Network on Climate Assemblies, connecting organisers, researchers, and policymakers working on climate citizens' assemblies across Europe.",
    website="https://www.knoca.eu",
    domain="knoca.eu",
    location="Europe",
    scale="Regional",
    maturity="Active",
    relevance_score=4,
    connection="search: citizens assembly climate governance",
    categories=["Participatory Democracy Movements"],
    notes="Key network for climate assembly methodology. Directly useful for Garden's assembly design.",
)

# ═══════════════════════════════════════════════════════════════
# Mark all 30 phrases from Round 2 as searched
# ═══════════════════════════════════════════════════════════════
print("\n--- MARKING PHRASES AS SEARCHED (Round 2) ---")

phrase_hits_r2 = {
    145: 0, 146: 2, 150: 0, 155: 0, 157: 0, 163: 1, 167: 0,
    168: 0, 170: 0, 172: 0, 173: 0, 175: 0, 176: 0, 177: 0,
    178: 0, 179: 0, 180: 1, 181: 1, 183: 1, 186: 0, 187: 0,
    192: 1, 194: 0, 195: 0, 197: 0, 198: 0, 199: 0, 200: 2,
    202: 1, 205: 3,
}

for pid, hits in phrase_hits_r2.items():
    mark_searched(pid, hits)

print(f"  Marked {len(phrase_hits_r2)} phrases as searched (Round 2)")

# ═══════════════════════════════════════════════════════════════
# Commit and summarise
# ═══════════════════════════════════════════════════════════════

conn.commit()

print("\n" + "=" * 60)
print("Step C Evaluation Complete — Summary")
print("=" * 60)

for table in ['actors', 'sources', 'people', 'search_phrases', 'source_actor', 'flags']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]} rows")
    except sqlite3.OperationalError:
        pass

cur.execute("SELECT COUNT(*) FROM search_phrases WHERE last_searched IS NOT NULL")
print(f"  phrases searched: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM search_phrases WHERE last_searched IS NULL")
print(f"  phrases remaining: {cur.fetchone()[0]}")

# Show new actors added
print(f"\n--- New Actors Added ---")
cur.execute("""
    SELECT a.name, a.type, o.code, a.relevance_score, a.location
    FROM actors a
    JOIN orientations o ON a.primary_orientation_id = o.id
    ORDER BY a.id DESC
    LIMIT 40
""")
rows = cur.fetchall()
# Only show ones from this session (not seeds)
cur.execute("SELECT COUNT(*) FROM actors")
total = cur.fetchone()[0]
new_count = total - 34  # 32 seeds + Viable Cities + Curve Labs
print(f"  Total actors: {total} ({new_count} new from this evaluation)")
for name, type_, orientation, score, location in rows[:new_count]:
    print(f"  [{score}] {name} ({type_}, {orientation}) — {location}")

# Show flags
print(f"\n--- Flags ---")
cur.execute("""
    SELECT f.flag_type, a.name, f.notes
    FROM flags f
    JOIN actors a ON f.actor_id = a.id
    ORDER BY f.flag_type, a.name
""")
for flag_type, name, notes in cur.fetchall():
    print(f"  [{flag_type}] {name}: {notes}")

conn.close()
