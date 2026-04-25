/**
 * ical.mjs — generic iCal (.ics) feed parser
 *
 * Many governance orgs expose iCal feeds. Pass the feed URL and a label.
 * Usage:
 *
 *   import { icalFeed } from './ical.mjs';
 *   export const myOrg = icalFeed('https://example.com/events.ics', 'My Org', ['ASSEMBLY']);
 *
 * To find an iCal feed URL:
 *   - Look for "Subscribe to calendar", "Add to Google Calendar", or "Export (.ics)" links
 *   - Many WordPress event plugins expose /events/feed/?post_type=event
 *   - Google Calendar public feeds: calendar.google.com/calendar/ical/...
 */

import {
  blankEvent, slugify, toIsoDate, stripHtml,
  inferOrientations, inferGeo, inferFormat, inferType,
  fetchText,
} from './_base.mjs';

// ── Minimal iCal parser ───────────────────────────────────────────────────────
function parseIcal(text) {
  const events = [];
  const blocks = text.split(/BEGIN:VEVENT/i).slice(1);

  for (const block of blocks) {
    const end = block.indexOf('END:VEVENT');
    const body = end >= 0 ? block.slice(0, end) : block;

    // Unfold continuation lines (RFC 5545)
    const unfolded = body.replace(/\r?\n[ \t]/g, '');

    function prop(name) {
      // Match PROPNAME or PROPNAME;PARAM=VAL
      const re = new RegExp(`^${name}(?:;[^:]+)?:(.*)`, 'im');
      const m = unfolded.match(re);
      return m ? m[1].trim() : '';
    }

    // Decode iCal text escaping
    function decode(s) {
      return s.replace(/\\n/g, '\n').replace(/\\,/g, ',').replace(/\\;/g, ';').replace(/\\\\/g, '\\');
    }

    // Parse DTSTART / DTEND — handle YYYYMMDD and YYYYMMDDTHHmmssZ formats
    function parseDate(raw) {
      if (!raw) return '';
      const stripped = raw.replace(/;[^:]*:/g, '').trim();
      if (/^\d{8}T\d{6}/.test(stripped)) {
        // YYYYMMDDTHHmmss[Z]
        const y = stripped.slice(0, 4);
        const mo = stripped.slice(4, 6);
        const d = stripped.slice(6, 8);
        return `${y}-${mo}-${d}`;
      }
      if (/^\d{8}$/.test(stripped)) {
        return `${stripped.slice(0, 4)}-${stripped.slice(4, 6)}-${stripped.slice(6, 8)}`;
      }
      return toIsoDate(stripped);
    }

    const summary     = decode(prop('SUMMARY'));
    const dtstart     = parseDate(prop('DTSTART'));
    const dtend       = parseDate(prop('DTEND'));
    const location    = decode(prop('LOCATION'));
    const url         = prop('URL');
    const rawDesc     = prop('DESCRIPTION');
    const desc        = decode(stripHtml(rawDesc)).slice(0, 600).trim();
    const uid         = prop('UID');

    if (!summary || !dtstart) continue;

    // Try to extract a talk title from description HTML.
    // researchseminars.org format: "Title: <a href="...">Talk Title</a>\nby Speaker..."
    // Fall back to summary if nothing is found.
    const titleMatch = rawDesc.match(/Title:\s*(?:<[^>]+>)?([^<\n\\]+)/i);
    const talkTitle  = titleMatch ? decode(titleMatch[1].trim()) : null;

    events.push({ summary, talkTitle, dtstart, dtend, location, url, desc, uid });
  }

  return events;
}

// ── Factory ───────────────────────────────────────────────────────────────────
export function icalFeed(feedUrl, sourceLabel, defaultOrientations = []) {
  return {
    SOURCE_LABEL: sourceLabel,
    SOURCE_URL:   feedUrl,

    async scrape() {
      const text = await fetchText(feedUrl);
      const parsed = parseIcal(text);

      return parsed.map(item => {
        // Use extracted talk title if available, otherwise fall back to SUMMARY
        const name = item.talkTitle || item.summary;
        const orientations = inferOrientations(name, item.desc);
        const { continent, subregion } = inferGeo(item.location, item.desc);
        const format = inferFormat(item.location, item.desc);
        const type   = inferType(name, item.desc);

        return {
          ...blankEvent(),
          slug:        slugify(name, item.dtstart),
          name,
          description: item.desc.slice(0, 400),
          date_start:  item.dtstart,
          date_end:    item.dtend,
          location:    item.location,
          website:     item.url,
          type,
          format,
          orientations: orientations.length ? orientations : defaultOrientations,
          continent,
          subregion,
          _source: sourceLabel,
        };
      });
    },
  };
}

// ── Configured iCal feeds ─────────────────────────────────────────────────────

// Metagov academic seminar series — governance of digital infrastructure,
// DAOs, collective intelligence, AI governance
export const metagovSeminars = icalFeed(
  'https://researchseminars.org/seminar/Metagov/ics',
  'Metagov Seminars',
  ['SPACESHIP', 'ASSEMBLY'],
);

// ── Add more feeds here ───────────────────────────────────────────────────────
// To find an iCal URL: look for "Subscribe to calendar" / "Add to Google Calendar"
// links, or check /events/feed/ on WordPress sites.

// export const unfcccEvents = icalFeed(
//   'https://unfccc.int/events/calendar/feed.ics',
//   'UNFCCC Events',
//   ['ASSEMBLY', 'GARDEN'],
// );

// export const icleiEvents = icalFeed(
//   'https://iclei.org/events.ics',
//   'ICLEI Events',
//   ['ASSEMBLY', 'SPACESHIP'],
// );

// Luma calendar iCal: find the subscription URL from your org's Luma calendar
// settings page (Settings → Calendar → "Subscribe" → copy .ics URL)
// export const myLumaCalendar = icalFeed(
//   'https://api.lu.ma/ical/calendar/cal-XXXXXXXX',
//   'Org Name (Luma)',
//   ['ASSEMBLY'],
// );
