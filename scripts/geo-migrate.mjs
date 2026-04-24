/**
 * Geographic taxonomy migration — adds continent, subregion, country[],
 * bioregion[], peoples[], languages[] to every actor in actors.json.
 * Existing fields (location, scale, etc.) are preserved unchanged.
 */

import { readFileSync, writeFileSync } from 'fs';

const actors = JSON.parse(readFileSync('src/data/actors.json', 'utf8'));

const MAPPINGS = {
  'Amsterdam, Netherlands / Global':               { continent:'europe',        subregion:'western-europe',             country:['NL'],               bioregion:[] },
  'Australia':                                     { continent:'oceania',        subregion:'australia-and-new-zealand',  country:['AU'],               bioregion:[] },
  'Brazil / Global':                               { continent:'americas',       subregion:'south-america',              country:['BR'],               bioregion:[] },
  'Canada':                                        { continent:'americas',       subregion:'northern-america',           country:['CA'],               bioregion:[] },
  'Copenhagen, Denmark':                           { continent:'europe',         subregion:'northern-europe',            country:['DK'],               bioregion:['Nordic'] },
  'DK / UG / MA / PK':                            { continent:'transnational',  subregion:null,                         country:['DK','UG','MA','PK'], bioregion:[] },
  'Denmark / Pan-Nordic':                          { continent:'europe',         subregion:'northern-europe',            country:['DK'],               bioregion:['Nordic'] },
  'EU':                                            { continent:'europe',         subregion:null,                         country:[],                   bioregion:[] },
  'Estonia':                                       { continent:'europe',         subregion:'northern-europe',            country:['EE'],               bioregion:['Nordic'] },
  'Estonia / Sweden':                              { continent:'europe',         subregion:'northern-europe',            country:['EE','SE'],          bioregion:['Nordic'] },
  'Europe':                                        { continent:'europe',         subregion:null,                         country:[],                   bioregion:[] },
  'France':                                        { continent:'europe',         subregion:'western-europe',             country:['FR'],               bioregion:[] },
  'Germany':                                       { continent:'europe',         subregion:'western-europe',             country:['DE'],               bioregion:[] },
  'Germany / Global':                              { continent:'europe',         subregion:'western-europe',             country:['DE'],               bioregion:[] },
  'Global':                                        { continent:'transnational',  subregion:null,                         country:[],                   bioregion:[] },
  'Global (coordination: India)':                  { continent:'transnational',  subregion:null,                         country:['IN'],               bioregion:[] },
  'Global / Amsterdam':                            { continent:'transnational',  subregion:null,                         country:['NL'],               bioregion:[] },
  'Helsinki, Finland':                             { continent:'europe',         subregion:'northern-europe',            country:['FI'],               bioregion:['Nordic'] },
  'India / Global':                                { continent:'asia',           subregion:'southern-asia',              country:['IN'],               bioregion:[] },
  'Italy':                                         { continent:'europe',         subregion:'southern-europe',            country:['IT'],               bioregion:[] },
  'Karasjok, Norway / Sapmi (Regional)':           { continent:'europe',         subregion:'northern-europe',            country:['NO'],               bioregion:['Nordic','Sapmi'], peoples:['Sami'] },
  'Norway':                                        { continent:'europe',         subregion:'northern-europe',            country:['NO'],               bioregion:['Nordic'] },
  'Oakland, USA':                                  { continent:'americas',       subregion:'northern-america',           country:['US'],               bioregion:[] },
  'Pan-Nordic':                                    { continent:'europe',         subregion:'northern-europe',            country:[],                   bioregion:['Nordic'] },
  'Pan-Nordic (Finland, Norway, Sweden, Denmark)': { continent:'europe',         subregion:'northern-europe',            country:['FI','NO','SE','DK'], bioregion:['Nordic'] },
  'Stockholm, Sweden':                             { continent:'europe',         subregion:'northern-europe',            country:['SE'],               bioregion:['Nordic'] },
  'Sweden':                                        { continent:'europe',         subregion:'northern-europe',            country:['SE'],               bioregion:['Nordic'] },
  'Sweden (Gotland)':                              { continent:'europe',         subregion:'northern-europe',            country:['SE'],               bioregion:['Nordic'] },
  'Sweden / Zambia':                               { continent:'europe',         subregion:'northern-europe',            country:['SE','ZM'],          bioregion:['Nordic'] },
  'Taiwan':                                        { continent:'asia',           subregion:'eastern-asia',               country:['TW'],               bioregion:[] },
  'Totnes, UK / Global':                           { continent:'europe',         subregion:'northern-europe',            country:['GB'],               bioregion:[] },
  'UK':                                            { continent:'europe',         subregion:'northern-europe',            country:['GB'],               bioregion:[] },
  'UK / Africa / South America':                   { continent:'transnational',  subregion:null,                         country:['GB'],               bioregion:[] },
  'UK / EU':                                       { continent:'europe',         subregion:'northern-europe',            country:['GB'],               bioregion:[] },
  'UK / Global':                                   { continent:'europe',         subregion:'northern-europe',            country:['GB'],               bioregion:[] },
  'UK / India':                                    { continent:'europe',         subregion:'northern-europe',            country:['GB','IN'],          bioregion:[] },
  'USA':                                           { continent:'americas',       subregion:'northern-america',           country:['US'],               bioregion:[] },
  'USA / Global':                                  { continent:'americas',       subregion:'northern-america',           country:['US'],               bioregion:[] },
  'Umea, Sweden / Swedish Lapland':                { continent:'europe',         subregion:'northern-europe',            country:['SE'],               bioregion:['Nordic','Sapmi'] },
  'Uppsala, Sweden (Secretariat) / Baltic Region': { continent:'europe',         subregion:'northern-europe',            country:['SE'],               bioregion:['Nordic','Baltic'] },
  'Wales / UK':                                    { continent:'europe',         subregion:'northern-europe',            country:['GB'],               bioregion:[] },
};

let migrated = 0;
let failed = 0;

const updated = actors.map(actor => {
  const m = MAPPINGS[actor.location];
  if (!m) {
    console.error('  NO MAPPING for:', actor.slug, '|', actor.location);
    failed++;
    return actor;
  }
  migrated++;
  return {
    ...actor,
    continent:  m.continent,
    subregion:  m.subregion ?? null,
    country:    m.country,
    bioregion:  m.bioregion,
    peoples:    m.peoples ?? [],
    languages:  [],
  };
});

if (failed > 0) {
  console.error(`\nABORTED — ${failed} actors had no mapping. Fix before writing.`);
  process.exit(1);
}

writeFileSync('src/data/actors.json', JSON.stringify(updated, null, 2) + '\n', 'utf8');

console.log(`Migration complete: ${migrated} actors updated.`);

// Verify no mojibake
const raw = readFileSync('src/data/actors.json', 'utf8');
const mojibake = (raw.match(/â€|Ã¤|Ã¶|Ã¼|Ã©/g) || []).length;
console.log(`Mojibake check: ${mojibake === 0 ? '0 — clean' : mojibake + ' INSTANCES FOUND!'}`);

// Summary
const continentCounts = {};
updated.forEach(a => {
  continentCounts[a.continent] = (continentCounts[a.continent]||0)+1;
});
console.log('\nContinent distribution:');
Object.entries(continentCounts).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(' ', v, k));
