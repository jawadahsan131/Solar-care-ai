# CHUNK 10 — Weather and solar forecast
(Paste MASTER BRIEF + PART 2 ADDENDUM, then this card. Independent of chunk 9; can run in parallel. Needs `homes` with lat/lon and `weather_cache` (run `sql_002_part2.sql`).)

## Goal
For any home and date, return 24-hour weather and an estimated solar generation curve per installed kW, with caching and fallbacks. Fully testable offline.

## Files (one at a time)
1. `api/app/services/part2_config.py` — constants from the addendum (create it here).
2. `api/app/services/weather.py` — Open-Meteo client (forecast + archive), cache, fallbacks.
3. `api/app/services/solar.py` — pure functions: PV curve, CDH, sun hours, daily summary.
4. `data/climate_normals.json` — monthly typical hourly temperature and GHI for major cities (Karachi, Lahore, Islamabad, Rawalpindi, Faisalabad, Multan, Peshawar, Quetta, Hyderabad, Sialkot). Mark values "approximate, replace with archive averages". Better: a script `scripts/build_normals.py` that downloads 3 years of archive data per city once and writes the file.
5. `api/app/routers/forecast.py` — endpoints.
6. `api/tests/fixtures/open_meteo_sample.json` (saved real response, trimmed) and `api/tests/test_solar.py`, `api/tests/test_weather_parse.py`.
7. Web: city picker (name -> lat/lon) in home settings + `/homes/[id]/forecast` page.

## weather.py
- `get_day(lat, lon, day)` -> HourlyWeather. Choose endpoint by date: past -> archive, today and the next 7 days -> forecast. Round lat/lon to 2 decimals for the cache key. Cache hit: forecast entries older than 3 hours are refreshed; archive entries never expire.
- Timezone Asia/Karachi so hour 0..23 = local time. Missing values -> linear interpolation for gaps up to 3 hours, otherwise fallback.
- Fallback order: fresh API -> stale cache (mark `stale=true`) -> climate normal (mark `source="normal"`). Always return the source so the UI can say "estimated from typical weather".
- Timeout 10 s, one retry, never crash the endpoint. Respect the free API: batch a 7-day request in one call, no per-hour calls.

## solar.py (pure, unit-tested)
- `pv_kw_per_kwp(ghi, temp_c)` per hour: `ghi/1000 * PR * (1 + temp_coeff*(cell_temp-25))` with `cell_temp = temp_c + 20*(ghi/800)`. Clamp at 0. Result is kW per 1 kWp installed. Multiply by `system_kw` to get kW.
- `sun_hours(ghi_series)` = sum(ghi)/1000 (peak-sun-hours equivalent for the day). Used to refine the sizing assumption (`peak_sun_hours`) per season.
- `cdh(temp_series, setpoint)`; `hdh` for heating if needed.
- `daily_summary(hourly)` -> {tmax, tmin, mean_cloud, sun_hours, cdh, text}. Text example "Hot and sunny: 38 C max, about 6.1 sun hours".
- Soiling note: add an optional `soiling_loss` (default 0.03, higher after dust days) as a documented assumption.

## Endpoints
- `GET /homes/{id}/forecast?date=&days=1..7` -> list of Forecast objects (addendum shapes). 400 if home has no lat/lon with a clear message and the city picker link.
- `GET /cities` -> list for the picker.

## Web page
- Today and next 7 days: temperature line, solar curve (kW per kWp, or kW if `system_kw` is set), sun-hours badge, source label ("live forecast" / "estimated"). No heavy design, a clear chart (Recharts) and a text summary.

## Tests (offline)
- PV curve is zero at night and peaks around midday for the fixture; temperature derate lowers output on a 45 C day vs 25 C; sun hours for the fixture match a hand calculation; fallback path returns `source="normal"` when the HTTP call is mocked to fail; cache key rounding.

## Acceptance
- [ ] Forecast for Lahore and Karachi for the next 3 days renders on the page.
- [ ] Turning off the network in the test still returns a labelled fallback.
- [ ] 100 consecutive calls make at most a handful of upstream requests (cache works).

## Handoff
HANDOFF NOTE: endpoint names and variables used, rate/limit findings, cities included.
