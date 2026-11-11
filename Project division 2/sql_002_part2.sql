-- sql/migrations/002_part2.sql  (run once in Supabase SQL Editor AFTER schema.sql)

alter table daily_logs add column if not exists appliance_hours jsonb;
alter table daily_logs add column if not exists predicted_kwh numeric;
alter table daily_logs add column if not exists weather jsonb;
alter table daily_logs add column if not exists source text not null default 'user';

create table if not exists weather_cache (
  lat2 numeric not null,
  lon2 numeric not null,
  day date not null,
  kind text not null check (kind in ('forecast','archive')),
  hourly jsonb not null,
  fetched_at timestamptz not null default now(),
  primary key (lat2, lon2, day, kind)
);

create table if not exists demand_models (
  home_id uuid primary key references homes(id) on delete cascade,
  params jsonb not null default '{}'::jsonb,
  n_days int not null default 0,
  metrics jsonb,
  fitted_at timestamptz not null default now()
);

create table if not exists recommendation_feedback (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references homes(id) on delete cascade,
  day date not null,
  rec_id text not null,
  status text not null check (status in ('done','skipped','not_possible')),
  created_at timestamptz not null default now()
);

-- Row Level Security
alter table demand_models enable row level security;
create policy "own demand models" on demand_models for all
  using (exists (select 1 from homes h where h.id = demand_models.home_id and h.user_id = auth.uid()))
  with check (exists (select 1 from homes h where h.id = demand_models.home_id and h.user_id = auth.uid()));

alter table recommendation_feedback enable row level security;
create policy "own rec feedback" on recommendation_feedback for all
  using (exists (select 1 from homes h where h.id = recommendation_feedback.home_id and h.user_id = auth.uid()))
  with check (exists (select 1 from homes h where h.id = recommendation_feedback.home_id and h.user_id = auth.uid()));

-- weather_cache holds public weather only; only the API (service role) touches it
alter table weather_cache enable row level security;
