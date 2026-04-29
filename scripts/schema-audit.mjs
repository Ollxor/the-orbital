import { readFileSync } from 'fs';

const p = JSON.parse(readFileSync('src/data/projects.json', 'utf8'));
const e = JSON.parse(readFileSync('src/data/events.json', 'utf8'));

// ── PROJECTS ──────────────────────────────────────────────────────────────
console.log('=== PROJECTS (' + p.length + ') ===');
const pFields = new Set();
p.forEach(x => Object.keys(x).forEach(k => pFields.add(k)));
console.log('All fields:', [...pFields].sort().join(', '));

const withActors = p.filter(x => x.actors?.length > 0).length;
console.log('Have actors[]:', withActors, '/', p.length);

const statuses = {};
p.forEach(x => { const s = x.status||'(none)'; statuses[s] = (statuses[s]||0)+1; });
console.log('Status values:', statuses);

const ptypes = {};
p.forEach(x => { const t = x.type||x.project_type||'(none)'; ptypes[t] = (ptypes[t]||0)+1; });
console.log('Type values:', ptypes);

const hasGeo = p.filter(x => x.continent).length;
console.log('Have continent:', hasGeo);

console.log('\nFirst project sample:');
console.log(JSON.stringify(p[0], null, 2));

// ── EVENTS ────────────────────────────────────────────────────────────────
console.log('\n=== EVENTS (' + e.length + ') ===');
const eFields = new Set();
e.forEach(x => Object.keys(x).forEach(k => eFields.add(k)));
console.log('All fields:', [...eFields].sort().join(', '));

const eWithActors = e.filter(x => x.actors?.length > 0).length;
console.log('Have actors[]:', eWithActors, '/', e.length);

const dateFields = [...eFields].filter(f => f.toLowerCase().includes('date'));
console.log('Date-related fields:', dateFields);

const formats = {};
e.forEach(x => { const f = x.format||'(none)'; formats[f] = (formats[f]||0)+1; });
console.log('Format values:', formats);

const etypes = {};
e.forEach(x => { const t = x.type||x.event_type||'(none)'; etypes[t] = (etypes[t]||0)+1; });
console.log('Type values:', etypes);

const eHasGeo = e.filter(x => x.continent).length;
console.log('Have continent:', eHasGeo);

console.log('\nFirst event sample:');
console.log(JSON.stringify(e[0], null, 2));
