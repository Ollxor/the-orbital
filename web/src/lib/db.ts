import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.resolve(__dirname, '../../../garden.db');

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(dbPath, { readonly: true });
    _db.pragma('foreign_keys = ON');
  }
  return _db;
}

// ─── Types ───────────────────────────────────────────────

export interface Actor {
  id: number;
  name: string;
  type: string;
  primary_orientation_id: number | null;
  secondary_orientation_id: number | null;
  description: string | null;
  website: string | null;
  domain: string | null;
  location: string | null;
  scale: string | null;
  maturity: string | null;
  relevance_score: number;
  connection: string | null;
  contact_pathway: string | null;
  canonical_id: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  // joined fields
  orientation_code?: string;
  orientation_name?: string;
  secondary_orientation_code?: string;
  secondary_orientation_name?: string;
  intel_count?: number;
  source_count?: number;
  people_count?: number;
  project_count?: number;
  category_count?: number;
}

export interface Project {
  id: number;
  name: string;
  website: string | null;
  description: string | null;
  geography: string | null;
  stage: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  // joined
  actor_count?: number;
}

export interface Person {
  id: number;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  linkedin_url: string | null;
  primary_orientation_id: number | null;
  skills: string | null;
  relationship_tier: string | null;
  status: string | null;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  // joined
  orientation_code?: string;
  orientation_name?: string;
  role?: string;
}

export interface Orientation {
  id: number;
  code: string;
  name: string;
  description: string | null;
  actor_count?: number;
  category_count?: number;
}

export interface Category {
  id: number;
  orientation_id: number;
  name: string;
  description: string | null;
  search_terms: string | null;
  actor_types: string | null;
  orientation_code?: string;
  actor_count?: number;
}

export interface Source {
  id: number;
  url: string;
  title: string | null;
  description: string | null;
  last_fetch: string | null;
  monitor: number;
}

export interface Intel {
  id: number;
  entity_type: string;
  entity_id: number;
  field: string;
  value: string;
  source_id: number | null;
  confidence: string;
}

export interface Flag {
  id: number;
  actor_id: number;
  flag_type: string;
  notes: string | null;
}

export interface Image {
  id: number;
  entity_type: string;
  entity_id: number;
  filename: string;
  alt_text: string | null;
  caption: string | null;
  sort_order: number;
}

export interface Tag {
  id: number;
  name: string;
  actor_count?: number;
  project_count?: number;
  person_count?: number;
  total_count?: number;
}

// ─── Orientation queries ─────────────────────────────────

export function getAllOrientations(): Orientation[] {
  const db = getDb();
  return db.prepare(`
    SELECT o.*,
      (SELECT COUNT(*) FROM actors a WHERE a.primary_orientation_id = o.id AND a.canonical_id IS NULL) as actor_count,
      (SELECT COUNT(*) FROM categories c WHERE c.orientation_id = o.id) as category_count
    FROM orientations o ORDER BY o.id
  `).all() as Orientation[];
}

export function getOrientation(code: string): Orientation | undefined {
  const db = getDb();
  return db.prepare(`
    SELECT o.*,
      (SELECT COUNT(*) FROM actors a WHERE a.primary_orientation_id = o.id AND a.canonical_id IS NULL) as actor_count,
      (SELECT COUNT(*) FROM categories c WHERE c.orientation_id = o.id) as category_count
    FROM orientations o WHERE o.code = ?
  `).get(code) as Orientation | undefined;
}

export function getOrientationCategories(orientationId: number): Category[] {
  const db = getDb();
  return db.prepare(`
    SELECT c.*,
      (SELECT COUNT(*) FROM actor_category ac WHERE ac.category_id = c.id) as actor_count
    FROM categories c WHERE c.orientation_id = ? ORDER BY c.name
  `).all(orientationId) as Category[];
}

export function getOrientationActors(orientationId: number): Actor[] {
  const db = getDb();
  return db.prepare(`
    SELECT a.*, o.code as orientation_code, o.name as orientation_name
    FROM actors a
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE a.primary_orientation_id = ? AND a.canonical_id IS NULL
    ORDER BY a.relevance_score DESC, a.name
  `).all(orientationId) as Actor[];
}

// ─── Actor queries ───────────────────────────────────────

export function getAllActors(): Actor[] {
  const db = getDb();
  return db.prepare(`
    SELECT a.*,
      o.code as orientation_code, o.name as orientation_name,
      o2.code as secondary_orientation_code, o2.name as secondary_orientation_name,
      (SELECT COUNT(*) FROM intel i WHERE i.entity_type='actor' AND i.entity_id=a.id) as intel_count,
      (SELECT COUNT(*) FROM source_actor sa WHERE sa.actor_id=a.id) as source_count,
      (SELECT COUNT(*) FROM person_actor pa WHERE pa.actor_id=a.id) as people_count,
      (SELECT COUNT(*) FROM project_actor pra WHERE pra.actor_id=a.id) as project_count
    FROM actors a
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    LEFT JOIN orientations o2 ON o2.id = a.secondary_orientation_id
    WHERE a.canonical_id IS NULL
    ORDER BY a.relevance_score DESC, a.name
  `).all() as Actor[];
}

export function getActor(id: number): Actor | undefined {
  const db = getDb();
  return db.prepare(`
    SELECT a.*,
      o.code as orientation_code, o.name as orientation_name,
      o2.code as secondary_orientation_code, o2.name as secondary_orientation_name
    FROM actors a
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    LEFT JOIN orientations o2 ON o2.id = a.secondary_orientation_id
    WHERE a.id = ?
  `).get(id) as Actor | undefined;
}

export function getActorCategories(actorId: number): Category[] {
  const db = getDb();
  return db.prepare(`
    SELECT c.*, o.code as orientation_code
    FROM categories c
    JOIN actor_category ac ON ac.category_id = c.id
    JOIN orientations o ON o.id = c.orientation_id
    WHERE ac.actor_id = ?
    ORDER BY c.name
  `).all(actorId) as Category[];
}

export function getActorPeople(actorId: number): Person[] {
  const db = getDb();
  return db.prepare(`
    SELECT p.*, pa.role,
      o.code as orientation_code, o.name as orientation_name
    FROM people p
    JOIN person_actor pa ON pa.person_id = p.id
    LEFT JOIN orientations o ON o.id = p.primary_orientation_id
    WHERE pa.actor_id = ?
    ORDER BY p.last_name, p.first_name
  `).all(actorId) as Person[];
}

export function getActorProjects(actorId: number): (Project & { relationship: string | null })[] {
  const db = getDb();
  return db.prepare(`
    SELECT p.*, pra.relationship
    FROM projects p
    JOIN project_actor pra ON pra.project_id = p.id
    WHERE pra.actor_id = ?
    ORDER BY p.name
  `).all(actorId) as (Project & { relationship: string | null })[];
}

export function getActorSources(actorId: number): Source[] {
  const db = getDb();
  return db.prepare(`
    SELECT s.*
    FROM sources s
    JOIN source_actor sa ON sa.source_id = s.id
    WHERE sa.actor_id = ?
    ORDER BY s.title
  `).all(actorId) as Source[];
}

export function getActorFlags(actorId: number): Flag[] {
  const db = getDb();
  return db.prepare(`
    SELECT * FROM flags WHERE actor_id = ? ORDER BY flag_type
  `).all(actorId) as Flag[];
}

export function getActorIntel(actorId: number): Intel[] {
  const db = getDb();
  return db.prepare(`
    SELECT * FROM intel WHERE entity_type = 'actor' AND entity_id = ? ORDER BY field
  `).all(actorId) as Intel[];
}

export function getRelatedActors(actorId: number, limit = 6): Actor[] {
  const db = getDb();
  // Actors sharing categories or orientation with this actor
  return db.prepare(`
    SELECT DISTINCT a.*, o.code as orientation_code, o.name as orientation_name
    FROM actors a
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE a.canonical_id IS NULL AND a.id != ?
      AND (
        a.primary_orientation_id = (SELECT primary_orientation_id FROM actors WHERE id = ?)
        OR a.id IN (
          SELECT ac2.actor_id FROM actor_category ac2
          WHERE ac2.category_id IN (SELECT ac.category_id FROM actor_category ac WHERE ac.actor_id = ?)
        )
      )
    ORDER BY a.relevance_score DESC
    LIMIT ?
  `).all(actorId, actorId, actorId, limit) as Actor[];
}

// ─── Project queries ─────────────────────────────────────

export function getAllProjects(): Project[] {
  const db = getDb();
  return db.prepare(`
    SELECT p.*,
      (SELECT COUNT(*) FROM project_actor pa WHERE pa.project_id = p.id) as actor_count
    FROM projects p ORDER BY p.name
  `).all() as Project[];
}

export function getProject(id: number): Project | undefined {
  const db = getDb();
  return db.prepare(`SELECT * FROM projects WHERE id = ?`).get(id) as Project | undefined;
}

export function getProjectActors(projectId: number): (Actor & { relationship: string | null })[] {
  const db = getDb();
  return db.prepare(`
    SELECT a.*, pra.relationship,
      o.code as orientation_code, o.name as orientation_name
    FROM actors a
    JOIN project_actor pra ON pra.actor_id = a.id
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE pra.project_id = ? AND a.canonical_id IS NULL
    ORDER BY a.name
  `).all(projectId) as (Actor & { relationship: string | null })[];
}

export function getProjectSources(projectId: number): Source[] {
  const db = getDb();
  return db.prepare(`
    SELECT s.*
    FROM sources s
    JOIN source_project sp ON sp.source_id = s.id
    WHERE sp.project_id = ?
    ORDER BY s.title
  `).all(projectId) as Source[];
}

export function getProjectIntel(projectId: number): Intel[] {
  const db = getDb();
  return db.prepare(`
    SELECT * FROM intel WHERE entity_type = 'project' AND entity_id = ? ORDER BY field
  `).all(projectId) as Intel[];
}

// ─── People queries ──────────────────────────────────────

export function getAllPeople(): Person[] {
  const db = getDb();
  return db.prepare(`
    SELECT p.*, o.code as orientation_code, o.name as orientation_name
    FROM people p
    LEFT JOIN orientations o ON o.id = p.primary_orientation_id
    ORDER BY p.relationship_tier, p.last_name, p.first_name
  `).all() as Person[];
}

export function getPerson(id: number): Person | undefined {
  const db = getDb();
  return db.prepare(`
    SELECT p.*, o.code as orientation_code, o.name as orientation_name
    FROM people p
    LEFT JOIN orientations o ON o.id = p.primary_orientation_id
    WHERE p.id = ?
  `).get(id) as Person | undefined;
}

export function getPersonActors(personId: number): (Actor & { role: string | null })[] {
  const db = getDb();
  return db.prepare(`
    SELECT a.*, pa.role,
      o.code as orientation_code, o.name as orientation_name
    FROM actors a
    JOIN person_actor pa ON pa.actor_id = a.id
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE pa.person_id = ? AND a.canonical_id IS NULL
    ORDER BY a.name
  `).all(personId) as (Actor & { role: string | null })[];
}

// ─── Image queries ───────────────────────────────────────

export function getEntityImages(entityType: string, entityId: number): Image[] {
  const db = getDb();
  return db.prepare(`
    SELECT * FROM images WHERE entity_type = ? AND entity_id = ? ORDER BY sort_order, id
  `).all(entityType, entityId) as Image[];
}

export function getActorImages(actorId: number): Image[] {
  return getEntityImages('actor', actorId);
}

export function getProjectImages(projectId: number): Image[] {
  return getEntityImages('project', projectId);
}

// ─── Source queries ──────────────────────────────────────

export function getAllSources(): Source[] {
  const db = getDb();
  return db.prepare(`SELECT * FROM sources ORDER BY title, url`).all() as Source[];
}

// ─── Category queries ───────────────────────────────────

export function getAllCategories(): Category[] {
  const db = getDb();
  return db.prepare(`
    SELECT c.*, o.code as orientation_code,
      (SELECT COUNT(*) FROM actor_category ac WHERE ac.category_id = c.id) as actor_count
    FROM categories c
    JOIN orientations o ON o.id = c.orientation_id
    ORDER BY o.code, c.name
  `).all() as Category[];
}

// ─── Tag queries ────────────────────────────────────────

export function getAllTags(): Tag[] {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT t.*,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'actor') as actor_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'project') as project_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'person') as person_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id) as total_count
      FROM tags t ORDER BY t.name
    `).all() as Tag[];
  } catch {
    return [];
  }
}

export function getTag(name: string): Tag | undefined {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT t.*,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'actor') as actor_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'project') as project_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id AND et.entity_type = 'person') as person_count,
        (SELECT COUNT(*) FROM entity_tag et WHERE et.tag_id = t.id) as total_count
      FROM tags t WHERE t.name = ?
    `).get(name) as Tag | undefined;
  } catch {
    return undefined;
  }
}

export function getEntityTags(entityType: string, entityId: number): Tag[] {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT t.* FROM tags t
      JOIN entity_tag et ON et.tag_id = t.id
      WHERE et.entity_type = ? AND et.entity_id = ?
      ORDER BY t.name
    `).all(entityType, entityId) as Tag[];
  } catch {
    return [];
  }
}

export function getActorTags(actorId: number): Tag[] {
  return getEntityTags('actor', actorId);
}

export function getProjectTags(projectId: number): Tag[] {
  return getEntityTags('project', projectId);
}

export function getPersonTags(personId: number): Tag[] {
  return getEntityTags('person', personId);
}

export function getTagActors(tagName: string): Actor[] {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT a.*, o.code as orientation_code, o.name as orientation_name
      FROM actors a
      JOIN entity_tag et ON et.entity_id = a.id AND et.entity_type = 'actor'
      JOIN tags t ON t.id = et.tag_id
      LEFT JOIN orientations o ON o.id = a.primary_orientation_id
      WHERE t.name = ? AND a.canonical_id IS NULL
      ORDER BY a.relevance_score DESC, a.name
    `).all(tagName) as Actor[];
  } catch {
    return [];
  }
}

export function getTagProjects(tagName: string): Project[] {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT p.* FROM projects p
      JOIN entity_tag et ON et.entity_id = p.id AND et.entity_type = 'project'
      JOIN tags t ON t.id = et.tag_id
      WHERE t.name = ?
      ORDER BY p.name
    `).all(tagName) as Project[];
  } catch {
    return [];
  }
}

export function getTagPeople(tagName: string): Person[] {
  const db = getDb();
  try {
    return db.prepare(`
      SELECT p.*, o.code as orientation_code, o.name as orientation_name
      FROM people p
      JOIN entity_tag et ON et.entity_id = p.id AND et.entity_type = 'person'
      JOIN tags t ON t.id = et.tag_id
      LEFT JOIN orientations o ON o.id = p.primary_orientation_id
      WHERE t.name = ?
      ORDER BY p.last_name, p.first_name
    `).all(tagName) as Person[];
  } catch {
    return [];
  }
}

// ─── Graph data ─────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: 'actor' | 'project' | 'person';
  orientation?: string;
  relevance?: number;
  entityId: number;
  actorType?: string;
  stage?: string;
  role?: string;
  location?: string;
  description?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  label?: string;
}

export function getGraphData(): { nodes: GraphNode[]; links: GraphLink[] } {
  const db = getDb();
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const nodeIds = new Set<string>();

  // ─── Nodes ───

  const actors = db.prepare(`
    SELECT a.id, a.name, a.type, a.relevance_score, a.location, a.description,
           o.code as orientation_code
    FROM actors a
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE a.canonical_id IS NULL
  `).all() as any[];

  for (const a of actors) {
    const nid = `actor-${a.id}`;
    nodeIds.add(nid);
    nodes.push({
      id: nid, label: a.name, type: 'actor', orientation: a.orientation_code,
      relevance: a.relevance_score, entityId: a.id, actorType: a.type,
      location: a.location, description: a.description,
    });
  }

  const projects = db.prepare(`SELECT id, name, stage, geography as location, description FROM projects`).all() as any[];
  for (const p of projects) {
    const nid = `project-${p.id}`;
    nodeIds.add(nid);
    nodes.push({
      id: nid, label: p.name, type: 'project', entityId: p.id,
      stage: p.stage, location: p.location, description: p.description,
    });
  }

  const people = db.prepare(`
    SELECT p.id, p.first_name, p.last_name, p.job_title, p.location,
           o.code as orientation_code
    FROM people p
    LEFT JOIN orientations o ON o.id = p.primary_orientation_id
  `).all() as any[];
  for (const p of people) {
    const nid = `person-${p.id}`;
    nodeIds.add(nid);
    const label = [p.first_name, p.last_name].filter(Boolean).join(' ');
    nodes.push({
      id: nid, label, type: 'person', orientation: p.orientation_code,
      entityId: p.id, role: p.job_title, location: p.location,
    });
  }

  // ─── Explicit relationship links (strong) ───

  const paLinks = db.prepare(`
    SELECT pa.project_id, pa.actor_id, pa.relationship
    FROM project_actor pa
    JOIN actors a ON a.id = pa.actor_id AND a.canonical_id IS NULL
  `).all() as any[];
  for (const l of paLinks) {
    const src = `actor-${l.actor_id}`;
    const tgt = `project-${l.project_id}`;
    if (nodeIds.has(src) && nodeIds.has(tgt)) {
      links.push({ source: src, target: tgt, type: 'explicit', label: l.relationship });
    }
  }

  const personLinks = db.prepare(`
    SELECT pa.person_id, pa.actor_id, pa.role
    FROM person_actor pa
    JOIN actors a ON a.id = pa.actor_id AND a.canonical_id IS NULL
  `).all() as any[];
  for (const l of personLinks) {
    const src = `person-${l.person_id}`;
    const tgt = `actor-${l.actor_id}`;
    if (nodeIds.has(src) && nodeIds.has(tgt)) {
      links.push({ source: src, target: tgt, type: 'explicit', label: l.role });
    }
  }

  // ─── Tag similarity links (the rich layer) ───
  // Find all entity pairs sharing 3+ tags — this is the primary relationship signal
  const dedupLinks = new Set<string>();
  for (const l of links) {
    const key = [l.source, l.target].sort().join('|');
    dedupLinks.add(key);
  }

  try {
    const tagPairs = db.prepare(`
      SELECT
        et1.entity_type || '-' || et1.entity_id as source,
        et2.entity_type || '-' || et2.entity_id as target,
        COUNT(*) as shared_tags
      FROM entity_tag et1
      JOIN entity_tag et2 ON et1.tag_id = et2.tag_id
        AND (et1.entity_type || '-' || et1.entity_id) < (et2.entity_type || '-' || et2.entity_id)
      GROUP BY source, target
      HAVING COUNT(*) >= 3
      ORDER BY shared_tags DESC
    `).all() as any[];

    for (const pair of tagPairs) {
      const key = [pair.source, pair.target].sort().join('|');
      if (dedupLinks.has(key)) continue;
      if (nodeIds.has(pair.source) && nodeIds.has(pair.target)) {
        dedupLinks.add(key);
        links.push({
          source: pair.source,
          target: pair.target,
          type: 'tag-similarity',
          label: `${pair.shared_tags} shared tags`,
        });
      }
    }
  } catch {
    // tags table may not exist
  }

  // ─── Shared category links (actor↔actor only) ───
  const catPairs = db.prepare(`
    SELECT ac1.actor_id as a1, ac2.actor_id as a2, COUNT(*) as shared
    FROM actor_category ac1
    JOIN actor_category ac2 ON ac1.category_id = ac2.category_id AND ac1.actor_id < ac2.actor_id
    JOIN actors a1a ON a1a.id = ac1.actor_id AND a1a.canonical_id IS NULL
    JOIN actors a2a ON a2a.id = ac2.actor_id AND a2a.canonical_id IS NULL
    GROUP BY ac1.actor_id, ac2.actor_id
    HAVING COUNT(*) >= 1
  `).all() as any[];

  for (const pair of catPairs) {
    const src = `actor-${pair.a1}`;
    const tgt = `actor-${pair.a2}`;
    const key = [src, tgt].sort().join('|');
    if (dedupLinks.has(key)) continue;
    if (nodeIds.has(src) && nodeIds.has(tgt)) {
      dedupLinks.add(key);
      links.push({ source: src, target: tgt, type: 'category', label: `${pair.shared} shared categories` });
    }
  }

  return { nodes, links };
}

// ─── Event types ────────────────────────────────────────

export interface Event {
  id: number;
  name: string;
  type: string | null;
  series: string | null;
  edition: string | null;
  location: string | null;
  date_start: string | null;
  date_end: string | null;
  recurrence: string | null;
  website: string | null;
  description: string | null;
  relevance_note: string | null;
  created_at: string;
  updated_at: string;
  // joined
  actor_count?: number;
}

export interface EventActor {
  event_id: number;
  actor_id: number;
  role: string | null;
  notes: string | null;
  // joined actor fields
  actor_name?: string;
  actor_type?: string;
  orientation_code?: string;
  orientation_name?: string;
  relevance_score?: number;
  actor_location?: string;
}

// ─── Event queries ──────────────────────────────────────

export function getAllEvents(): Event[] {
  const db = getDb();
  return db.prepare(`
    SELECT e.*,
      (SELECT COUNT(*) FROM event_actor ea WHERE ea.event_id = e.id) as actor_count
    FROM events e
    ORDER BY
      CASE
        WHEN e.date_start = 'upcoming' THEN '9999'
        WHEN e.date_start IS NULL THEN '9998'
        ELSE e.date_start
      END DESC
  `).all() as Event[];
}

export function getEvent(id: number): Event | undefined {
  const db = getDb();
  return db.prepare(`
    SELECT e.*,
      (SELECT COUNT(*) FROM event_actor ea WHERE ea.event_id = e.id) as actor_count
    FROM events e WHERE e.id = ?
  `).get(id) as Event | undefined;
}

export function getEventActors(eventId: number): EventActor[] {
  const db = getDb();
  return db.prepare(`
    SELECT ea.*, a.name as actor_name, a.type as actor_type,
      a.relevance_score, a.location as actor_location,
      o.code as orientation_code, o.name as orientation_name
    FROM event_actor ea
    JOIN actors a ON a.id = ea.actor_id
    LEFT JOIN orientations o ON o.id = a.primary_orientation_id
    WHERE ea.event_id = ?
    ORDER BY ea.role, a.name
  `).all(eventId) as EventActor[];
}

export function getActorEvents(actorId: number): (Event & { role: string | null })[] {
  const db = getDb();
  return db.prepare(`
    SELECT e.*, ea.role
    FROM events e
    JOIN event_actor ea ON ea.event_id = e.id
    WHERE ea.actor_id = ?
    ORDER BY e.date_start DESC NULLS LAST
  `).all(actorId) as (Event & { role: string | null })[];
}

export function getRelatedEvents(eventId: number, limit = 6): Event[] {
  const db = getDb();
  // Events sharing actors or same series
  return db.prepare(`
    SELECT DISTINCT e.*,
      (SELECT COUNT(*) FROM event_actor ea2 WHERE ea2.event_id = e.id) as actor_count
    FROM events e
    WHERE e.id != ? AND (
      e.series = (SELECT series FROM events WHERE id = ? AND series IS NOT NULL)
      OR e.id IN (
        SELECT ea2.event_id FROM event_actor ea2
        WHERE ea2.actor_id IN (SELECT ea.actor_id FROM event_actor ea WHERE ea.event_id = ?)
        AND ea2.event_id != ?
      )
    )
    ORDER BY e.date_start DESC NULLS LAST
    LIMIT ?
  `).all(eventId, eventId, eventId, eventId, limit) as Event[];
}

export const EVENT_TYPE_ICONS: Record<string, string> = {
  Conference: '\u25C6',
  Summit: '\u25B2',
  Forum: '\u25CF',
  Workshop: '\u25A0',
  Symposium: '\u25C8',
  Assembly: '\u2B22',
  Festival: '\u2726',
  LARP: '\u2694',
  Convention: '\u25CE',
  Prize: '\u2605',
  Campaign: '\u2691',
  Webinar: '\u25E1',
  Other: '\u25CB',
};

// ─── Stats ───────────────────────────────────────────────

export function getStats() {
  const db = getDb();
  const counts = db.prepare(`
    SELECT
      (SELECT COUNT(*) FROM actors WHERE canonical_id IS NULL) as actors,
      (SELECT COUNT(*) FROM projects) as projects,
      (SELECT COUNT(*) FROM people) as people,
      (SELECT COUNT(*) FROM sources) as sources,
      (SELECT COUNT(*) FROM intel) as intel,
      (SELECT COUNT(*) FROM categories) as categories
  `).get() as Record<string, number>;
  // Tags table may not exist yet
  try {
    const tagCount = db.prepare(`SELECT COUNT(*) as c FROM tags`).get() as { c: number };
    counts.tags = tagCount.c;
  } catch {
    counts.tags = 0;
  }
  // Events table
  try {
    const eventCount = db.prepare(`SELECT COUNT(*) as c FROM events`).get() as { c: number };
    counts.events = eventCount.c;
  } catch {
    counts.events = 0;
  }
  return counts;
}

// ─── Orientation color mapping ───────────────────────────

export const ORIENTATION_COLORS: Record<string, string> = {
  GARDEN: '#6b8f71',
  SPACESHIP: '#6b7f8f',
  TEMPLE: '#8f7b6b',
  ASSEMBLY: '#7b6b8f',
};

export const ORIENTATION_DESCRIPTIONS: Record<string, string> = {
  GARDEN: 'Regenerative ecosystems, biodiversity, indigenous stewardship, and nature-based governance',
  SPACESHIP: 'Earth systems science, digital twins, spatial intelligence, and technological infrastructure',
  TEMPLE: 'Ritual, ceremony, immersive experience, transformative practice, and inner development',
  ASSEMBLY: 'Democratic innovation, deliberative governance, participatory systems, and institutional design',
};

export const FLAG_LABELS: Record<string, string> = {
  network_connected: 'Network Connected',
  close_vision: 'Close to Vision',
  event_opportunity: 'Event Opportunity',
  funding_source: 'Funding Source',
  nordic_based: 'Nordic Based',
};

export const MATURITY_ORDER = ['Idea', 'Early', 'Active', 'Established'];
export const SCALE_ORDER = ['Local', 'National', 'Regional', 'Global'];
