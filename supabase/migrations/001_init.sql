-- ── The Orbital — Phase 1 schema ────────────────────────────────────────────
-- Run this in the Supabase SQL editor: https://supabase.com/dashboard/project/lathlnothoosbwrvxtel/sql

-- ── user_profiles ────────────────────────────────────────────────────────────
-- Mirror of auth.users with display-friendly fields.
-- Created on first sign-in via auth callback, updated on subsequent sign-ins.

create table if not exists public.user_profiles (
  id             uuid primary key references auth.users(id) on delete cascade,
  email          text not null,
  display_name   text,
  avatar_url     text,
  last_sign_in   timestamptz,
  created_at     timestamptz not null default now()
);

alter table public.user_profiles enable row level security;

-- Users can read and update their own profile only
create policy "users: select own profile"
  on public.user_profiles for select
  using (auth.uid() = id);

create policy "users: update own profile"
  on public.user_profiles for update
  using (auth.uid() = id);

create policy "users: insert own profile"
  on public.user_profiles for insert
  with check (auth.uid() = id);

-- ── invites ──────────────────────────────────────────────────────────────────
-- Managed exclusively via the invite-user.py script (service role key).
-- No RLS policies for anon — the invite check in auth/callback uses the admin client.

create table if not exists public.invites (
  id         bigint primary key generated always as identity,
  email      text not null unique,
  invited_by text,           -- optional note: who invited this person
  created_at timestamptz not null default now(),
  used_at    timestamptz     -- null = unused
);

alter table public.invites enable row level security;

-- Authenticated users can read their own invite row (needed for client-side invite check)
-- They cannot insert, update, or delete — that's service-role-only via invite-user.py
create policy "users: check own invite"
  on public.invites for select
  using (auth.jwt()->>'email' = email);

-- ── reads (Phase 2 — created now, populated later) ───────────────────────────
-- One row per article/video a user has read.
-- Article metadata is snapshotted here because content lives in JSON files,
-- not in Postgres — so stats queries can run entirely within Postgres.

create table if not exists public.reads (
  id              bigint primary key generated always as identity,
  user_id         uuid not null references auth.users(id) on delete cascade,
  article_slug    text not null,
  article_title   text,
  article_date    date,
  orientations    text[],    -- snapshotted from news.json at read-time
  tags            text[],
  source_url      text,
  read_at         timestamptz not null default now(),
  unique (user_id, article_slug)
);

alter table public.reads enable row level security;

create policy "users: select own reads"
  on public.reads for select
  using (auth.uid() = user_id);

create policy "users: insert own reads"
  on public.reads for insert
  with check (auth.uid() = user_id);

create policy "users: delete own reads"
  on public.reads for delete
  using (auth.uid() = user_id);

-- Index for fast per-user lookups
create index if not exists reads_user_id_idx on public.reads(user_id);
create index if not exists reads_read_at_idx on public.reads(user_id, read_at desc);
