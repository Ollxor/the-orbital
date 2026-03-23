#!/usr/bin/env python3
"""
Migrate tags — create tags tables and auto-extract tags from existing entities.

Usage:
    python3 migrate_tags.py [--dry-run]

Extracts tags from:
- Actor descriptions, types, orientations, categories, flags, and locations
- Project descriptions, stages, and geography
- People skills and orientations
- News markdown frontmatter (for cross-referencing)
"""
import json
import os
import re
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")

# Domain-relevant tags to extract from text
DOMAIN_TAGS = {
    # Governance approaches
    'governance', 'participatory', 'deliberative', 'democracy', 'democratic-innovation',
    'decentralized', 'decentralised', 'cooperative', 'commons', 'dao',
    'citizens-assembly', 'sortition', 'liquid-democracy',
    # Ecological
    'regenerative', 'biodiversity', 'rewilding', 'permaculture', 'agroforestry',
    'rights-of-nature', 'indigenous', 'stewardship', 'ecosystem',
    'climate', 'sustainability', 'conservation', 'restoration',
    # Technology
    'open-source', 'digital-twin', 'platform', 'blockchain', 'ai',
    'data', 'interoperability', 'governance-tech',
    # Transformative
    'ritual', 'ceremony', 'immersive', 'larp', 'festival', 'contemplative',
    'consciousness', 'inner-development', 'art', 'performance',
    # Structural
    'research', 'funding', 'education', 'policy', 'advocacy',
    'network', 'movement', 'coalition', 'publication',
    # Geographic
    'nordic', 'europe', 'global-south', 'africa', 'asia', 'americas', 'oceania',
    'sweden', 'denmark', 'finland', 'norway', 'iceland',
}

# Map orientation codes to tags
ORIENTATION_TAGS = {
    'GARDEN': ['ecological-governance', 'nature-based'],
    'SPACESHIP': ['systems-thinking', 'technology'],
    'TEMPLE': ['transformative-practice', 'experiential'],
    'ASSEMBLY': ['democratic-innovation', 'institutional-design'],
}

# Map actor types to tags
TYPE_TAGS = {
    'NGO': ['civil-society'],
    'Company': ['enterprise'],
    'Research': ['research'],
    'Government': ['public-sector'],
    'Network': ['network'],
    'Movement': ['movement'],
}

# Map flag types to tags
FLAG_TAGS = {
    'network_connected': ['network-connected'],
    'close_vision': ['aligned-vision'],
    'event_opportunity': ['events'],
    'funding_source': ['funding'],
    'nordic_based': ['nordic'],
}

# Map project stages to tags
STAGE_TAGS = {
    'research': ['research'],
    'pilot': ['pilot'],
    'deployed': ['deployed'],
    'scaled': ['scaled'],
}


def normalize_tag(text):
    """Normalize a string into a valid tag: lowercase, hyphenated, no special chars."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def extract_tags_from_text(text):
    """Extract domain-relevant tags from free text."""
    if not text:
        return set()
    text_lower = text.lower()
    found = set()
    for tag in DOMAIN_TAGS:
        # Check for the tag as a word (with hyphens converted to spaces for matching)
        search_term = tag.replace('-', ' ')
        if search_term in text_lower or tag in text_lower:
            found.add(tag)
    return found


def extract_location_tags(location):
    """Extract geographic tags from location string."""
    if not location:
        return set()
    loc_lower = location.lower()
    tags = set()

    nordic_countries = {'sweden', 'denmark', 'norway', 'finland', 'iceland'}
    for country in nordic_countries:
        if country in loc_lower:
            tags.add(country)
            tags.add('nordic')

    if any(w in loc_lower for w in ['europe', 'european', 'eu', 'uk', 'germany', 'france',
                                     'netherlands', 'spain', 'italy', 'switzerland']):
        tags.add('europe')

    if any(w in loc_lower for w in ['global', 'international', 'worldwide']):
        tags.add('global')

    return tags


def ensure_tag(cur, tag_name):
    """Insert tag if not exists, return tag_id."""
    cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    return cur.fetchone()[0]


def link_tag(cur, tag_id, entity_type, entity_id):
    """Link a tag to an entity."""
    cur.execute("INSERT OR IGNORE INTO entity_tag (tag_id, entity_type, entity_id) VALUES (?, ?, ?)",
                (tag_id, entity_type, entity_id))


def main():
    dry_run = '--dry-run' in sys.argv

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Create tables
    print("Creating tags tables...")
    cur.execute("""CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT (datetime('now'))
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS entity_tag (
        tag_id INTEGER NOT NULL REFERENCES tags(id),
        entity_type TEXT NOT NULL CHECK (entity_type IN ('actor', 'project', 'person')),
        entity_id INTEGER NOT NULL,
        PRIMARY KEY (tag_id, entity_type, entity_id)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entity_tag_entity ON entity_tag(entity_type, entity_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entity_tag_tag ON entity_tag(tag_id)")
    conn.commit()

    stats = {'actors': 0, 'projects': 0, 'people': 0, 'tags_created': 0, 'links_created': 0}

    # ─── Tag actors ───
    print("\nExtracting tags for actors...")
    cur.execute("""
        SELECT a.id, a.name, a.type, a.description, a.location, a.scale,
               o.code as orientation_code
        FROM actors a
        LEFT JOIN orientations o ON o.id = a.primary_orientation_id
        WHERE a.canonical_id IS NULL
    """)
    actors = [dict(row) for row in cur.fetchall()]

    for actor in actors:
        tags = set()

        # From orientation
        if actor['orientation_code'] and actor['orientation_code'] in ORIENTATION_TAGS:
            tags.update(ORIENTATION_TAGS[actor['orientation_code']])

        # From type
        if actor['type'] in TYPE_TAGS:
            tags.update(TYPE_TAGS[actor['type']])

        # From description
        tags.update(extract_tags_from_text(actor['description']))
        tags.update(extract_tags_from_text(actor['name']))

        # From location
        tags.update(extract_location_tags(actor['location']))

        # From scale
        if actor['scale'] == 'Global':
            tags.add('global')

        # From flags
        cur.execute("SELECT flag_type FROM flags WHERE actor_id = ?", (actor['id'],))
        for row in cur.fetchall():
            if row['flag_type'] in FLAG_TAGS:
                tags.update(FLAG_TAGS[row['flag_type']])

        # From categories
        cur.execute("""
            SELECT c.name FROM categories c
            JOIN actor_category ac ON ac.category_id = c.id
            WHERE ac.actor_id = ?
        """, (actor['id'],))
        for row in cur.fetchall():
            cat_tag = normalize_tag(row['name'])
            if cat_tag and len(cat_tag) > 2:
                tags.add(cat_tag)

        if tags:
            stats['actors'] += 1
            if not dry_run:
                for tag_name in tags:
                    tag_id = ensure_tag(cur, tag_name)
                    link_tag(cur, tag_id, 'actor', actor['id'])
                    stats['links_created'] += 1
            else:
                print(f"  {actor['name']}: {', '.join(sorted(tags))}")

    # ─── Tag projects ───
    print("\nExtracting tags for projects...")
    cur.execute("SELECT id, name, description, geography, stage FROM projects")
    projects = [dict(row) for row in cur.fetchall()]

    for project in projects:
        tags = set()

        # From description
        tags.update(extract_tags_from_text(project['description']))
        tags.update(extract_tags_from_text(project['name']))

        # From geography
        tags.update(extract_location_tags(project['geography']))

        # From stage
        if project['stage'] and project['stage'] in STAGE_TAGS:
            tags.update(STAGE_TAGS[project['stage']])

        if tags:
            stats['projects'] += 1
            if not dry_run:
                for tag_name in tags:
                    tag_id = ensure_tag(cur, tag_name)
                    link_tag(cur, tag_id, 'project', project['id'])
                    stats['links_created'] += 1
            else:
                print(f"  {project['name']}: {', '.join(sorted(tags))}")

    # ─── Tag people ───
    print("\nExtracting tags for people...")
    cur.execute("""
        SELECT p.id, p.first_name, p.last_name, p.skills, p.location,
               o.code as orientation_code
        FROM people p
        LEFT JOIN orientations o ON o.id = p.primary_orientation_id
    """)
    people = [dict(row) for row in cur.fetchall()]

    for person in people:
        tags = set()

        # From orientation
        if person['orientation_code'] and person['orientation_code'] in ORIENTATION_TAGS:
            tags.update(ORIENTATION_TAGS[person['orientation_code']])

        # From skills
        tags.update(extract_tags_from_text(person['skills']))

        # From location
        tags.update(extract_location_tags(person['location']))

        if tags:
            stats['people'] += 1
            if not dry_run:
                for tag_name in tags:
                    tag_id = ensure_tag(cur, tag_name)
                    link_tag(cur, tag_id, 'person', person['id'])
                    stats['links_created'] += 1
            else:
                name = f"{person['first_name'] or ''} {person['last_name'] or ''}".strip()
                print(f"  {name}: {', '.join(sorted(tags))}")

    if not dry_run:
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM tags")
        stats['tags_created'] = cur.fetchone()[0]

    conn.close()

    print(f"\n{'=== DRY RUN ===' if dry_run else '=== Migration Complete ==='}")
    print(f"  Actors tagged: {stats['actors']}")
    print(f"  Projects tagged: {stats['projects']}")
    print(f"  People tagged: {stats['people']}")
    if not dry_run:
        print(f"  Tags created: {stats['tags_created']}")
        print(f"  Tag links created: {stats['links_created']}")


if __name__ == "__main__":
    main()
