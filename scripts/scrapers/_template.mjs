/**
 * _template.mjs — copy this file and fill in the blanks to add a new source.
 *
 * Naming convention: use the site's primary domain name (e.g. involve.mjs,
 * earthcharter.mjs). Export a single `scrape()` async function.
 *
 * The function must return an array of partial event objects. Fields you
 * can't determine automatically should be omitted (they'll be left blank
 * for editorial review). The runner will merge your output with blankEvent()
 * and call inferOrientations / inferGeo on anything you don't supply.
 */

import { blankEvent, slugify, toIsoDate, fetchJson, fetchText } from './_base.mjs';

// Human-readable label shown in scraper run output
export const SOURCE_LABEL = 'Template Source';
// Canonical URL of the events listing page (for reference only — not fetched here)
export const SOURCE_URL   = 'https://example.com/events/';

export async function scrape() {
  // ── 1. Fetch raw data ──────────────────────────────────────────────────────
  // const raw = await fetchJson('https://api.example.com/events?format=json');
  // const html = await fetchText('https://example.com/events/');
  const raw = [];  // replace with real fetch

  // ── 2. Map to partial event objects ───────────────────────────────────────
  return raw.map(item => ({
    ...blankEvent(),
    slug:        slugify(item.title, item.start_date),
    name:        item.title,
    description: item.summary ?? '',
    date_start:  toIsoDate(item.start_date),
    date_end:    toIsoDate(item.end_date),
    location:    item.location ?? '',
    website:     item.url ?? '',
    image:       item.image ?? '',
    // Leave orientations, tags, actors, geo empty — filled during review
    // Set _source so the runner can label the review file
    _source:     SOURCE_LABEL,
  }));
}
