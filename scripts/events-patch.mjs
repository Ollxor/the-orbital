/**
 * events-patch.mjs
 * Adds new empty fields to all events (no content backfill).
 * Existing field names (date_start, date_end, type) are preserved.
 *
 * Run: node scripts/events-patch.mjs
 */
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA = join(__dirname, '..', 'src', 'data', 'events.json');

const events = JSON.parse(readFileSync(DATA, 'utf8'));

const updated = events.map(e => ({
  ...e,
  // New fields — empty, no auto-backfill
  format:          e.format          ?? '',   // in-person | online | hybrid
  cost:            e.cost            ?? '',   // free | paid | sliding-scale
  languages:       e.languages       ?? [],   // ISO 639-1
  continent:       e.continent       ?? '',
  subregion:       e.subregion       ?? '',
  country:         e.country         ?? [],
  scale:           e.scale           ?? '',
  bioregion:       e.bioregion       ?? [],
  peoples:         e.peoples         ?? [],
  linked_projects: e.linked_projects ?? [],
}));

writeFileSync(DATA, JSON.stringify(updated, null, 2) + '\n', 'utf8');
console.log(`Patched ${updated.length} events. New fields added: format, cost, languages, continent, subregion, country, scale, bioregion, peoples, linked_projects`);
