import { defineMiddleware } from 'astro:middleware';
import { createSupabaseServerClient } from './lib/supabase';

// Only SSR pages invoke this middleware; static pages are pre-rendered and skip it.
export const onRequest = defineMiddleware(async (context, next) => {
  const supabase = createSupabaseServerClient(context.request, context.cookies);
  context.locals.supabase = supabase;

  // Refresh session (rotates tokens if needed, writes updated cookies to response)
  const { data: { session } } = await supabase.auth.getSession();
  context.locals.session = session;
  context.locals.user = session?.user ?? null;

  return next();
});
