// Client-side read-tracking for The Orbital.
// Loaded by index.astro (and other feed pages). Adds a "Mark read" button to
// each .news-card and persists state via the `reads` table on Supabase.

import { createClient, type Session } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://lathlnothoosbwrvxtel.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhdGhsbm90aG9vc2J3cnZ4dGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjU1OTYsImV4cCI6MjA5Mjk0MTU5Nn0.VZJxCAbOfpiepbvgq9m0xC2wMe0IgFNlUUUC9wbk3Gc';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
});

const readSlugs = new Set<string>();
let session: Session | null = null;

function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const day = 86400000;
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return Math.round(diff / 60_000) + 'm ago';
  if (diff < day) return Math.round(diff / 3_600_000) + 'h ago';
  if (diff < day * 7) return Math.round(diff / day) + 'd ago';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function articleData(card: HTMLElement): {
  slug: string;
  title: string;
  date: string;
  orientations: string[];
  tags: string[];
  source_url: string;
} {
  const slug = card.dataset.slug || '';
  const title = card.dataset.title || '';
  const date = card.dataset.date || '';
  const orientations = (card.dataset.orientations || '').split(',').filter(Boolean);
  const tags = (card.dataset.tags || '').split(',').filter(Boolean);
  const source_url = card.dataset.sourceUrl || '';
  return { slug, title, date, orientations, tags, source_url };
}

function applyState(card: HTMLElement) {
  const slug = card.dataset.slug;
  if (!slug) return;
  const isRead = readSlugs.has(slug);
  card.classList.toggle('is-read', isRead);
  const btn = card.querySelector<HTMLButtonElement>('.mark-read-btn');
  if (btn) {
    btn.dataset.read = isRead ? '1' : '0';
    btn.textContent = isRead ? '✓ Read' : 'Mark as read';
    btn.title = isRead ? 'Click to unmark as read' : 'Mark this article as read';
  }
}

async function toggleRead(card: HTMLElement) {
  if (!session) return;
  const slug = card.dataset.slug;
  if (!slug) return;
  const wasRead = readSlugs.has(slug);

  // Optimistic UI
  if (wasRead) readSlugs.delete(slug);
  else readSlugs.add(slug);
  applyState(card);

  try {
    if (wasRead) {
      await supabase.from('reads')
        .delete()
        .eq('user_id', session.user.id)
        .eq('article_slug', slug);
    } else {
      const a = articleData(card);
      await supabase.from('reads').upsert(
        {
          user_id: session.user.id,
          article_slug: a.slug,
          article_title: a.title,
          article_date: a.date || null,
          orientations: a.orientations,
          tags: a.tags,
          source_url: a.source_url,
          read_at: new Date().toISOString(),
        },
        { onConflict: 'user_id,article_slug' },
      );
    }
    // Refresh nav read counter
    if ((window as any).__refreshAuthNav) (window as any).__refreshAuthNav();
  } catch (e) {
    console.error('[reads] toggle failed:', e);
    // Roll back optimistic update
    if (wasRead) readSlugs.add(slug);
    else readSlugs.delete(slug);
    applyState(card);
  }
}

function injectButtons() {
  const cards = document.querySelectorAll<HTMLElement>('.news-card[data-slug]');
  cards.forEach((card) => {
    if (card.querySelector('.mark-read-btn')) return; // already injected

    const body = card.querySelector('.card-body');
    if (!body) return;

    const btn = document.createElement('button');
    btn.className = 'mark-read-btn';
    btn.type = 'button';
    btn.textContent = 'Mark as read';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleRead(card);
    });

    // Add a "Read" badge container too (visible only when read)
    const badge = document.createElement('span');
    badge.className = 'read-badge';
    badge.textContent = '✓ Read';

    // Wrap in a row so they sit together
    const row = document.createElement('div');
    row.className = 'read-row';
    row.appendChild(btn);
    row.appendChild(badge);
    body.appendChild(row);

    applyState(card);
  });
}

function hideButtons() {
  document.querySelectorAll<HTMLElement>('.read-row').forEach((r) => r.remove());
  document.querySelectorAll<HTMLElement>('.news-card.is-read').forEach((c) => {
    c.classList.remove('is-read');
  });
}

async function loadReads() {
  if (!session) return;
  readSlugs.clear();
  const { data, error } = await supabase
    .from('reads')
    .select('article_slug')
    .eq('user_id', session.user.id);
  if (error) {
    console.error('[reads] load failed:', error.message);
    return;
  }
  (data ?? []).forEach((r: any) => readSlugs.add(r.article_slug));
  document.querySelectorAll<HTMLElement>('.news-card[data-slug]').forEach(applyState);
}

async function init() {
  const { data } = await supabase.auth.getSession();
  session = data.session;

  if (session) {
    injectButtons();
    await loadReads();
  } else {
    hideButtons();
  }

  supabase.auth.onAuthStateChange(async (_event, newSession) => {
    session = newSession;
    if (session) {
      injectButtons();
      await loadReads();
    } else {
      hideButtons();
    }
  });
}

init();
