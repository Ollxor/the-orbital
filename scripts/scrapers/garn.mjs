/**
 * garn.mjs — GARN (Global Alliance for the Rights of Nature)
 *
 * Source: https://www.garn.org/events/
 * Method: WordPress REST API (wp-event-manager plugin)
 *         GET https://www.garn.org/wp-json/wp/v2/event_listing
 *
 * GARN events are predominantly rights-of-nature focused:
 * orientations GARDEN + ASSEMBLY are a safe default but the runner
 * will override with keyword inference if description is rich enough.
 */

import {
  blankEvent, slugify, toIsoDate, stripHtml,
  inferOrientations, inferGeo, inferFormat, inferType,
  fetchJson,
} from './_base.mjs';

export const SOURCE_LABEL = 'GARN (Rights of Nature)';
export const SOURCE_URL   = 'https://www.garn.org/events/';

const API = 'https://www.garn.org/wp-json/wp/v2/event_listing';
const PER_PAGE = 100;

async function fetchPage(page) {
  const url = `${API}?per_page=${PER_PAGE}&page=${page}&orderby=date&order=asc&status=publish`;
  return fetchJson(url);
}

export async function scrape() {
  const results = [];
  let page = 1;

  while (true) {
    let items;
    try {
      items = await fetchPage(page);
    } catch (err) {
      if (page === 1) throw err;          // first page failing is a real error
      break;                              // later pages failing = end of results
    }
    if (!Array.isArray(items) || items.length === 0) break;

    for (const item of items) {
      // Title
      const name = stripHtml(item.title?.rendered ?? '');
      if (!name) continue;

      // Dates — WP Event Manager stores them in meta
      const meta   = item.meta ?? {};
      const rawStart = meta._event_start_date ?? meta.event_start_date ?? '';
      const rawEnd   = meta._event_end_date   ?? meta.event_end_date   ?? '';
      const date_start = toIsoDate(rawStart) || toIsoDate(item.date ?? '');
      const date_end   = toIsoDate(rawEnd);

      // Description — prefer excerpt, fallback to truncated content
      const descHtml   = item.excerpt?.rendered ?? item.content?.rendered ?? '';
      const description = stripHtml(descHtml).slice(0, 400).trim();

      // Location
      const location = meta._event_location ?? meta.event_location ?? '';

      // Website — registration URL or permalink
      const website = meta._event_registration ?? meta.event_registration ?? item.link ?? '';

      // Image
      const image = item.featured_media_url ?? item._embedded?.['wp:featuredmedia']?.[0]?.source_url ?? '';

      // Inferred fields
      const orientations = inferOrientations(name, description);
      const { continent, subregion } = inferGeo(location, description);
      const format = inferFormat(location, description);
      const type   = inferType(name, description);

      results.push({
        ...blankEvent(),
        slug:        slugify(name, date_start),
        name,
        description,
        date_start,
        date_end,
        location,
        website,
        image,
        type,
        format,
        orientations: orientations.length ? orientations : ['GARDEN', 'ASSEMBLY'],
        continent,
        subregion,
        _source: SOURCE_LABEL,
      });
    }

    if (items.length < PER_PAGE) break;
    page++;
  }

  return results;
}
