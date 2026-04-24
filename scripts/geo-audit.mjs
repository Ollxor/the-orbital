import { readFileSync } from 'fs';

const actors = JSON.parse(readFileSync('src/data/actors.json', 'utf8'));

const mappings = {
  'Amsterdam, Netherlands / Global':               { continent:'europe',        subregion:'western-europe',             country:['NL'],           bioregion:[] },
  'Australia':                                     { continent:'oceania',        subregion:'australia-and-new-zealand',  country:['AU'],           bioregion:[] },
  'Brazil / Global':                               { continent:'americas',       subregion:'south-america',              country:['BR'],           bioregion:[] },
  'Canada':                                        { continent:'americas',       subregion:'northern-america',           country:['CA'],           bioregion:[] },
  'Copenhagen, Denmark':                           { continent:'europe',         subregion:'northern-europe',            country:['DK'],           bioregion:['Nordic'] },
  'DK / UG / MA / PK':                            { continent:'transnational',  subregion:null,                         country:['DK','UG','MA','PK'], bioregion:[] },
  'Denmark / Pan-Nordic':                          { continent:'europe',         subregion:'northern-europe',            country:['DK'],           bioregion:['Nordic'] },
  'EU':                                            { continent:'europe',         subregion:null,                         country:[],               bioregion:[] },
  'Estonia':                                       { continent:'europe',         subregion:'northern-europe',            country:['EE'],           bioregion:['Nordic'] },
  'Estonia / Sweden':                              { continent:'europe',         subregion:'northern-europe',            country:['EE','SE'],      bioregion:['Nordic'] },
  'Europe':                                        { continent:'europe',         subregion:null,                         country:[],               bioregion:[] },
  'France':                                        { continent:'europe',         subregion:'western-europe',             country:['FR'],           bioregion:[] },
  'Germany':                                       { continent:'europe',         subregion:'western-europe',             country:['DE'],           bioregion:[] },
  'Germany / Global':                              { continent:'europe',         subregion:'western-europe',             country:['DE'],           bioregion:[] },
  'Global':                                        { continent:'transnational',  subregion:null,                         country:[],               bioregion:[] },
  'Global (coordination: India)':                  { continent:'transnational',  subregion:null,                         country:['IN'],           bioregion:[] },
  'Global / Amsterdam':                            { continent:'transnational',  subregion:null,                         country:['NL'],           bioregion:[] },
  'Helsinki, Finland':                             { continent:'europe',         subregion:'northern-europe',            country:['FI'],           bioregion:['Nordic'] },
  'India / Global':                                { continent:'asia',           subregion:'southern-asia',              country:['IN'],           bioregion:[] },
  'Italy':                                         { continent:'europe',         subregion:'southern-europe',            country:['IT'],           bioregion:[] },
  'Karasjok, Norway / Sapmi (Regional)':           { continent:'europe',         subregion:'northern-europe',            country:['NO'],           bioregion:['Nordic','Sapmi'], peoples:['Sami'] },
  'Norway':                                        { continent:'europe',         subregion:'northern-europe',            country:['NO'],           bioregion:['Nordic'] },
  'Oakland, USA':                                  { continent:'americas',       subregion:'northern-america',           country:['US'],           bioregion:[] },
  'Pan-Nordic':                                    { continent:'europe',         subregion:'northern-europe',            country:[],               bioregion:['Nordic'] },
  'Pan-Nordic (Finland, Norway, Sweden, Denmark)': { continent:'europe',         subregion:'northern-europe',            country:['FI','NO','SE','DK'], bioregion:['Nordic'] },
  'Stockholm, Sweden':                             { continent:'europe',         subregion:'northern-europe',            country:['SE'],           bioregion:['Nordic'] },
  'Sweden':                                        { continent:'europe',         subregion:'northern-europe',            country:['SE'],           bioregion:['Nordic'] },
  'Sweden (Gotland)':                              { continent:'europe',         subregion:'northern-europe',            country:['SE'],           bioregion:['Nordic'] },
  'Sweden / Zambia':                               { continent:'europe',         subregion:'northern-europe',            country:['SE','ZM'],      bioregion:['Nordic'] },
  'Taiwan':                                        { continent:'asia',           subregion:'eastern-asia',               country:['TW'],           bioregion:[] },
  'Totnes, UK / Global':                           { continent:'europe',         subregion:'northern-europe',            country:['GB'],           bioregion:[] },
  'UK':                                            { continent:'europe',         subregion:'northern-europe',            country:['GB'],           bioregion:[] },
  'UK / Africa / South America':                   { continent:'transnational',  subregion:null,                         country:['GB'],           bioregion:[] },
  'UK / EU':                                       { continent:'europe',         subregion:'northern-europe',            country:['GB'],           bioregion:[] },
  'UK / Global':                                   { continent:'europe',         subregion:'northern-europe',            country:['GB'],           bioregion:[] },
  'UK / India':                                    { continent:'europe',         subregion:'northern-europe',            country:['GB','IN'],      bioregion:[] },
  'USA':                                           { continent:'americas',       subregion:'northern-america',           country:['US'],           bioregion:[] },
  'USA / Global':                                  { continent:'americas',       subregion:'northern-america',           country:['US'],           bioregion:[] },
  'Umea, Sweden / Swedish Lapland':                { continent:'europe',         subregion:'northern-europe',            country:['SE'],           bioregion:['Nordic','Sapmi'] },
  'Uppsala, Sweden (Secretariat) / Baltic Region': { continent:'europe',         subregion:'northern-europe',            country:['SE'],           bioregion:['Nordic','Baltic'] },
  'Wales / UK':                                    { continent:'europe',         subregion:'northern-europe',            country:['GB'],           bioregion:[] },
};

// Coverage check
const unmapped = actors.filter(a => !mappings[a.location]);
console.log('=== COVERAGE ===');
console.log('Distinct location strings:', new Set(actors.map(a => a.location)).size);
console.log('Location strings in mapping table:', Object.keys(mappings).length);
console.log('Total actors:', actors.length);
console.log('Unmapped actors:', unmapped.length);
if (unmapped.length) {
  console.log('UNMAPPED:');
  unmapped.forEach(a => console.log(' ', a.slug, '|', a.location));
}

// Continent distribution after migration
const continentCounts = {};
actors.forEach(a => {
  const c = (mappings[a.location] || {}).continent || '(unmapped)';
  continentCounts[c] = (continentCounts[c]||0)+1;
});
console.log('\n=== CONTINENT DISTRIBUTION AFTER MIGRATION ===');
Object.entries(continentCounts).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(' ', v, k));

// Scale distribution (already in data)
const scaleCounts = {};
actors.forEach(a => {
  scaleCounts[a.scale||'(none)'] = (scaleCounts[a.scale||'(none)']||0)+1;
});
console.log('\n=== SCALE (already in actors.json) ===');
Object.entries(scaleCounts).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(' ', v, k));

// Show notable editorial calls
console.log('\n=== NOTABLE EDITORIAL DECISIONS (need approval) ===');
const notable = [
  '"Global" location strings (35 actors) → continent:transnational  (scale field already set)',
  '"USA/Global", "UK/Global", "Germany/Global" → home continent kept, scale already=Global',
  '"UK" → subregion:northern-europe  (UN M49 places UK in Northern Europe)',
  '"DK/UG/MA/PK" (Planetary Guardians/SpiralWeb) → transnational (spans Africa+Europe+Asia)',
  '"UK/Africa/South America" → transnational',
  '"Sweden/Zambia" → continent:europe, country:[SE,ZM] — primary base is Sweden',
  '"India/Global" → continent:asia (primary base is India)',
  'Karasjok/Sapmi → peoples:["Sami"], bioregion:["Nordic","Sapmi"]',
  'Uppsala/Baltic → bioregion:["Nordic","Baltic"]',
  'Umea/Swedish Lapland → bioregion:["Nordic","Sapmi"]',
];
notable.forEach(n => console.log(' -', n));

console.log('\n=== GAPS (actors with no Africa/Oceania/Asia representation) ===');
console.log('  Africa: 0 actors');
console.log('  Oceania: 1 actor (Australia)');
console.log('  Asia: 2 actors (India/Global, Taiwan)');
console.log('  → This will be visible in the filter bar with zero-counts, per spec.');
