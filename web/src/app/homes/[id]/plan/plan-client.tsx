"use client";

import Link from "next/link";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { Home } from "@/lib/types";

type Recommendation = {
  id: string;
  appliance_type: string;
  title: string;
  from_hours: number[];
  to_hours: number[];
  kwh_moved: number;
  grid_import_saved_kwh: number;
  reason: string;
  difficulty: "easy" | "medium" | "hard";
};
type Plan = {
  day: string;
  system_kw: number;
  summary: string;
  weather_source: string;
  weather_stale: boolean;
  metrics: {
    self_consumption_pct: number;
    solar_coverage_pct: number;
    evening_deficit_kwh: number;
    grid_import_kwh: number;
    plan_grid_import_kwh: number;
    total_load_kwh: number;
    plan_total_load_kwh: number;
    estimated_saving_pkr: number | null;
    cost_label: string;
  };
  solar_kw: number[];
  load_kw: number[];
  plan_load_kw: number[];
  recommendations: Recommendation[];
  tips: Array<{ type: string; text: string }>;
};
type Verdict = { day: string; status: string };

function localDay(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function previousDay(): string {
  const day = new Date();
  day.setDate(day.getDate() - 1);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

export default function PlanClient({ dashboard = false }: { dashboard?: boolean }) {
  const { id } = useParams<{ id: string }>();
  const [home, setHome] = useState<Home | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [panelKw, setPanelKw] = useState("");
  const [batteryKwh, setBatteryKwh] = useState("");
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadPlan = useCallback(async (selectedPanel: string, selectedBattery: string) => {
    setErrorMessage("");
    const query = new URLSearchParams({ date: localDay() });
    if (selectedPanel !== "") query.set("panel_kw", selectedPanel);
    if (selectedBattery !== "") query.set("battery_kwh", selectedBattery);
    try {
      const result = await apiFetch<Plan>(`/homes/${id}/recommendations?${query.toString()}`);
      setPlan(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load today’s plan.");
      setPlan(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiFetch<Home>(`/homes/${id}`),
      apiFetch<Verdict[]>(`/homes/${id}/verdicts?days=14`),
    ])
      .then(([homeData, verdicts]) => {
        if (!active) return;
        setHome(homeData);
        if (homeData.system_kw) setPanelKw(String(homeData.system_kw));
        setVerdict(verdicts.find((item) => item.day === previousDay()) ?? null);
        void loadPlan(homeData.system_kw ? String(homeData.system_kw) : "", "");
      })
      .catch((error: unknown) => {
        if (active) setErrorMessage(error instanceof Error ? error.message : "Could not load your home.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [id, loadPlan]);

  const chartData = useMemo(() => plan?.load_kw.map((load, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    solar: plan.solar_kw[hour],
    current: load,
    planned: plan.plan_load_kw[hour],
  })) ?? [], [plan]);

  async function sendFeedback(recommendation: Recommendation, status: "done" | "not_possible") {
    if (!plan) return;
    setBusy(true);
    setErrorMessage("");
    setNotice("");
    try {
      await apiFetch(
        `/homes/${id}/recommendations/${encodeURIComponent(recommendation.id)}/feedback`,
        {
          method: "POST",
          body: JSON.stringify({ day: plan.day, status }),
        },
      );
      setFeedback((current) => ({ ...current, [recommendation.id]: status }));
      setNotice(status === "done" ? "Thanks — marked as done." : "Thanks — we’ll avoid this time window in future suggestions.");
      if (status === "not_possible") await loadPlan(panelKw, batteryKwh);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save your feedback.");
    } finally {
      setBusy(false);
    }
  }

  async function updateSystemAssumptions() {
    setBusy(true);
    await loadPlan(panelKw, batteryKwh);
    setBusy(false);
  }

  if (loading) return <section className="home-content"><div className="loading-panel">Building your solar plan…</div></section>;

  return (
    <section className="home-content plan-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">{dashboard ? "HOME ENERGY DASHBOARD" : "SOLAR-HOUR PLAN"}</p>
          <h1>{dashboard ? "Your home at a glance" : "Today’s solar plan"}</h1>
          <p className="muted">Estimate for {plan?.day ?? localDay()}; shift flexible use only when practical.</p>
        </div>
        {!dashboard && <Link className="button button-quiet" href={`/homes/${id}/dashboard`}>Dashboard</Link>}
      </div>
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}
      {!plan ? (
        <div className="empty-panel">
          <h2>Choose a weather location</h2>
          <p className="muted">A saved city is needed to estimate the solar curve.</p>
          <Link className="button button-primary" href={`/homes/${id}/forecast`}>Set city</Link>
        </div>
      ) : (
        <>
          <section className="report-panel plan-assumptions">
            <div className="panel-heading"><div><p className="eyebrow">SYSTEM ASSUMPTION</p><h2>Solar size and battery</h2></div></div>
            <div className="plan-assumption-form">
              <label>
                Panel size (kWp)
                <input max="100" min="0" onChange={(event) => setPanelKw(event.target.value)} placeholder={home?.system_kw ? String(home.system_kw) : "Enter a planned size"} step="0.1" type="number" value={panelKw} />
              </label>
              <label>
                Battery capacity (optional, kWh)
                <input max="200" min="0" onChange={(event) => setBatteryKwh(event.target.value)} placeholder="Leave blank if unknown" step="0.1" type="number" value={batteryKwh} />
              </label>
              <button className="button button-primary" disabled={busy} onClick={() => void updateSystemAssumptions()} type="button">
                {busy ? "Updating…" : "Update plan"}
              </button>
            </div>
          </section>

          {dashboard && (
            <div className="report-stats dashboard-stats">
              <div className="report-stat"><span>Predicted today</span><strong>{plan.metrics.total_load_kwh.toFixed(1)} kWh</strong></div>
              <div className="report-stat"><span>Solar coverage</span><strong>{plan.metrics.solar_coverage_pct.toFixed(0)}%</strong></div>
              <div className="report-stat"><span>Self-consumption</span><strong>{plan.metrics.self_consumption_pct.toFixed(0)}%</strong></div>
              <div className="report-stat"><span>Yesterday</span><strong className={`verdict-text verdict-${verdict?.status ?? "unknown"}`}>{verdict?.status ?? "unknown"}</strong></div>
            </div>
          )}

          <section className="report-panel plan-panel">
            <div className="panel-heading">
            <div><p className="eyebrow">SOLAR AND LOAD</p><h2>{plan.summary}</h2></div>
              <span>{plan.system_kw.toFixed(1)} kWp</span>
            </div>
            <div className="chart-wrap plan-chart">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" vertical={false} />
                  <ReferenceArea x1="09:00" x2="16:00" fill="#eaf4e9" fillOpacity={0.75} />
                  <XAxis dataKey="hour" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} interval={3} />
                  <YAxis tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Line dataKey="solar" name="Solar (kW)" stroke="#d2a931" strokeWidth={2} dot={false} />
                  <Line dataKey="current" name="Current load (kW)" stroke="#718074" strokeWidth={2} dot={false} />
                  <Line dataKey="planned" name="Planned load (kW)" stroke="#438665" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="plan-metrics">
              <span>Grid import: <strong>{plan.metrics.grid_import_kwh.toFixed(1)} kWh</strong></span>
              <span>After plan: <strong>{plan.metrics.plan_grid_import_kwh.toFixed(1)} kWh</strong></span>
              <span>Solar window: <strong>09:00–17:00</strong></span>
            </div>
            <p className="muted plan-cost">
              {plan.metrics.estimated_saving_pkr === null
                ? plan.metrics.cost_label
                : `Estimated cost reduction: PKR ${plan.metrics.estimated_saving_pkr.toFixed(0)}. ${plan.metrics.cost_label}`}
            </p>
            <p className="forecast-source">
              Weather: {plan.weather_source}{plan.weather_stale ? " · cached data may be stale" : ""}.
              {Math.abs(plan.metrics.total_load_kwh - plan.metrics.plan_total_load_kwh) < 0.01 ? " Total energy remains unchanged; only timing moves." : ""}
            </p>
          </section>

          <section className="report-panel plan-panel">
            <div className="panel-heading"><div><p className="eyebrow">OPTIONAL ACTIONS</p><h2>Flexible loads to consider moving</h2></div></div>
            {plan.recommendations.length === 0 ? (
              <p className="muted">No worthwhile flexible-load move was found for this estimate. Fixed and essential loads are not moved.</p>
            ) : (
              <div className="recommendation-list">
                {plan.recommendations.map((recommendation) => (
                  <article className="recommendation-card" key={recommendation.id}>
                    <div>
                      <p className="recommendation-title">{recommendation.title}</p>
                      <p className="muted">{recommendation.reason}</p>
                      <small>About {recommendation.kwh_moved.toFixed(2)} kWh moved · {recommendation.grid_import_saved_kwh.toFixed(2)} kWh less grid import · {recommendation.difficulty}</small>
                    </div>
                    <div className="recommendation-actions">
                      <button className="button button-primary" disabled={busy || Boolean(feedback[recommendation.id])} onClick={() => void sendFeedback(recommendation, "done")} type="button">
                        {feedback[recommendation.id] === "done" ? "Marked done" : "Done"}
                      </button>
                      <button className="button button-quiet" disabled={busy || Boolean(feedback[recommendation.id])} onClick={() => void sendFeedback(recommendation, "not_possible")} type="button">
                        {feedback[recommendation.id] === "not_possible" ? "Saved" : "Not possible"}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          {plan.tips.length > 0 && (
            <section className="report-panel plan-panel">
              <div className="panel-heading"><div><p className="eyebrow">CONTEXT</p><h2>Other things to know</h2></div></div>
              <ul className="driver-list">{plan.tips.map((tip, index) => <li key={`${tip.type}-${index}`}>{tip.text}</li>)}</ul>
            </section>
          )}
        </>
      )}
      <p className="disclaimer">
        These are cautious estimates, not safety-critical instructions. Keep essential loads running and follow appliance manufacturer guidance.
      </p>
    </section>
  );
}
