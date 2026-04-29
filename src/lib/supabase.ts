import { createServerClient, parseCookieHeader, serializeCookieHeader } from '@supabase/ssr';
import { createClient } from '@supabase/supabase-js';
import type { AstroCookies } from 'astro';

// ── Public constants (safe to use in browser bundles) ───────────────────────

export const SUPABASE_URL = import.meta.env.PUBLIC_SUPABASE_URL;
export const SUPABASE_ANON_KEY = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;

// ── Server client — reads/writes cookies, used in SSR pages + middleware ────

export function createSupabaseServerClient(
  request: Request,
  cookies: AstroCookies,
) {
  return createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return parseCookieHeader(request.headers.get('Cookie') ?? '');
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          cookies.set(name, value, options);
        });
      },
    },
  });
}

// ── Admin client — service role, bypasses RLS. NEVER import in browser ──────

export function createSupabaseAdminClient() {
  return createClient(
    SUPABASE_URL,
    import.meta.env.SUPABASE_SERVICE_ROLE_KEY,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );
}
