-- Run once in the Supabase SQL Editor after sql/schema.sql.
alter table public.daily_logs add column if not exists appliance_hours jsonb;
alter table public.daily_logs add column if not exists predicted_kwh numeric;
alter table public.daily_logs add column if not exists weather jsonb;
alter table public.daily_logs add column if not exists source text not null default 'user';

create table if not exists public.weather_cache (
  lat2 numeric not null,
  lon2 numeric not null,
  day date not null,
  hourly jsonb not null,
  kind text not null check (kind in ('forecast', 'archive')),
  fetched_at timestamptz not null default now(),
  primary key (lat2, lon2, day, kind)
);

create table if not exists public.demand_models (
  home_id uuid primary key references public.homes(id) on delete cascade,
  params jsonb not null default '{}'::jsonb,
  fitted_at timestamptz not null default now(),
  n_days integer not null default 0,
  metrics jsonb
);

create table if not exists public.recommendation_feedback (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  day date not null,
  rec_id text not null,
  status text not null check (status in ('done', 'skipped', 'not_possible')),
  created_at timestamptz not null default now()
);

alter table public.weather_cache enable row level security;
alter table public.demand_models enable row level security;
alter table public.recommendation_feedback enable row level security;

drop policy if exists "own demand models" on public.demand_models;
create policy "own demand models" on public.demand_models for all
  using (exists (
    select 1 from public.homes h
    where h.id = demand_models.home_id and h.user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.homes h
    where h.id = demand_models.home_id and h.user_id = auth.uid()
  ));

drop policy if exists "own rec feedback" on public.recommendation_feedback;
create policy "own rec feedback" on public.recommendation_feedback for all
  using (exists (
    select 1 from public.homes h
    where h.id = recommendation_feedback.home_id and h.user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.homes h
    where h.id = recommendation_feedback.home_id and h.user_id = auth.uid()
  ));

-- Weather is public data; only the API service role accesses this cache.
