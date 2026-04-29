// Middleware is a no-op for now — all pages are statically prerendered.
// Auth state is managed client-side via @supabase/ssr createBrowserClient.
// If SSR pages are added in future, expand this file.
import { defineMiddleware } from 'astro:middleware';
export const onRequest = defineMiddleware((_ctx, next) => next());
