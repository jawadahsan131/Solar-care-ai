create extension if not exists "pgcrypto";

create table if not exists public.homes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'My home',
  city text,
  lat double precision,
  lon double precision,
  family_size integer check (family_size between 1 and 50),
  system_kw numeric,
  created_at timestamptz not null default now()
);

create table if not exists public.appliance_catalog (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  brand text,
  model text,
  capacity_value numeric,
  capacity_unit text,
  rated_watts numeric not null check (rated_watts >= 0),
  duty_factor numeric not null default 1.0 check (duty_factor > 0 and duty_factor <= 1),
  inverter boolean,
  surge_factor numeric not null default 1.0 check (surge_factor >= 1),
  default_hours numeric check (default_hours between 0 and 24),
  source text,
  verified boolean not null default false,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.home_appliances (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  room text,
  type text not null,
  brand text,
  model text,
  capacity_value numeric,
  capacity_unit text,
  inverter boolean,
  watts numeric not null check (watts >= 0 and watts <= 20000),
  duty_factor numeric not null default 1.0 check (duty_factor > 0 and duty_factor <= 1),
  surge_factor numeric not null default 1.0 check (surge_factor >= 1),
  qty integer not null default 1 check (qty between 1 and 50),
  hourly_use jsonb not null default '[]'::jsonb,
  is_essential boolean not null default false,
  source_tag text not null default 'user'
    check (source_tag in ('label', 'catalog', 'guess', 'user')),
  confidence numeric check (confidence between 0 and 1),
  user_verified boolean not null default false,
  image_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_home_appliances_home on public.home_appliances(home_id);

create table if not exists public.detections (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  room text,
  image_path text,
  backend text,
  predicted jsonb not null default '[]'::jsonb,
  final jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_detections_home on public.detections(home_id, created_at desc);

create table if not exists public.bills (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  month date not null,
  units_kwh numeric not null check (units_kwh >= 0),
  raw jsonb,
  created_at timestamptz not null default now(),
  unique (home_id, month)
);

create table if not exists public.daily_logs (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  log_date date not null,
  ac_hours numeric,
  outage_hours numeric,
  guests boolean,
  meter_kwh numeric,
  notes text,
  created_at timestamptz not null default now(),
  unique (home_id, log_date)
);

create table if not exists public.sizing_reports (
  id uuid primary key default gen_random_uuid(),
  home_id uuid not null references public.homes(id) on delete cascade,
  input jsonb not null,
  result jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_sizing_reports_home on public.sizing_reports(home_id, created_at desc);

alter table public.homes enable row level security;
alter table public.appliance_catalog enable row level security;
alter table public.home_appliances enable row level security;
alter table public.detections enable row level security;
alter table public.bills enable row level security;
alter table public.daily_logs enable row level security;
alter table public.sizing_reports enable row level security;

drop policy if exists "own homes" on public.homes;
create policy "own homes" on public.homes for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "catalog readable" on public.appliance_catalog;
create policy "catalog readable" on public.appliance_catalog for select to authenticated
  using (true);

drop policy if exists "own appliances" on public.home_appliances;
create policy "own appliances" on public.home_appliances for all
  using (
    exists (
      select 1 from public.homes h
      where h.id = home_appliances.home_id and h.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.homes h
      where h.id = home_appliances.home_id and h.user_id = auth.uid()
    )
  );

drop policy if exists "own detections" on public.detections;
create policy "own detections" on public.detections for all
  using (
    exists (
      select 1 from public.homes h
      where h.id = detections.home_id and h.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.homes h
      where h.id = detections.home_id and h.user_id = auth.uid()
    )
  );

drop policy if exists "own bills" on public.bills;
create policy "own bills" on public.bills for all
  using (
    exists (
      select 1 from public.homes h
      where h.id = bills.home_id and h.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.homes h
      where h.id = bills.home_id and h.user_id = auth.uid()
    )
  );

drop policy if exists "own daily logs" on public.daily_logs;
create policy "own daily logs" on public.daily_logs for all
  using (
    exists (
      select 1 from public.homes h
      where h.id = daily_logs.home_id and h.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.homes h
      where h.id = daily_logs.home_id and h.user_id = auth.uid()
    )
  );

drop policy if exists "own reports" on public.sizing_reports;
create policy "own reports" on public.sizing_reports for all
  using (
    exists (
      select 1 from public.homes h
      where h.id = sizing_reports.home_id and h.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.homes h
      where h.id = sizing_reports.home_id and h.user_id = auth.uid()
    )
  );
