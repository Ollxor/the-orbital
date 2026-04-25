/**
 * projects-patch.mjs
 * - Renames `stage` → `status` on every project
 * - Normalises status values to canonical enum
 * - Adds new empty fields (no geo backfill)
 *
 * Run: node scripts/projects-patch.mjs
 */
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA = join(__dirname, '..', 'src', 'data', 'projects.json');

const STATUS_MAP = {
  'Active':      'active',
  'active':      'active',
  'Early':       'planned',
  'early':       'planned',
  'deployed':    'active',
  'pilot':       'active',
  'in-progress': 'active',
  'complete':    'completed',
  'completed':   'completed',
  'concept':     'planned',
  'planned':     'planned',
  'paused':      'paused',
  'archived':    'archived',
};

const projects = JSON.parse(readFileSync(DATA, 'utf8'));

const updated = projects.map(p => {
  // Destructure out `stage` so it disappears
  const { stage, ...rest } = p;
  const rawStatus = (stage ?? '').trim();
  const normalizedStatus = STATUS_MAP[rawStatus] ?? 'active';

  return {
    ...rest,
    // Normalised status replaces stage
    status:       normalizedStatus,
    // New fields — empty, no auto-backfill
    project_type: p.project_type  ?? '',
    openness:     p.openness      ?? '',
    start_date:   p.start_date    ?? '',
    end_date:     p.end_date      ?? '',
    continent:    p.continent     ?? '',
    subregion:    p.subregion     ?? '',
    country:      p.country       ?? [],
    scale:        p.scale         ?? '',
    bioregion:    p.bioregion     ?? [],
    peoples:      p.peoples       ?? [],
    linked_events:p.linked_events ?? [],
  };
});

writeFileSync(DATA, JSON.stringify(updated, null, 2) + '\n', 'utf8');

console.log(`Patched ${updated.length} projects\n`);
console.log('Status breakdown:');
const counts = {};
updated.forEach(p => { counts[p.status] = (counts[p.status] || 0) + 1; });
Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([s,n]) => console.log(`  ${s}: ${n}`));
console.log('\nFull mapping:');
updated.forEach(p => console.log(`  [${p.status.padEnd(9)}]  ${p.slug}`));
