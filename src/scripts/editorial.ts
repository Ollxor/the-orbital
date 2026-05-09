// Admin-only editorial tier overrides.
// When the user is admin, every news card gets a small "promote/demote"
// pill. Clicking it writes to editorial_overrides table.
//
// Card requirements: data-slug + data-tier on the .news-card element.

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://lathlnothoosbwrvxtel.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhdGhsbm90aG9vc2J3cnZ4dGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjU1OTYsImV4cCI6MjA5Mjk0MTU5Nn0.VZJxCAbOfpiepbvgq9m0xC2wMe0IgFNlUUUC9wbk3Gc';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
});

// Map: slug → effective tier (after applying overrides)
const overrideMap = new Map<string, 'main' | 'stream'>();

async function loadOverrides() {
  const { data, error } = await supabase
    .from('editorial_overrides')
    .select('slug, tier');
  if (error) {
    console.warn('[editorial] load overrides failed:', error.message);
    return;
  }
  overrideMap.clear();
  (data ?? []).forEach((row: any) => {
    if (row.tier === 'main' || row.tier === 'stream') {
      overrideMap.set(row.slug, row.tier);
    }
  });
}

function applyOverridesToCards() {
  document.querySelectorAll<HTMLElement>('.news-card[data-slug]').forEach(card => {
    const slug = card.dataset.slug!;
    const original = card.dataset.tier ?? 'main';
    const override = overrideMap.get(slug);
    const effective = override ?? original;
    card.dataset.effectiveTier = effective;

    // On the homepage: hide stream-tier (effective) cards
    const onHome = window.location.pathname === '/';
    if (onHome && effective === 'stream') {
      card.classList.add('editorial-hidden');
    } else {
      card.classList.remove('editorial-hidden');
    }

    // Update any tier badge
    const badge = card.querySelector<HTMLElement>('.tier-chip.tier-main, .tier-chip.tier-stream');
    if (badge) {
      badge.textContent = effective;
      badge.className = `tier-chip tier-${effective}`;
    }
  });
}

function injectAdminControls() {
  document.querySelectorAll<HTMLElement>('.news-card[data-slug]').forEach(card => {
    if (card.querySelector('.editorial-pill')) return; // already injected

    const slug = card.dataset.slug!;
    const effective = card.dataset.effectiveTier ?? card.dataset.tier ?? 'main';
    const targetTier: 'main' | 'stream' = effective === 'main' ? 'stream' : 'main';
    const verb = effective === 'main' ? 'demote → stream' : 'promote → main';

    const pill = document.createElement('button');
    pill.type = 'button';
    pill.className = 'editorial-pill';
    pill.textContent = verb;
    pill.dataset.targetTier = targetTier;
    pill.title = `Editorial override: set ${slug} to ${targetTier}`;
    pill.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      pill.disabled = true;
      pill.textContent = 'saving…';

      const { error } = await supabase
        .from('editorial_overrides')
        .upsert(
          { slug, tier: targetTier, set_by: (await supabase.auth.getSession()).data.session?.user.id },
          { onConflict: 'slug' },
        );

      if (error) {
        console.error('[editorial] override failed:', error);
        pill.textContent = 'error';
        setTimeout(() => { pill.disabled = false; }, 2000);
        return;
      }

      overrideMap.set(slug, targetTier);
      applyOverridesToCards();
      // Re-inject this card's pill with new state
      pill.remove();
      injectAdminControls();
    });

    // Find a good attachment point — inside the read-row if present, else at the end of card-body
    const readRow = card.querySelector('.read-row');
    if (readRow) {
      readRow.appendChild(pill);
    } else {
      const body = card.querySelector('.card-body') ?? card;
      body.appendChild(pill);
    }
  });
}

async function init() {
  // Wait for admin state to be determined
  function start() {
    if ((window as any).__isAdmin) {
      loadOverrides().then(() => {
        applyOverridesToCards();
        injectAdminControls();
      });
    } else {
      // Even non-admins need overrides applied (so promoted/demoted entries
      // show up consistently for everyone). But anon-key SELECT requires
      // signed-in, so we only do this for signed-in users.
      const session = (window as any).__supabase?.auth?.getSession?.();
      if (session) {
        loadOverrides().then(applyOverridesToCards);
      }
    }
  }

  // If admin state is already set (event fired before our import loaded), use it.
  if ((window as any).__isAdmin !== undefined) {
    start();
  }
  // Listen for admin-state events from Base.astro
  document.addEventListener('admin-state', () => start());
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
