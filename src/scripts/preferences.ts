// Per-user feed preferences applied client-side.
// Runs on every page that includes news cards. If the user is signed in
// and has saved preferences, hide cards that don't match.
//
// Cards are expected to have:
//   data-orientations="GARDEN,ASSEMBLY"  (CSV)
//   class="news-card"
//   optional: data-tier="main" | "stream"
//   optional: data-kind="video" | "article"

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://lathlnothoosbwrvxtel.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhdGhsbm90aG9vc2J3cnZ4dGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjU1OTYsImV4cCI6MjA5Mjk0MTU5Nn0.VZJxCAbOfpiepbvgq9m0xC2wMe0IgFNlUUUC9wbk3Gc';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
});

interface Prefs {
  orientations_hide: string[];
  tags_hide: string[];
  sources_hide: string[];
  show_articles: boolean;
  show_videos: boolean;
  show_stream: boolean;
}

const DEFAULT_PREFS: Prefs = {
  orientations_hide: [],
  tags_hide: [],
  sources_hide: [],
  show_articles: true,
  show_videos: true,
  show_stream: false,
};

function applyPrefs(prefs: Prefs) {
  const cards = document.querySelectorAll<HTMLElement>('.news-card[data-slug]');
  cards.forEach(card => {
    const orients = (card.dataset.orientations ?? '').split(',').filter(Boolean);
    const tags = (card.dataset.tags ?? '').split(',').filter(Boolean);
    const tier = card.dataset.tier ?? 'main';
    const kind = card.dataset.kind ?? 'article';

    let hide = false;

    // Hide if all of the entry's orientations are in the hide list
    if (prefs.orientations_hide.length > 0 && orients.length > 0) {
      if (orients.every(o => prefs.orientations_hide.includes(o))) hide = true;
    }
    // Hide if any of the entry's tags is in the hide list
    if (!hide && prefs.tags_hide.length > 0) {
      if (tags.some(t => prefs.tags_hide.includes(t))) hide = true;
    }
    // Hide by content type
    if (!hide && kind === 'video' && !prefs.show_videos) hide = true;
    if (!hide && kind !== 'video' && !prefs.show_articles) hide = true;
    // Stream tier on homepage only if user opted in.
    // The /stream page itself ignores this — user is explicitly there to see everything.
    const onStreamPage = window.location.pathname.startsWith('/stream');
    if (!hide && !onStreamPage && tier === 'stream' && !prefs.show_stream) hide = true;

    card.classList.toggle('pref-hidden', hide);
  });
}

async function loadAndApply() {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return; // no prefs to apply

  const { data: row } = await supabase
    .from('user_preferences')
    .select('orientations_hide, tags_hide, sources_hide, show_articles, show_videos, show_stream')
    .eq('user_id', session.user.id)
    .maybeSingle();

  const prefs: Prefs = { ...DEFAULT_PREFS, ...(row ?? {}) };
  applyPrefs(prefs);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadAndApply);
} else {
  loadAndApply();
}
