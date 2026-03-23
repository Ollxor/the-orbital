#!/usr/bin/env python3
"""
Extract entities from a single chunk — designed to be called by AI agent per chunk.

Usage:
    python3 extract_chunk.py <chunk_json> [--out <output_json>] [--campaign <name>]

Reads a chunk JSON, outputs an extraction template that the AI agent fills in.
If --out is provided, writes a blank template there. Otherwise prints to stdout.

The AI agent should:
1. Read the chunk text
2. Fill in the extraction JSON
3. Save to the output path
"""
import argparse
import json
import os
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")

EXTRACTION_TEMPLATE = {
    "chunk_file": "",
    "actors": [
        # {
        #     "name": "Organisation / Company / Network Name",
        #     "type": "NGO|Company|Research|Government|Network|Movement|Person",
        #     "primary_orientation": "GARDEN|SPACESHIP|TEMPLE|ASSEMBLY",
        #     "secondary_orientation": null,
        #     "categories": ["category name from the 30 categories"],
        #     "tags": ["lowercase-hyphenated-keywords", "e.g. governance, funding, nordic, open-source"],
        #     "description": "1-2 sentences on what they do",
        #     "location": "Country or region",
        #     "url": "https://...",
        #     "scale": "Local|National|Regional|Global",
        #     "maturity": "Idea|Early|Active|Established",
        #     "relevance_score": 3,  # 1-5: how directly relevant to The Garden's vision
        #     "connection": "how we found them (which seed actor, search term)",
        #     "contact_pathway": "do we know someone who knows them?",
        #     "notes": "",
        #     "intel": [
        #         {"field": "field_name", "value": "field_value"}
        #     ]
        # }
    ],
    "projects": [
        # {
        #     "name": "Project / Initiative Name",
        #     "website": "https://...",
        #     "description": "",
        #     "geography": "",
        #     "stage": "research|pilot|deployed|scaled",
        #     "tags": ["lowercase-hyphenated-keywords"],
        #     "actors_involved": [{"name": "...", "relationship": "organiser|partner|funder|participant"}],
        #     "intel": [
        #         {"field": "field_name", "value": "field_value"}
        #     ]
        # }
    ],
    "people": [
        # {
        #     "first_name": "",
        #     "last_name": "",
        #     "primary_orientation": "GARDEN|SPACESHIP|TEMPLE|ASSEMBLY",
        #     "skills": "what they bring",
        #     "tags": ["lowercase-hyphenated-keywords"],
        #     "actor_names": ["Actor they work with"],
        #     "role": "founder|advisor|researcher|member|...",
        #     "job_title": "",
        #     "linkedin_url": "",
        #     "email": "",
        #     "relationship_tier": "To explore",
        #     "notes": ""
        # }
    ],
    # Use this array to capture new intel about actors that already exist in the database. Match by name.
    "existing_actor_intel": [
        # {
        #     "actor_name": "Name of actor already in database",
        #     "intel": [
        #         {"field": "field_name", "value": "field_value"}
        #     ]
        # }
    ],
    "events": [
        # {
        #     "name": "Event Name",
        #     "type": "Conference|Summit|Workshop|Festival|Assembly|Symposium|LARP|Convention|Forum|Prize|Campaign|Other",
        #     "series": "Recurring series name (e.g. 'UNFCCC COP') or null",
        #     "edition": "Specific edition (e.g. 'COP30', '2025') or null",
        #     "location": "City, Country",
        #     "date_start": "ISO date or partial (e.g. '2025-06', '2025')",
        #     "date_end": "ISO date or null",
        #     "recurrence": "one-off|annual|biennial|irregular|ongoing",
        #     "website": "https://...",
        #     "description": "1-2 sentences",
        #     "relevance_note": "Why this event matters for The Garden",
        #     "actors": [{"name": "Actor Name", "role": "organizer|speaker|attendee|sponsor|exhibitor|partner"}]
        # }
    ],
    "search_phrases": [
        # {"phrase": "search query", "priority": "high|medium|low"}
    ],
    "source_urls": [
        # {"url": "https://...", "title": "", "description": "", "monitor": false}
    ]
}


def load_campaign_hints(campaign_name: str) -> list[str] | None:
    """Load intel_fields from a campaign to use as extraction hints."""
    if not os.path.exists(DB):
        return None
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT intel_fields FROM campaigns WHERE name = ?", (campaign_name,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate extraction template for a chunk")
    parser.add_argument("chunk_json", help="Path to chunk JSON file")
    parser.add_argument("--out", default=None, help="Output path for extraction template")
    parser.add_argument("--campaign", default="garden-landscape", help="Campaign name (default: garden-landscape)")
    args = parser.parse_args()

    with open(args.chunk_json) as f:
        chunk = json.load(f)

    template = dict(EXTRACTION_TEMPLATE)
    template["chunk_file"] = os.path.basename(args.chunk_json)

    # Add campaign hint fields to template comments
    campaign_hints = None
    if args.campaign:
        campaign_hints = load_campaign_hints(args.campaign)
        if campaign_hints:
            template["_campaign"] = args.campaign
            template["_intel_field_hints"] = campaign_hints

    # Add orientation classification guide
    template["_classification_guide"] = {
        "GARDEN": "Land, ecosystems, food, water, biodiversity, indigenous knowledge",
        "SPACESHIP": "Technology, platforms, data systems, governance tools, economic infrastructure, alternative ownership",
        "TEMPLE": "Experiences, games, rituals, art, performance, festivals, transformation, consciousness, meaning-making",
        "ASSEMBLY": "Global governance structures, democracy innovation, rights frameworks, climate justice, planetary-scale design",
    }

    if args.out:
        with open(args.out, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"Template written to {args.out}")
        print(f"Chunk: {chunk['word_count']} words from {chunk['source_file']} (chunk {chunk['chunk_index']+1}/{chunk['total_chunks']})")
        if campaign_hints:
            print(f"Campaign: {args.campaign} — intel fields: {campaign_hints}")
    else:
        print(json.dumps(template, indent=2))


if __name__ == "__main__":
    main()
