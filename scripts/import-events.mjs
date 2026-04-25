/**
 * import-events.mjs — import a reviewed events file into events.json
 *
 * Run:
 *   node scripts/import-events.mjs scripts/review/events-2026-04-25.json
 *
 * What it does:
 *   - Validates each event (slug, name, date_start required)
 *   - Strips internal fields (_source, etc.)
 *   - Deduplicates against current events.json (by slug and normalised name)
 *   - Appends new events to events.json, sorted by date_start descending
 *   - Prints a summary of what was added and what was skipped
 */

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname  = dirname(fileURLToPath(import.meta.url));
const root       = join(__dirname, '..');
const eventsPath = join(root, 'src', 'data', 'events.json');

// ── Args ──────────────────────────────────────────────────────────────────────
const reviewFile = process.argv[2];
if (!reviewFile) {
  console.error('Usage: node scripts/import-events.mjs <path-to-review-file.json>');
  process.exit(1);
}

// ── Load ──────────────────────────────────────────────────────────────────────
const existing = JSON.parse(readFileSync(eventsPath, 'utf8'));
let candidates;
try {
  candidates = JSON.parse(readFileSync(reviewFile, 'utf8'));
} catch (err) {
  console.error(`Could not read review file: ${err.message}`);
  process.exit(1);
}

if (!Array.isArray(candidates)) {
  console.error('Review file must be a JSON array.');
  process.exit(1);
}

// ── Validate ──────────────────────────────────────────────────────────────────
// Required fields that must be set before importing
const REQUIRED = ['slug', 'name', 'date_start'];
// Internal fields to strip before writing
const INTERNAL = ['_source', '_score', '_raw'];

const existingSlugs = new Set(existing.map(e => e.slug));
function normTitle(t) { return t.toLowerCase().replace(/[^a-z0-9]/g, ''); }
const existingTitles = new Set(existing.map(e => normTitle(e.name)));

const toAdd  = [];
const skipped = [];

for (const ev of candidates) {
  // Validate required
  const missing = REQUIRED.filter(f => !ev[f]);
  if (missing.length) {
    skipped.push({ name: ev.name ?? '(unnamed)', reason: `missing: ${missing.join(', ')}` });
    continue;
  }

  // Dedup
  if (existingSlugs.has(ev.slug)) {
    skipped.push({ name: ev.name, reason: `slug already exists: ${ev.slug}` });
    continue;
  }
  if (existingTitles.has(normTitle(ev.name))) {
    skipped.push({ name: ev.name, reason: 'name already exists (normalised match)' });
    continue;
  }

  // Strip internal fields
  const clean = { ...ev };
  INTERNAL.forEach(f => delete clean[f]);

  toAdd.push(clean);
  existingSlugs.add(clean.slug);
  existingTitles.add(normTitle(clean.name));
}

// ── Summary ───────────────────────────────────────────────────────────────────
console.log(`\nReview file: ${reviewFile}`);
console.log(`  Candidates: ${candidates.length}`);
console.log(`  To add:     ${toAdd.length}`);
console.log(`  Skipped:    ${skipped.length}`);

if (skipped.length) {
  console.log('\nSkipped:');
  skipped.forEach(s => console.log(`  ✗ ${s.name} — ${s.reason}`));
}

if (toAdd.length === 0) {
  console.log('\nNothing to import.');
  process.exit(0);
}

console.log('\nAdding:');
toAdd.forEach(e => console.log(`  ✓ [${e.date_start}] ${e.name}`));

// ── Write ─────────────────────────────────────────────────────────────────────
const merged = [...existing, ...toAdd]
  .sort((a, b) => (b.date_start || '').localeCompare(a.date_start || ''));

writeFileSync(eventsPath, JSON.stringify(merged, null, 2) + '\n', 'utf8');
console.log(`\n✓ events.json updated (${existing.length} → ${merged.length} events)`);
console.log('\nRemember to run: npm run build   to verify before committing.');
