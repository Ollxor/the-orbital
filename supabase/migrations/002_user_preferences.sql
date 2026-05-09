-- ── The Orbital — Phase 3: per-user feed filtering ─────────────────────────
-- Run this in: https://supabase.com/dashboard/project/lathlnothoosbwrvxtel/sql/new

create table if not exists public.user_preferences (
  user_id              uuid primary key references auth.users(id) on delete cascade,
  -- Hide-lists: empty arrays mean "show everything in that dimension"
  orientations_hide    text[] not null default array[]::text[],   -- e.g. ['MYSTERIES']
  tags_hide            text[] not null default array[]::text[],
  tags_follow          text[] not null default array[]::text[],   -- pin to top
  sources_hide         text[] not null default array[]::text[],   -- by source name
  show_articles        boolean not null default true,
  show_videos          boolean not null default true,
  show_stream          boolean not null default false,            -- false = main only
  -- Free-text preference prompt (v2: server-side LLM filter)
  personal_prompt      text,
  updated_at           timestamptz not null default now()
);

alter table public.user_preferences enable row level security;

-- Users can read and write their own preferences only
create policy "users: read own prefs"
  on public.user_preferences for select
  using (auth.uid() = user_id);

create policy "users: insert own prefs"
  on public.user_preferences for insert
  with check (auth.uid() = user_id);

create policy "users: update own prefs"
  on public.user_preferences for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users: delete own prefs"
  on public.user_preferences for delete
  using (auth.uid() = user_id);

-- Updated_at trigger
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists user_preferences_set_updated_at on public.user_preferences;
create trigger user_preferences_set_updated_at
  before update on public.user_preferences
  for each row execute procedure public.set_updated_at();
