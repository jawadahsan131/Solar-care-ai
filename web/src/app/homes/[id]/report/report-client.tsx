"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiFetch } from "@/lib/api";
import type { Appliance, Home, SizingResult } from "@/lib/types";
import CalibrationCard from "./calibration-card";

type Assumptions = {
  peak_sun_hours: number;
  outage_hours: number;
  autonomy_days: number;
  battery_dod: number;
};

type SavedBill = { month: string; units_kwh: number };
type Calibration = {
  estimated_monthly_kwh: number;
  bill_monthly_kwh: number | null;
  ratio: number | null;
  band: string;
};
type SavedReport = { report_id: string; created_at: string; result: SizingResult };

const optionCopy = {
  off_grid: {
    title: "Off-grid",
    description: "For a home that needs to run independently from the grid.",
    tone: "gold",
  },
  hybrid: {
    title: "Hybrid",
    description: "Solar with grid support and backup for essential loads.",
    tone: "green",
  },
  on_grid: {
    title: "On-grid",
    description: "For reducing daytime grid use; this estimate includes no battery.",
    tone: "blue",
  },
} as const;

export default function SizingReportPage() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<SizingResult | null>(null);
  const [reportId, setReportId] = useState("");
  const [createdAt, setCreatedAt] = useState("");
  const [home, setHome] = useState<Home | null>(null);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [latestBill, setLatestBill] = useState<SavedBill | null>(null);
  const [calibration, setCalibration] = useState<Calibration | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(true);
  const [detailsError, setDetailsError] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [assumptions, setAssumptions] = useState({
    peak_sun_hours: 5,
    outage_hours: 4,
    autonomy_days: 1,
    battery_dod: 0.8,
  });

  useEffect(() => {
    let active = true;
    void Promise.allSettled([
      apiFetch<Home>(`/homes/${id}`),
      apiFetch<Appliance[]>(`/homes/${id}/appliances`),
      apiFetch<SavedBill[]>(`/homes/${id}/bills`),
      apiFetch<Calibration>(`/homes/${id}/calibration`),
    ]).then(([homeResult, applianceResult, billResult, calibrationResult]) => {
      if (!active) return;
      const failures: string[] = [];
      if (homeResult.status === "fulfilled") setHome(homeResult.value);
      else failures.push("home details");
      if (applianceResult.status === "fulfilled") setAppliances(applianceResult.value);
      else failures.push("appliances");
      if (billResult.status === "fulfilled") setLatestBill(billResult.value[0] ?? null);
      else failures.push("bills");
      if (calibrationResult.status === "fulfilled") setCalibration(calibrationResult.value);
      else failures.push("bill calibration");
      if (failures.length) setDetailsError(`Could not load ${failures.join(", ")} for the printable report.`);
      setDetailsLoading(false);
    });
    return () => { active = false; };
  }, [id]);

  async function calculate() {
    setBusy(true);
    setErrorMessage("");
    try {
      const report = await apiFetch<SavedReport>(`/homes/${id}/size`, {
        method: "POST",
        body: JSON.stringify({ assumptions }),
      });
      setResult(report.result);
      setReportId(report.report_id);
      setCreatedAt(report.created_at);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not calculate a report.");
    } finally {
      setBusy(false);
    }
  }

  const hourlyData = result?.load_profile_kw.map((load, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    load,
  })) ?? [];
  const breakdownData = result?.breakdown.slice(0, 8).map((item) => ({
    type: item.type.replaceAll("_", " "),
    kwh: item.kwh,
  })) ?? [];

  return (
    <section className="home-content report-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">SOLAR ESTIMATE</p>
          <h1>Your sizing report</h1>
          <p className="muted">A planning estimate based on your saved appliance list.</p>
        </div>
        {result && <button className="button button-quiet print-button" onClick={() => window.print()}>Print / Save PDF</button>}
      </div>
      {errorMessage && <p className="inline-error screen-only" role="alert">{errorMessage}</p>}
      {detailsError && <p className="inline-error screen-only" role="alert">{detailsError}</p>}
      <div className="screen-report">
      <CalibrationCard />

      {!result ? (
        <div className="report-start-card">
          <div className="report-start-icon" aria-hidden="true">☼</div>
          <h2>Compare three ways to go solar</h2>
          <p className="muted">
            Your appliance hours and running power will be used to calculate panel,
            inverter, and battery estimates.
          </p>
          <button className="button button-primary button-large" disabled={busy || detailsLoading} onClick={() => void calculate()}>
            {busy ? "Calculating…" : detailsLoading ? "Loading home data…" : "Calculate my solar system"}
          </button>
        </div>
      ) : (
        <>
          {result.warnings.length > 0 && (
            <section className="warning-list" aria-label="Sizing warnings">
              {result.warnings.map((warning) => (
                <p key={warning}><span aria-hidden="true">!</span>{warning}</p>
              ))}
            </section>
          )}

          <div className="report-stats">
            <ReportStat label="Daily energy" value={`${result.daily_kwh.toFixed(2)} kWh`} />
            <ReportStat label="Peak load" value={`${result.peak_kw.toFixed(2)} kW`} />
            <ReportStat label="Connected load" value={`${result.connected_kw.toFixed(2)} kW`} />
          </div>

          <section className="option-grid">
            {result.options.map((option) => {
              const copy = optionCopy[option.kind];
              return (
                <article className={`system-option option-${copy.tone}`} key={option.kind}>
                  <span className="option-kicker">{copy.title} system</span>
                  <p>{copy.description}</p>
                  <div className="option-numbers">
                    <div><strong>{option.panel_kw.toFixed(2)}</strong><span>Panel kW</span></div>
                    <div><strong>{option.inverter_kw.toFixed(2)}</strong><span>Inverter kW</span></div>
                    <div><strong>{option.battery_kwh.toFixed(2)}</strong><span>Battery kWh</span></div>
                  </div>
                  {option.notes.map((note) => <small className="option-note" key={note}>{note}</small>)}
                </article>
              );
            })}
          </section>

          <div className="report-chart-grid">
            <section className="report-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">YOUR DAY</p><h2>Hourly appliance load</h2></div>
                <span>kW</span>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hourlyData} margin={{ top: 10, right: 4, bottom: 0, left: -20 }}>
                    <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="hour" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} interval={3} />
                    <YAxis tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} kW`, "Average load"]} />
                    <Bar dataKey="load" fill="#438665" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="day-night-split">
                <span><i className="day-dot" />Day <strong>{result.day_kwh.toFixed(2)} kWh</strong></span>
                <span><i className="night-dot" />Night <strong>{result.night_kwh.toFixed(2)} kWh</strong></span>
              </div>
            </section>

            <section className="report-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">ENERGY BREAKDOWN</p><h2>Largest daily loads</h2></div>
                <span>kWh/day</span>
              </div>
              {breakdownData.length ? (
                <div className="chart-wrap breakdown-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={breakdownData} layout="vertical" margin={{ top: 4, right: 18, bottom: 0, left: 3 }}>
                      <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                      <YAxis dataKey="type" type="category" width={92} tick={{ fill: "#526357", fontSize: 10 }} tickLine={false} axisLine={false} />
                      <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} kWh`, "Daily energy"]} />
                      <Bar dataKey="kwh" fill="#d2a931" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="muted">No appliance energy data is available.</p>
              )}
            </section>
          </div>

          <section className="assumptions-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">TUNE THE ESTIMATE</p><h2>Planning assumptions</h2></div>
              <span>Change and recalculate</span>
            </div>
            <div className="assumption-fields">
              <AssumptionInput label="Peak sun hours / day" max={10} min={1} name="peak_sun_hours" onChange={setAssumptions} value={assumptions.peak_sun_hours} step={0.5} />
              <AssumptionInput label="Outage coverage (hours)" max={24} min={1} name="outage_hours" onChange={setAssumptions} value={assumptions.outage_hours} step={1} />
              <AssumptionInput label="Battery autonomy (days)" max={5} min={0.5} name="autonomy_days" onChange={setAssumptions} value={assumptions.autonomy_days} step={0.5} />
              <label>Battery depth of discharge
                <select
                  onChange={(event) => setAssumptions((values) => ({ ...values, battery_dod: Number(event.target.value) }))}
                  value={assumptions.battery_dod}
                >
                  <option value={0.8}>Lithium · 80%</option>
                  <option value={0.5}>Lead-acid · 50%</option>
                </select>
              </label>
            </div>
            <button className="button button-primary" disabled={busy} onClick={() => void calculate()}>
              {busy ? "Recalculating…" : "Recalculate"}
            </button>
          </section>
        </>
      )}
      <p className="disclaimer">
        This is an estimate for planning, not an installation design. Please confirm
        appliance ratings and system sizing with a qualified installer.
      </p>
      </div>
      {result && (
        <article className="print-report">
          <header className="print-report-header">
            <p className="eyebrow">SOLAR CARE · SYSTEM PLANNING REPORT</p>
            <h1>{home?.name ?? "Home solar estimate"}</h1>
            <p>{home?.city ?? "Location not set"} · Generated {createdAt ? new Date(createdAt).toLocaleDateString() : "today"}</p>
          </header>

          <section className="print-report-summary">
            <div><span>Estimated daily energy</span><strong>{result.daily_kwh.toFixed(2)} kWh</strong></div>
            <div><span>Peak load</span><strong>{result.peak_kw.toFixed(2)} kW</strong></div>
            <div><span>Connected load</span><strong>{result.connected_kw.toFixed(2)} kW</strong></div>
          </section>

          <section className="print-report-section">
            <h2>Appliances and source</h2>
            {appliances.length > 0 ? (
              <table className="print-appliance-table">
                <thead><tr><th>Appliance</th><th>Qty</th><th>Watts</th><th>Hours/day</th><th>Source</th><th>Review</th></tr></thead>
                <tbody>
                  {appliances.map((appliance) => (
                    <tr key={appliance.id}>
                      <td>{appliance.type.replaceAll("_", " ")}{appliance.brand ? ` · ${appliance.brand}` : ""}</td>
                      <td>{appliance.qty}</td>
                      <td>{appliance.watts}</td>
                      <td>{appliance.hours_per_day.toFixed(1)}</td>
                      <td>{appliance.source_tag}</td>
                      <td>{appliance.user_verified ? "Verified" : "Needs review"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p>No saved appliances are available.</p>}
          </section>

          <section className="print-report-section">
            <h2>System options</h2>
            <div className="print-options">
              {result.options.map((option) => (
                <div key={option.kind}>
                  <strong>{option.kind.replaceAll("_", " ")}</strong>
                  <span>{option.panel_kw.toFixed(1)} kW panels</span>
                  <span>{option.inverter_kw.toFixed(1)} kW inverter</span>
                  <span>{option.battery_kwh.toFixed(1)} kWh battery</span>
                </div>
              ))}
            </div>
          </section>

          <section className="print-report-section print-calibration">
            <h2>Bill calibration</h2>
            {calibration?.bill_monthly_kwh !== null && calibration?.bill_monthly_kwh !== undefined ? (
              <p>
                Latest bill ({latestBill?.month ?? "month unavailable"}): {calibration.bill_monthly_kwh.toFixed(1)} kWh/month.
                Appliance estimate: {calibration.estimated_monthly_kwh.toFixed(1)} kWh/month
                {calibration.ratio !== null ? ` · calibration ratio ${calibration.ratio.toFixed(2)}` : ""}.
              </p>
            ) : <p>No bill is available for calibration.</p>}
          </section>

          <section className="print-report-section print-assumptions">
            <h2>Assumptions and warnings</h2>
            <ul>
              {Object.entries(result.assumptions).map(([name, value]) => <li key={name}>{name.replaceAll("_", " ")}: {value}</li>)}
              {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          </section>

          <p className="print-report-disclaimer">
            Planning estimate, not a quotation or installation design. Confirm appliance ratings and system sizing with a qualified installer.
          </p>
          <footer className="print-report-footer">
            Report ID: {reportId || "not available"} · Generated {createdAt ? new Date(createdAt).toLocaleString() : "today"}
          </footer>
        </article>
      )}
    </section>
  );
}

function ReportStat({ label, value }: { label: string; value: string }) {
  return <div className="report-stat"><span>{label}</span><strong>{value}</strong></div>;
}

function AssumptionInput({
  label,
  name,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  name: keyof Assumptions;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: Dispatch<SetStateAction<Assumptions>>;
}) {
  return (
    <label>{label}
      <input
        max={max}
        min={min}
        name={name}
        onChange={(event) => onChange((values) => ({ ...values, [name]: Number(event.target.value) }))}
        step={step}
        type="number"
        value={value}
      />
    </label>
  );
}
