-- ── The Orbital — admin role + editorial overrides ─────────────────────────
-- Run this in: https://supabase.com/dashboard/project/lathlnothoosbwrvxtel/sql/new

-- 1. Add is_admin to user_profiles
alter table public.user_profiles
  add column if not exists is_admin boolean not null default false;

-- 2. Mark Olle as admin (replace with your actual email if different)
--    Uncomment and edit, then run:
-- update public.user_profiles set is_admin = true where email = 'olle@example.com';

-- 3. Editorial tier overrides — admin can promote stream→main or demote main→stream
--    without modifying news.json.
create table if not exists public.editorial_overrides (
  slug         text primary key,
  tier         text not null check (tier in ('main', 'stream')),
  set_by       uuid not null references auth.users(id) on delete cascade,
  set_at       timestamptz not null default now(),
  note         text
);

alter table public.editorial_overrides enable row level security;

-- Anyone signed in can READ overrides (so the client can apply them)
create policy "all signed-in: read overrides"
  on public.editorial_overrides for select
  to authenticated
  using (true);

-- Only admins can WRITE overrides
create policy "admins: insert overrides"
  on public.editorial_overrides for insert
  to authenticated
  with check (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );

create policy "admins: update overrides"
  on public.editorial_overrides for update
  to authenticated
  using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  )
  with check (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );

create policy "admins: delete overrides"
  on public.editorial_overrides for delete
  to authenticated
  using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and is_admin = true
    )
  );
