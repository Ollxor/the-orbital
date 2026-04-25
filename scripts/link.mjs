/**
 * link.mjs — manual relationship linker
 *
 * Wire up actors↔projects↔events without editing JSON by hand.
 *
 * Usage examples:
 *   node scripts/link.mjs --actor=sortition-foundation --project=858-project
 *   node scripts/link.mjs --actor=digidem-lab --event=nordic-forum-2025
 *   node scripts/link.mjs --project=vtaiwan --event=civic-tech-summit-2025
 *   node scripts/link.mjs --unlink --actor=sortition-foundation --project=858-project
 *
 * Flags:
 *   --actor=<slug>    actor slug (from actors.json)
 *   --project=<slug>  project slug (from projects.json)
 *   --event=<slug>    event slug (from events.json)
 *   --unlink          remove the link instead of adding it
 *   --dry-run         print what would change without writing files
 *
 * Rules:
 *   --actor + --project  → adds actor to project.actors[] AND project slug
 *                          to the actor's projects (printed, not stored — actors
 *                          don't have a projects[] field yet; update manually if needed)
 *   --actor + --event    → adds actor to event.actors[]
 *   --project + --event  → adds project to event.linked_projects[]
 *                          AND event to project.linked_events[]
 *   All three together   → does all of the above
 */

import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

// ── Parse args ──────────────────────────────────────────────────────────────
const args = Object.fromEntries(
  process.argv.slice(2)
    .filter(a => a.startsWith('--'))
    .map(a => {
      const [k, v] = a.slice(2).split('=');
      return [k, v ?? true];
    })
);

const actorSlug   = args.actor   ?? null;
const projectSlug = args.project ?? null;
const eventSlug   = args.event   ?? null;
const unlink      = args.unlink  === true || args.unlink === 'true';
const dryRun      = args['dry-run'] === true || args['dry-run'] === 'true';

if (!actorSlug && !projectSlug && !eventSlug) {
  console.error('Usage: node scripts/link.mjs [--actor=<slug>] [--project=<slug>] [--event=<slug>] [--unlink] [--dry-run]');
  process.exit(1);
}
if (!actorSlug && !projectSlug && !eventSlug) {
  console.error('Provide at least two of --actor, --project, --event to create a link.');
  process.exit(1);
}

// ── Load data ────────────────────────────────────────────────────────────────
const ACTORS_PATH   = join(root, 'src', 'data', 'actors.json');
const PROJECTS_PATH = join(root, 'src', 'data', 'projects.json');
const EVENTS_PATH   = join(root, 'src', 'data', 'events.json');

const actors   = JSON.parse(readFileSync(ACTORS_PATH, 'utf8'));
const projects = JSON.parse(readFileSync(PROJECTS_PATH, 'utf8'));
const events   = JSON.parse(readFileSync(EVENTS_PATH, 'utf8'));

// ── Validate slugs ───────────────────────────────────────────────────────────
function findActor(slug)   { return actors.find(a => a.slug === slug); }
function findProject(slug) { return projects.find(p => p.slug === slug); }
function findEvent(slug)   { return events.find(e => e.slug === slug); }

let ok = true;
if (actorSlug   && !findActor(actorSlug))   { console.error(`✗ Actor not found: ${actorSlug}`);   ok = false; }
if (projectSlug && !findProject(projectSlug)) { console.error(`✗ Project not found: ${projectSlug}`); ok = false; }
if (eventSlug   && !findEvent(eventSlug))   { console.error(`✗ Event not found: ${eventSlug}`);   ok = false; }
if (!ok) process.exit(1);

// ── Link/unlink helpers ──────────────────────────────────────────────────────
function addToArray(arr, value) {
  if (!Array.isArray(arr)) return [value];
  if (arr.includes(value)) return arr;
  return [...arr, value];
}
function removeFromArray(arr, value) {
  if (!Array.isArray(arr)) return [];
  return arr.filter(v => v !== value);
}
function mutate(arr, value) {
  return unlink ? removeFromArray(arr, value) : addToArray(arr, value);
}

const verb  = unlink ? 'Unlinked' : 'Linked';
const arrow = unlink ? '✗' : '✓';
const changes = [];

// ── actor ↔ project ──────────────────────────────────────────────────────────
if (actorSlug && projectSlug) {
  const p = findProject(projectSlug);
  const before = [...(p.actors ?? [])];
  p.actors = mutate(p.actors ?? [], actorSlug);
  if (JSON.stringify(before) !== JSON.stringify(p.actors)) {
    changes.push({ file: 'projects.json', data: projects });
    console.log(`${arrow} ${verb}: actor "${actorSlug}" in project "${projectSlug}".actors[]`);
  } else {
    console.log(`  (no change) actor "${actorSlug}" already ${unlink ? 'absent from' : 'present in'} project "${projectSlug}".actors[]`);
  }
}

// ── actor ↔ event ────────────────────────────────────────────────────────────
if (actorSlug && eventSlug) {
  const e = findEvent(eventSlug);
  const before = [...(e.actors ?? [])];
  e.actors = mutate(e.actors ?? [], actorSlug);
  if (JSON.stringify(before) !== JSON.stringify(e.actors)) {
    changes.push({ file: 'events.json', data: events });
    console.log(`${arrow} ${verb}: actor "${actorSlug}" in event "${eventSlug}".actors[]`);
  } else {
    console.log(`  (no change) actor "${actorSlug}" already ${unlink ? 'absent from' : 'present in'} event "${eventSlug}".actors[]`);
  }
}

// ── project ↔ event ──────────────────────────────────────────────────────────
if (projectSlug && eventSlug) {
  const p = findProject(projectSlug);
  const e = findEvent(eventSlug);

  const pbefore = [...(p.linked_events ?? [])];
  p.linked_events = mutate(p.linked_events ?? [], eventSlug);
  if (JSON.stringify(pbefore) !== JSON.stringify(p.linked_events)) {
    if (!changes.find(c => c.file === 'projects.json')) changes.push({ file: 'projects.json', data: projects });
    console.log(`${arrow} ${verb}: event "${eventSlug}" in project "${projectSlug}".linked_events[]`);
  } else {
    console.log(`  (no change) event "${eventSlug}" already ${unlink ? 'absent from' : 'present in'} project "${projectSlug}".linked_events[]`);
  }

  const ebefore = [...(e.linked_projects ?? [])];
  e.linked_projects = mutate(e.linked_projects ?? [], projectSlug);
  if (JSON.stringify(ebefore) !== JSON.stringify(e.linked_projects)) {
    if (!changes.find(c => c.file === 'events.json')) changes.push({ file: 'events.json', data: events });
    console.log(`${arrow} ${verb}: project "${projectSlug}" in event "${eventSlug}".linked_projects[]`);
  } else {
    console.log(`  (no change) project "${projectSlug}" already ${unlink ? 'absent from' : 'present in'} event "${eventSlug}".linked_projects[]`);
  }
}

// ── Write ────────────────────────────────────────────────────────────────────
if (changes.length === 0) {
  console.log('Nothing to write.');
  process.exit(0);
}

if (dryRun) {
  console.log('\n[dry-run] No files written.');
  process.exit(0);
}

const FILE_MAP = {
  'actors.json':   { path: ACTORS_PATH,   data: actors },
  'projects.json': { path: PROJECTS_PATH, data: projects },
  'events.json':   { path: EVENTS_PATH,   data: events },
};

const written = new Set(changes.map(c => c.file));
written.forEach(file => {
  const { path, data } = FILE_MAP[file];
  writeFileSync(path, JSON.stringify(data, null, 2) + '\n', 'utf8');
  console.log(`  Wrote ${file}`);
});
