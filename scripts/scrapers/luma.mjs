/**
 * luma.mjs — generic Lu.ma calendar scraper
 *
 * Lu.ma hosts events for many orgs in the planetary governance space.
 * This module exports a factory: `lumaCalendar(calendarApiId, label, defaultOrientations)`
 *
 * API endpoint (embed API, no auth required):
 *   https://api.lu.ma/calendar/get-items?calendarApiId=CAL_ID&period=future&pagination_limit=100
 *
 * Known calendars are configured at the bottom of this file and re-exported
 * as named scrapers so the runner can import them like any other scraper.
 *
 * To add a new Lu.ma calendar:
 *   1. Open the org's Lu.ma calendar page in a browser
 *   2. Right-click → Inspect → Network tab → look for a request to
 *      api.lu.ma/calendar/get-items — copy the calendarApiId
 *   3. Add an entry at the bottom of this file
 */

import {
  blankEvent, slugify, toIsoDate, stripHtml,
  inferOrientations, inferGeo, inferFormat, inferType,
  fetchJson,
} from './_base.mjs';

const LUMA_API = 'https://api.lu.ma/calendar/get-items';

function lumaCalendar(calendarApiId, sourceLabel, defaultOrientations = []) {
  return {
    SOURCE_LABEL: sourceLabel,
    SOURCE_URL:   `https://lu.ma/calendar/${calendarApiId}`,

    async scrape() {
      const results = [];
      let cursor = null;

      while (true) {
        const params = new URLSearchParams({
          calendarApiId,
          period: 'future',
          pagination_limit: '100',
        });
        if (cursor) params.set('pagination_cursor', cursor);

        let data;
        try {
          data = await fetchJson(`${LUMA_API}?${params}`);
        } catch (err) {
          if (!cursor) throw err;   // first page = real error
          break;
        }

        const entries = data?.entries ?? data?.items ?? [];
        if (!Array.isArray(entries) || entries.length === 0) break;

        for (const entry of entries) {
          const ev = entry.event ?? entry;

          const name = ev.name ?? ev.title ?? '';
          if (!name) continue;

          const date_start = toIsoDate(ev.start_at ?? ev.starts_at ?? '');
          const date_end   = toIsoDate(ev.end_at   ?? ev.ends_at   ?? '');

          const description = stripHtml(ev.description ?? '').slice(0, 400).trim();

          // Lu.ma returns geo_address_info with city/country
          const geo   = ev.geo_address_info ?? {};
          const location = [geo.city, geo.country].filter(Boolean).join(', ')
            || (ev.location ?? '');

          const website = ev.url
            ? (ev.url.startsWith('http') ? ev.url : `https://lu.ma/${ev.url}`)
            : (ev.slug ? `https://lu.ma/${ev.slug}` : '');

          const image = ev.cover_url ?? ev.image_url ?? '';

          const orientations = inferOrientations(name, description);
          const { continent, subregion } = inferGeo(location, description);
          const format = inferFormat(location, description)
            || (ev.geo_latitude ? 'in-person' : '');
          const type = inferType(name, description);

          // Country code from Lu.ma
          const country = geo.country_code ? [geo.country_code.toUpperCase()] : [];

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
            country,
            orientations: orientations.length ? orientations : defaultOrientations,
            continent,
            subregion,
            _source: sourceLabel,
          });
        }

        cursor = data?.next_cursor ?? data?.pagination?.next_cursor ?? null;
        if (!cursor || entries.length < 100) break;
      }

      return results;
    },
  };
}

// ── Configured calendars ──────────────────────────────────────────────────────
// NOTE: Luma's programmatic API (/calendar/get-items) now requires an API key.
// To use this scraper you need either:
//   A) A Luma API key: set LUMA_API_KEY env var and add header
//      'x-luma-api-key': process.env.LUMA_API_KEY to the fetch call above.
//   B) The iCal subscription URL from the org's Luma calendar settings
//      (use icalFeed() from ical.mjs instead — see example there).
//
// To find a calendarApiId: open the org's Luma calendar in a browser,
// open DevTools → Network → filter for "get-items" — the calendarApiId
// appears in the request URL.
//
// Metagov is served via researchseminars.org/ics instead (configured in ical.mjs).

// Placeholder — uncomment and fill in once you have the calendar ID + API key:
// export const democracyNext = lumaCalendar('cal-XXXXXXXX', 'Democracy Next', ['ASSEMBLY']);
// export const refiDao       = lumaCalendar('cal-XXXXXXXX', 'ReFi DAO', ['SPACESHIP', 'GARDEN']);
