/**
 * scrape-events.mjs — fetch events from all configured sources,
 * deduplicate against events.json, and write a review file.
 *
 * Run:
 *   node scripts/scrape-events.mjs
 *   node scripts/scrape-events.mjs --source=garn         # single source
 *   node scripts/scrape-events.mjs --dry-run             # print summary, no file
 *   node scripts/scrape-events.mjs --future-only=false   # include past events too
 *
 * Output:
 *   scripts/review/events-YYYY-MM-DD.json
 *
 * After reviewing the output file (remove unwanted events, fill in blanks,
 * assign orientations), run:
 *   node scripts/import-events.mjs scripts/review/events-YYYY-MM-DD.json
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { dedup } from './scrapers/_base.mjs';

// ── Scrapers ──────────────────────────────────────────────────────────────────
// Import each scraper module. Add new sources here.
import * as garn from './scrapers/garn.mjs';
import { metagovSeminars } from './scrapers/ical.mjs';
// import { democracyNext } from './scrapers/luma.mjs';   // needs Luma API key
// import * as involve from './scrapers/involve.mjs';     // Cloudflare-blocked, add when bypass found
// import { unfcccEvents } from './scrapers/ical.mjs';    // add iCal URL when found

// Registry: [scraper object, enabled]
// Set enabled=false to skip a source without removing it.
const SCRAPERS = [
  [garn,            true],
  [metagovSeminars, true],
  // [democracyNext,  true],
  // [involve,        true],
  // [unfcccEvents,   true],
];

// ── Args ──────────────────────────────────────────────────────────────────────
const args = Object.fromEntries(
  process.argv.slice(2)
    .filter(a => a.startsWith('--'))
    .map(a => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; })
);
const filterSource  = args.source ?? null;
const dryRun        = args['dry-run'] === true || args['dry-run'] === 'true';
const futureOnly    = (args['future-only'] ?? 'true') !== 'false';

// ── Paths ─────────────────────────────────────────────────────────────────────
const __dirname   = dirname(fileURLToPath(import.meta.url));
const root        = join(__dirname, '..');
const eventsPath  = join(root, 'src', 'data', 'events.json');
const reviewDir   = join(__dirname, 'review');
const today       = new Date().toISOString().slice(0, 10);
const reviewPath  = join(reviewDir, `events-${today}.json`);

const existingEvents = JSON.parse(readFileSync(eventsPath, 'utf8'));

// ── Run scrapers ──────────────────────────────────────────────────────────────
const allCandidates = [];
const stats = [];

for (const [scraper, enabled] of SCRAPERS) {
  if (!enabled) continue;
  const label = scraper.SOURCE_LABEL ?? scraper.name ?? '?';
  if (filterSource && !label.toLowerCase().includes(filterSource.toLowerCase())) continue;

  process.stdout.write(`  Fetching ${label}… `);
  const t0 = Date.now();
  try {
    const results = await scraper.scrape();
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`${results.length} events (${elapsed}s)`);
    allCandidates.push(...results);
    stats.push({ label, found: results.length, error: null });
  } catch (err) {
    console.log(`ERROR: ${err.message}`);
    stats.push({ label, found: 0, error: err.message });
  }
}

// ── Filter future-only ────────────────────────────────────────────────────────
const todayIso = today;
const filtered = futureOnly
  ? allCandidates.filter(e => !e.date_start || e.date_start >= todayIso)
  : allCandidates;

// ── Deduplicate ───────────────────────────────────────────────────────────────
const novel = dedup(filtered, existingEvents);

// ── Summary ───────────────────────────────────────────────────────────────────
console.log('\n── Summary ──────────────────────────────────────────────');
for (const s of stats) {
  if (s.error) console.log(`  ✗ ${s.label}: ${s.error}`);
  else         console.log(`  ✓ ${s.label}: ${s.found} fetched`);
}
console.log(`\n  Total fetched:   ${allCandidates.length}`);
console.log(`  After date filter: ${filtered.length}`);
console.log(`  Novel (not in events.json): ${novel.length}`);

if (novel.length === 0) {
  console.log('\n  Nothing new to review. Exiting.');
  process.exit(0);
}

if (dryRun) {
  console.log('\n  [dry-run] Would write:');
  novel.forEach(e => console.log(`    ${e.date_start}  ${e.name}  [${e._source}]`));
  process.exit(0);
}

// ── Write review file ─────────────────────────────────────────────────────────
if (!existsSync(reviewDir)) mkdirSync(reviewDir, { recursive: true });

// Strip internal _source from the written file but keep as a comment-style field
// for visibility during review (it's removed by import-events.mjs)
const reviewData = novel.map(e => {
  const { _source, ...rest } = e;
  return { ...rest, _source };   // keep at end for readability
});

writeFileSync(reviewPath, JSON.stringify(reviewData, null, 2) + '\n', 'utf8');

console.log(`\n  ✓ Review file written: ${reviewPath}`);
console.log('\nNext steps:');
console.log('  1. Open the review file and remove events that don\'t belong');
console.log('  2. Fill in: orientations, tags, actors, relevance_note, scale');
console.log('  3. Run: node scripts/import-events.mjs ' + reviewPath);
