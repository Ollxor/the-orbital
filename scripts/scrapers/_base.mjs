/**
 * _base.mjs — shared utilities for all event scrapers
 */

// ── Slug ──────────────────────────────────────────────────────────────────────
export function slugify(name, date = '') {
  const year = date ? String(new Date(date).getFullYear()) : '';
  const base = name
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')   // strip diacritics
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/-$/, '')
    .slice(0, 60);
  return year ? `${base}-${year}` : base;
}

// ── Strip HTML ────────────────────────────────────────────────────────────────
export function stripHtml(html = '') {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&#039;/g, "'")
    .replace(/\s{2,}/g, ' ')
    .trim();
}

// ── Orientation inference ─────────────────────────────────────────────────────
const KW = {
  GARDEN: [
    'nature','ecology','ecological','biodiversity','regenerative','regeneration',
    'agroecology','soil','food sovereignty','land rights','forest','ocean','rewilding',
    'indigenous','traditional knowledge','species','ecosystem','conservation',
    'rights of nature','environmental','watershed','carbon','circular economy',
    'permaculture','biosphere','oceans','climate adaptation','bioregion',
  ],
  SPACESHIP: [
    'technology','digital','data','artificial intelligence',' ai ','satellite',
    'monitoring','blockchain','platform','tech ','modelling','simulation',
    'dashboard','open source','civic tech','algorithm','machine learning',
    'geospatial','remote sensing','sensor','iot','earth observation','twin',
  ],
  MYSTERIES: [
    'larp','role-play','roleplay','game','play ','ritual','festival','theatre',
    'theater','experience','immersive','arts','art ','creative','storytelling',
    'narrative','ceremony','ceremony','imagination','speculative','futures',
    'scenario','performance','installation','embodied','participatory art',
  ],
  ASSEMBLY: [
    'assembly','deliberation','deliberative','democracy','governance','sortition',
    'commons','participation','participatory','citizens\'','citizen assembly',
    'parliament','policy','decision-making','vote','voting','consensus',
    'cooperation','multilateral','treaty','convention','summit','negotiation',
    'civil society','global governance','collective decision','co-creation',
  ],
};

export function inferOrientations(title = '', description = '') {
  const text = (title + ' ' + description).toLowerCase();
  const scores = {};
  for (const [o, kws] of Object.entries(KW)) {
    scores[o] = kws.reduce((n, kw) => n + (text.includes(kw) ? 1 : 0), 0);
  }
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const top = sorted.filter(([, s]) => s > 0);
  if (top.length === 0) return [];
  // Include top scorer; include second if within 2 points and at least 1
  const result = [top[0][0]];
  if (top.length > 1 && top[1][1] >= 1 && top[0][1] - top[1][1] <= 2) {
    result.push(top[1][0]);
  }
  return result;
}

// ── Geo inference (rough) ─────────────────────────────────────────────────────
const GEO_HINTS = [
  // [pattern, continent, subregion]
  [/\b(africa|nigeria|kenya|ghana|ethiopia|senegal|tanzania|uganda|cameroon|south africa|cairo|nairobi|accra|lagos|dar es salaam)\b/i, 'africa', ''],
  [/\b(europe|eu |european union|germany|france|uk |united kingdom|spain|sweden|norway|denmark|finland|netherlands|belgium|switzerland|poland|italy|austria|portugal)\b/i, 'europe', ''],
  [/\b(nordic|scandinavia|stockholm|oslo|copenhagen|helsinki)\b/i, 'europe', 'northern-europe'],
  [/\b(usa|united states|new york|washington|california|chicago|san francisco|los angeles|boston)\b/i, 'north-america', 'northern-america'],
  [/\b(canada|toronto|vancouver|montreal|ottawa)\b/i, 'north-america', 'northern-america'],
  [/\b(latin america|brazil|mexico|colombia|argentina|chile|peru|ecuador|bolivia|venezuela|rio|bogota|lima|buenos aires|sao paulo|mexico city)\b/i, 'latin-america', ''],
  [/\b(asia|india|china|japan|south korea|indonesia|philippines|vietnam|thailand|bangladesh|pakistan|nepal|myanmar|cambodia|delhi|beijing|tokyo|seoul)\b/i, 'asia', ''],
  [/\b(middle east|saudi arabia|uae|dubai|jordan|lebanon|turkey|iran|israel)\b/i, 'asia', 'western-asia'],
  [/\b(oceania|australia|new zealand|pacific|papua|fiji|samoa|tonga|vanuatu)\b/i, 'oceania', ''],
  [/\bonline\b/i, 'transnational', ''],
  [/\bvirtual\b/i, 'transnational', ''],
  [/\bglobal\b/i, 'transnational', ''],
];

export function inferGeo(location = '', description = '') {
  const text = (location + ' ' + description).toLowerCase();
  for (const [re, continent, subregion] of GEO_HINTS) {
    if (re.test(text)) return { continent, subregion };
  }
  return { continent: '', subregion: '' };
}

// ── Format inference ──────────────────────────────────────────────────────────
export function inferFormat(location = '', description = '') {
  const text = (location + ' ' + description).toLowerCase();
  if (/\b(online|virtual|webinar|zoom|livestream|remote)\b/.test(text)) {
    if (/\b(in.person|hybrid|onsite|on.site)\b/.test(text)) return 'hybrid';
    return 'online';
  }
  if (/\b(in.person|onsite|on.site)\b/.test(text)) return 'in-person';
  return '';
}

// ── Type normalisation ────────────────────────────────────────────────────────
const TYPE_MAP = [
  [/\bconference\b/i, 'Conference'],
  [/\bsummit\b/i, 'Summit'],
  [/\bwebinar\b/i, 'Webinar'],
  [/\bforum\b/i, 'Forum'],
  [/\bworkshop\b/i, 'Workshop'],
  [/\bsymposium\b/i, 'Symposium'],
  [/\bassembly\b/i, 'Assembly'],
  [/\bfestival\b/i, 'Festival'],
  [/\blarp\b/i, 'LARP'],
  [/\bcampign\b/i, 'Campaign'],
  [/\bconvention\b/i, 'Convention'],
];
export function inferType(name = '', description = '') {
  const text = name + ' ' + description;
  for (const [re, t] of TYPE_MAP) {
    if (re.test(text)) return t;
  }
  return 'Conference';
}

// ── Date normalisation ────────────────────────────────────────────────────────
export function toIsoDate(raw) {
  if (!raw) return '';
  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  try {
    const d = new Date(raw);
    if (isNaN(d.getTime())) return '';
    return d.toISOString().slice(0, 10);
  } catch { return ''; }
}

// ── Blank event scaffold ──────────────────────────────────────────────────────
export function blankEvent() {
  return {
    slug: '',
    name: '',
    description: '',
    date_start: '',
    date_end: '',
    location: '',
    website: '',
    image: '',
    imageAlt: '',
    type: '',
    format: '',
    cost: '',
    languages: [],
    orientations: [],
    tags: [],
    actors: [],
    continent: '',
    subregion: '',
    country: [],
    scale: '',
    bioregion: [],
    peoples: [],
    relevance_note: '',
    series: '',
    edition: '',
    recurrence: '',
    linked_projects: [],
  };
}

// ── Deduplication ─────────────────────────────────────────────────────────────
function normaliseTitle(t) {
  return t.toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function dedup(candidates, existing) {
  const existingSlugs = new Set(existing.map(e => e.slug));
  const existingTitles = new Map(
    existing.map(e => [normaliseTitle(e.name), e.slug])
  );

  return candidates.filter(c => {
    if (existingSlugs.has(c.slug)) return false;
    const normTitle = normaliseTitle(c.name);
    if (existingTitles.has(normTitle)) return false;
    return true;
  });
}

// ── Fetch with timeout + user-agent ──────────────────────────────────────────
export async function fetchJson(url, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'The Orbital events scraper (theorbital.net)' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchText(url, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'The Orbital events scraper (theorbital.net)' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return await res.text();
  } finally {
    clearTimeout(timer);
  }
}
