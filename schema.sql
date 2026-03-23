-- Garden Crawler — Landscape Research Database Schema
-- Adapted from Voysys lead gen pipeline for The Garden project

-- ═══════════════════════════════════════════════════════════════
-- Core taxonomy: Orientations → Categories (hierarchical)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS orientations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,          -- GARDEN, SPACESHIP, TEMPLE, ASSEMBLY
    name TEXT NOT NULL,                 -- Full name: "Garden of Eden", etc.
    description TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orientation_id INTEGER NOT NULL REFERENCES orientations(id),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    search_terms JSON,                  -- JSON array of 4-6 search phrases
    actor_types JSON,                   -- JSON array of expected types, e.g. ["NGO", "Company", "Research"]
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_categories_orientation ON categories(orientation_id);

-- ═══════════════════════════════════════════════════════════════
-- Actors — organisations, companies, networks, movements, people
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('NGO', 'Company', 'Research', 'Government', 'Network', 'Movement', 'Person')),
    primary_orientation_id INTEGER REFERENCES orientations(id),
    secondary_orientation_id INTEGER REFERENCES orientations(id),
    description TEXT,                   -- 1-2 sentences on what they do
    website TEXT,
    domain TEXT,                        -- normalized domain for dedup
    location TEXT,                      -- country or region
    scale TEXT CHECK (scale IN ('Local', 'National', 'Regional', 'Global')),
    maturity TEXT CHECK (maturity IN ('Idea', 'Early', 'Active', 'Established')),
    relevance_score INTEGER DEFAULT 0 CHECK (relevance_score BETWEEN 1 AND 5),
    connection TEXT,                    -- how we found them (seed actor, search term, etc.)
    contact_pathway TEXT,               -- do we know someone who knows them?
    canonical_id INTEGER REFERENCES actors(id),  -- self-ref for dedup/merge
    notes TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_actors_type ON actors(type);
CREATE INDEX IF NOT EXISTS idx_actors_primary_orientation ON actors(primary_orientation_id);
CREATE INDEX IF NOT EXISTS idx_actors_relevance ON actors(relevance_score);
CREATE INDEX IF NOT EXISTS idx_actors_canonical ON actors(canonical_id);
CREATE INDEX IF NOT EXISTS idx_actors_domain ON actors(domain);

-- Junction: actors ↔ categories (many-to-many)
CREATE TABLE IF NOT EXISTS actor_category (
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    PRIMARY KEY (actor_id, category_id)
);

-- ═══════════════════════════════════════════════════════════════
-- People Map — individuals connected to actors
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    job_title TEXT,
    linkedin_url TEXT,
    primary_orientation_id INTEGER REFERENCES orientations(id),
    skills TEXT,                         -- what they bring
    relationship_tier TEXT CHECK (relationship_tier IN (
        'Core team candidate', 'Strategic advisor', 'Advisor / participant',
        'Participant / contributor', 'Research collaborator', 'To explore'
    )),
    status TEXT DEFAULT 'To contact',    -- freeform: "Active", "Not yet contacted", etc.
    location TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

-- Junction: people ↔ actors (many-to-many, with role)
CREATE TABLE IF NOT EXISTS person_actor (
    person_id INTEGER NOT NULL REFERENCES people(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    role TEXT,                           -- "founder", "advisor", "researcher", "member", etc.
    PRIMARY KEY (person_id, actor_id)
);

-- ═══════════════════════════════════════════════════════════════
-- Projects — specific initiatives that actors undertake
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    website TEXT,
    description TEXT,
    geography TEXT,
    stage TEXT,                          -- research, pilot, deployed, scaled
    notes TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════
-- Intel — key-value facts with provenance
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS intel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('actor', 'project')),
    entity_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    confidence TEXT DEFAULT 'extracted' CHECK (confidence IN ('extracted', 'verified', 'stale')),
    campaign_id INTEGER REFERENCES campaigns(id),
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    UNIQUE (entity_type, entity_id, field, source_id)
);

CREATE INDEX IF NOT EXISTS idx_intel_entity ON intel(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_intel_campaign ON intel(campaign_id);

-- ═══════════════════════════════════════════════════════════════
-- Sources — URL-based sources of information
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    last_fetch DATETIME,
    monitor BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sources_last_fetch ON sources(last_fetch);
CREATE INDEX IF NOT EXISTS idx_sources_monitor ON sources(monitor);

-- ═══════════════════════════════════════════════════════════════
-- Search phrases — queries for discovering new actors/sources
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS search_phrases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT UNIQUE NOT NULL,
    category_id INTEGER REFERENCES categories(id),  -- which category spawned this phrase
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    hit_count INTEGER DEFAULT 0,
    last_searched DATETIME,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_search_phrases_last_searched ON search_phrases(last_searched);
CREATE INDEX IF NOT EXISTS idx_search_phrases_priority ON search_phrases(priority);
CREATE INDEX IF NOT EXISTS idx_search_phrases_category ON search_phrases(category_id);

-- ═══════════════════════════════════════════════════════════════
-- Campaigns — research focus areas (kept for brief system compatibility)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    intel_fields JSON,
    scoring_prompt TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════
-- Briefs — generated research prompts
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    focus TEXT NOT NULL,                 -- gaps/deepen/expand
    campaign_id INTEGER REFERENCES campaigns(id),
    actor_targets TEXT,                  -- JSON array of actor names targeted
    prompt_text TEXT,
    result_file TEXT,
    model TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════
-- Junction tables — provenance links
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS source_actor (
    source_id INTEGER NOT NULL REFERENCES sources(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    PRIMARY KEY (source_id, actor_id)
);

CREATE TABLE IF NOT EXISTS source_project (
    source_id INTEGER NOT NULL REFERENCES sources(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    PRIMARY KEY (source_id, project_id)
);

CREATE TABLE IF NOT EXISTS source_person (
    source_id INTEGER NOT NULL REFERENCES sources(id),
    person_id INTEGER NOT NULL REFERENCES people(id),
    PRIMARY KEY (source_id, person_id)
);

CREATE TABLE IF NOT EXISTS project_actor (
    project_id INTEGER NOT NULL REFERENCES projects(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    relationship TEXT,                   -- operator, developer, partner, funder, participant
    PRIMARY KEY (project_id, actor_id)
);

-- ═══════════════════════════════════════════════════════════════
-- High-value flags — actors of special interest
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    flag_type TEXT NOT NULL CHECK (flag_type IN (
        'network_connected',            -- already connected to someone in our network
        'close_vision',                  -- doing something very close to The Garden's vision
        'event_opportunity',             -- running events where Garden could be presented
        'funding_source',               -- offers funding or grants relevant to our work
        'nordic_based'                   -- based in Sweden or the Nordics
    )),
    notes TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_flags_actor ON flags(actor_id);
CREATE INDEX IF NOT EXISTS idx_flags_type ON flags(flag_type);

-- ═══════════════════════════════════════════════════════════════
-- Events — conferences, festivals, assemblies, workshops
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN (
        'Conference', 'Festival', 'Workshop', 'Assembly',
        'Summit', 'Symposium', 'Webinar', 'LARP', 'Convention',
        'Forum', 'Prize', 'Campaign', 'Other'
    )),
    series TEXT,                              -- recurring event series name (e.g. "COP", "IUCN World Conservation Congress")
    edition TEXT,                             -- specific edition (e.g. "COP26", "2021")
    location TEXT,                            -- city, country
    date_start TEXT,                          -- ISO date or partial (e.g. "2025-06", "2025")
    date_end TEXT,
    recurrence TEXT CHECK (recurrence IN ('one-off', 'annual', 'biennial', 'irregular', 'ongoing')),
    website TEXT,
    description TEXT,
    relevance_note TEXT,                      -- why this event matters for The Garden
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_start);
CREATE INDEX IF NOT EXISTS idx_events_series ON events(series);

-- Junction: events ↔ actors (many-to-many, with role)
CREATE TABLE IF NOT EXISTS event_actor (
    event_id INTEGER NOT NULL REFERENCES events(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    role TEXT CHECK (role IN ('organizer', 'speaker', 'attendee', 'sponsor', 'exhibitor', 'partner')),
    notes TEXT,
    PRIMARY KEY (event_id, actor_id)
);

CREATE INDEX IF NOT EXISTS idx_event_actor_actor ON event_actor(actor_id);

-- ═══════════════════════════════════════════════════════════════
-- Tags — flexible keyword tagging for all entity types
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- lowercase, hyphenated (e.g. "rights-of-nature")
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS entity_tag (
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('actor', 'project', 'person', 'event')),
    entity_id INTEGER NOT NULL,
    PRIMARY KEY (tag_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_tag_entity ON entity_tag(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_tag_tag ON entity_tag(tag_id);
