/**
 * import-actors.mjs — import a reviewed actors staging file into actors.json
 *
 * Run:
 *   node scripts/import-actors.mjs scripts/review/actors-2026-04-26.json
 *
 * What it does:
 *   - Validates each actor (slug, name, continent required)
 *   - Deduplicates against current actors.json (by slug and normalised name)
 *   - Appends new actors to actors.json, sorted alphabetically by slug
 *   - Prints a summary of what was added and what was skipped
 *
 * Repeatable workflow (run again any time to add more actors from a region):
 *   1. Generate a staging file (manually or via a research agent)
 *   2. Review it — remove entries you don't want, fill in gaps
 *   3. node scripts/import-actors.mjs <path>
 *   4. npm run build   (verify no TS errors)
 *   5. git add src/data/actors.json && git commit && git push
 */

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname  = dirname(fileURLToPath(import.meta.url));
const root       = join(__dirname, '..');
const actorsPath = join(root, 'src', 'data', 'actors.json');

// ── Args ──────────────────────────────────────────────────────────────────────
const reviewFile = process.argv[2];
if (!reviewFile) {
  console.error('Usage: node scripts/import-actors.mjs <path-to-staging-file.json>');
  process.exit(1);
}

// ── Load ──────────────────────────────────────────────────────────────────────
const existing = JSON.parse(readFileSync(actorsPath, 'utf8'));
let candidates;
try {
  candidates = JSON.parse(readFileSync(reviewFile, 'utf8'));
} catch (err) {
  console.error(`Could not read staging file: ${err.message}`);
  process.exit(1);
}
if (!Array.isArray(candidates)) {
  console.error('Staging file must be a JSON array.');
  process.exit(1);
}

// ── Validate ──────────────────────────────────────────────────────────────────
const REQUIRED = ['slug', 'name', 'continent'];
const INTERNAL = ['_source', '_score', '_raw', '_region'];

// Ensure all expected schema fields are present (add blanks if missing)
const BLANK_ACTOR = {
  slug: '', name: '', type: '', description: '', about: '', website: '',
  location: '', scale: '', orientations: [], tags: [], continent: '',
  subregion: '', country: [], bioregion: [], peoples: [], languages: [],
};

const existingSlugs  = new Set(existing.map(a => a.slug));
function normName(n) { return n.toLowerCase().replace(/[^a-z0-9]/g, ''); }
const existingNames  = new Set(existing.map(a => normName(a.name)));

const toAdd   = [];
const skipped = [];

for (const raw of candidates) {
  // Strip internal fields
  const actor = { ...BLANK_ACTOR };
  for (const [k, v] of Object.entries(raw)) {
    if (!INTERNAL.includes(k)) actor[k] = v;
  }

  // Validate required
  const missing = REQUIRED.filter(f => !actor[f]);
  if (missing.length) {
    skipped.push({ name: actor.name || '(unnamed)', reason: `missing: ${missing.join(', ')}` });
    continue;
  }

  // Dedup by slug
  if (existingSlugs.has(actor.slug)) {
    skipped.push({ name: actor.name, reason: `slug already exists: ${actor.slug}` });
    continue;
  }

  // Dedup by normalised name
  if (existingNames.has(normName(actor.name))) {
    skipped.push({ name: actor.name, reason: 'name already exists (normalised match)' });
    continue;
  }

  toAdd.push(actor);
  existingSlugs.add(actor.slug);
  existingNames.add(normName(actor.name));
}

// ── Summary ───────────────────────────────────────────────────────────────────
console.log(`\nStaging file: ${reviewFile}`);
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
toAdd.forEach(a => console.log(`  ✓ [${a.continent}] ${a.name}`));

// ── Write ─────────────────────────────────────────────────────────────────────
const merged = [...existing, ...toAdd]
  .sort((a, b) => a.slug.localeCompare(b.slug));

writeFileSync(actorsPath, JSON.stringify(merged, null, 2) + '\n', 'utf8');
console.log(`\n✓ actors.json updated (${existing.length} → ${merged.length} actors)`);
console.log('\nRemember to run: npm run build   to verify before committing.');
