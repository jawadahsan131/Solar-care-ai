"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiFetch } from "@/lib/api";
import type { Home } from "@/lib/types";

type Variant = {
  yearly_solar_kwh: number;
  yearly_load_kwh: number;
  solar_coverage_pct: number;
  self_consumption_pct: number;
  grid_import_avoided_kwh: number;
  yearly_bill_saving_pkr: number | null;
  evening_battery_kwh_per_year: number;
  outage_coverage_hours: number;
};
type Scenario = {
  id: string;
  label: string;
  panel_kw: number;
  battery_kwh: number;
  inverter_kw: number;
  estimated_investment_pkr: number | null;
  payback_range_years: { low_years: number; high_years: number } | null;
  sensitivity: { low: Variant; base: Variant; high: Variant };
};
type WhatIfResult = {
  city: string | null;
  weather_source: string;
  appliance_count: number;
  assumptions: string[];
  scenarios: Scenario[];
  seasonal_average_day: Record<string, { solar_kw: number[]; load_kw: number[] }>;
  sensitivity_assumptions: Record<string, string>;
  tariff_available: boolean;
};

const SEASONS = ["Winter", "Spring", "Summer", "Autumn"];

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export default function WhatIfClient() {
  const { id } = useParams<{ id: string }>();
  const [home, setHome] = useState<Home | null>(null);
  const [panelKw, setPanelKw] = useState(5);
  const [batteryKwh, setBatteryKwh] = useState(5);
  const [outageHours, setOutageHours] = useState(4);
  const [costPerKw, setCostPerKw] = useState("");
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [season, setSeason] = useState("Summer");
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;
    void apiFetch<Home>(`/homes/${id}`)
      .then((data) => {
        if (!active) return;
        setHome(data);
        if (data.system_kw !== null && data.system_kw !== undefined) {
          setPanelKw(data.system_kw);
        }
      })
      .catch((error: unknown) => {
        if (active) setErrorMessage(error instanceof Error ? error.message : "Could not load this home.");
      });
    return () => { active = false; };
  }, [id]);

  const compare = useCallback(async () => {
    setBusy(true);
    setErrorMessage("");
    try {
      const payload: {
        panel_kw: number;
        battery_kwh: number;
        outage_hours: number;
        cost_per_kw_pkr?: number;
      } = { panel_kw: panelKw, battery_kwh: batteryKwh, outage_hours: outageHours };
      if (costPerKw.trim()) {
        const cost = Number(costPerKw);
        if (!Number.isFinite(cost) || cost < 0 || cost > 100_000_000) {
          throw new Error("Enter an installed cost per kW between 0 and 100,000,000 PKR.");
        }
        payload.cost_per_kw_pkr = cost;
      }
      const response = await apiFetch<WhatIfResult>(`/homes/${id}/whatif`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setResult(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not run the what-if estimate.");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, [batteryKwh, costPerKw, id, outageHours, panelKw]);

  const chartData = useMemo(() => {
    const profile = result?.seasonal_average_day[season];
    if (!profile) return [];
    return profile.load_kw.map((load, hour) => ({
      hour: `${String(hour).padStart(2, "0")}:00`,
      solar: profile.solar_kw[hour],
      load,
    }));
  }, [result, season]);

  return (
    <section className="home-content whatif-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">PRE-PURCHASE SCENARIOS</p>
          <h1>Explore solar system sizes</h1>
          <p className="muted">{home?.name ?? "Your home"}{home?.city ? ` · ${home.city}` : ""}</p>
        </div>
      </div>
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}

      <section className="report-panel whatif-controls">
        <div className="panel-heading">
          <div><p className="eyebrow">YOUR ASSUMPTIONS</p><h2>Adjust before comparing</h2></div>
        </div>
        <label className="whatif-slider">
          <span>Base panel size <strong>{panelKw.toFixed(1)} kWp</strong></span>
          <input max="100" min="0" onChange={(event) => setPanelKw(Number(event.target.value))} step="0.5" type="range" value={panelKw} />
        </label>
        <label className="whatif-slider">
          <span>Base battery capacity <strong>{batteryKwh.toFixed(1)} kWh</strong></span>
          <input max="30" min="0" onChange={(event) => setBatteryKwh(Number(event.target.value))} step="0.5" type="range" value={batteryKwh} />
        </label>
        <div className="whatif-extra-inputs">
          <label>
            Planned outage duration (hours)
            <input max="24" min="0" onChange={(event) => setOutageHours(Number(event.target.value))} step="1" type="number" value={outageHours} />
          </label>
          <label>
            Installed cost per kW (PKR, optional)
            <input max="100000000" min="0" onChange={(event) => setCostPerKw(event.target.value)} placeholder="Enter a quote; no default price is assumed" type="number" value={costPerKw} />
          </label>
        </div>
        <button className="button button-primary" disabled={busy} onClick={() => void compare()} type="button">
          {busy ? "Comparing…" : "Compare scenarios"}
        </button>
      </section>

      {result ? (
        <>
          <p className="whatif-disclaimer">Estimates, not a quotation. Results use {result.weather_source} for {result.city ?? "the selected location"} and {result.appliance_count} saved appliances.</p>
          <div className="whatif-scenario-grid">
            {result.scenarios.map((scenario) => {
              const base = scenario.sensitivity.base;
              return (
                <article className={`whatif-scenario scenario-${scenario.id}`} key={scenario.id}>
                  <p className="eyebrow">{scenario.label.toUpperCase()}</p>
                  <h2>{scenario.panel_kw.toFixed(1)} kWp{scenario.battery_kwh > 0 ? ` · ${scenario.battery_kwh.toFixed(1)} kWh battery` : " · no battery"}</h2>
                  <div className="whatif-primary-metric">
                    <strong>{formatNumber(base.solar_coverage_pct)}%</strong>
                    <span>of modeled load covered by solar and storage</span>
                  </div>
                  <dl>
                    <div><dt>Solar generation</dt><dd>{formatNumber(base.yearly_solar_kwh)} kWh/year</dd></div>
                    <div><dt>Self-consumed solar</dt><dd>{formatNumber(base.self_consumption_pct)}%</dd></div>
                    <div><dt>Grid import avoided</dt><dd>{formatNumber(base.grid_import_avoided_kwh)} kWh/year</dd></div>
                    <div><dt>Evening battery coverage</dt><dd>{formatNumber(base.evening_battery_kwh_per_year)} kWh/year</dd></div>
                    <div><dt>Outage coverage</dt><dd>{base.outage_coverage_hours.toFixed(1)} of {outageHours} hours</dd></div>
                    {base.yearly_bill_saving_pkr !== null && (
                      <div><dt>Estimated bill saving</dt><dd>PKR {formatNumber(base.yearly_bill_saving_pkr)}/year</dd></div>
                    )}
                  </dl>
                  <p className="whatif-band">
                    Range: {formatNumber(scenario.sensitivity.low.solar_coverage_pct)}–{formatNumber(scenario.sensitivity.high.solar_coverage_pct)}% load coverage
                  </p>
                  {scenario.estimated_investment_pkr !== null && (
                    <p className="whatif-payback">
                      User-entered cost estimate: PKR {formatNumber(scenario.estimated_investment_pkr)}
                      {scenario.payback_range_years
                        ? ` · Simple payback ${scenario.payback_range_years.low_years}–${scenario.payback_range_years.high_years} years`
                        : " · Payback unavailable without positive tariff savings"}
                    </p>
                  )}
                </article>
              );
            })}
          </div>
          {!result.tariff_available && (
            <p className="muted">Bill savings and payback are hidden until official rates are entered in data/tariff.json. This avoids inventing a tariff.</p>
          )}

          <section className="report-panel whatif-chart-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">SEASONAL PROFILE</p><h2>Typical day: solar vs. appliance load</h2></div>
              <span>kW</span>
            </div>
            <div className="season-select" role="group" aria-label="Select season">
              {SEASONS.map((item) => (
                <button aria-pressed={season === item} className={season === item ? "active" : ""} key={item} onClick={() => setSeason(item)} type="button">
                  {item}
                </button>
              ))}
            </div>
            <div className="whatif-chart">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 12, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} interval={3} />
                  <YAxis tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} kW`]} />
                  <Line dataKey="solar" name="Solar generation" stroke="#d2a931" strokeWidth={2.5} dot={false} />
                  <Line dataKey="load" name="Appliance load" stroke="#438665" strokeWidth={2.5} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="report-panel">
            <div className="panel-heading"><div><p className="eyebrow">SENSITIVITY AND LIMITS</p><h2>How to read the range</h2></div></div>
            <ul className="driver-list">
              {Object.entries(result.sensitivity_assumptions).map(([key, description]) => <li key={key}><strong>{key}: </strong>{description}</li>)}
              {result.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}
            </ul>
          </section>
        </>
      ) : (
        <div className="empty-panel">
          <h2>Compare three planning scenarios</h2>
          <p className="muted">The estimate runs one representative climate-normal day per month and weights it by that month’s days.</p>
          <button className="button button-primary" disabled={busy} onClick={() => void compare()} type="button">
            {busy ? "Comparing…" : "Run estimate"}
          </button>
        </div>
      )}
      <p className="disclaimer">Planning estimates only, not a quotation or installation design. Confirm system sizing, battery configuration, and safety with a qualified installer.</p>
    </section>
  );
}
