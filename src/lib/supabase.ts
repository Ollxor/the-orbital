// Browser Supabase client factory.
// All auth in The Orbital runs client-side (static Cloudflare Pages deployment).
// Uses localStorage for session storage (default behaviour of @supabase/supabase-js).

import { createClient } from '@supabase/supabase-js';

export const SUPABASE_URL = 'https://lathlnothoosbwrvxtel.supabase.co';
export const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhdGhsbm90aG9vc2J3cnZ4dGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzczNjU1OTYsImV4cCI6MjA5Mjk0MTU5Nn0.VZJxCAbOfpiepbvgq9m0xC2wMe0IgFNlUUUC9wbk3Gc';

export function createSupabaseClient() {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
      flowType: 'pkce',
    },
  });
}
