"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
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

type Demand = {
  day: string;
  hourly_kw: number[];
  total_kwh: number;
  low_kwh: number;
  high_kwh: number;
  by_type: Record<string, number>;
  drivers: string[];
  confidence: "low" | "medium" | "high";
  weather_source: string;
  weather_stale: boolean;
  learning_days: number;
};
type Verdict = {
  day: string;
  actual_kwh: number | null;
  expected_kwh: number;
  status: "normal" | "high" | "low" | "unknown";
  reasons: string[];
};

function yesterday(): string {
  const day = new Date();
  day.setDate(day.getDate() - 1);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

export default function TodayClient() {
  const { id } = useParams<{ id: string }>();
  const [demand, setDemand] = useState<Demand | null>(null);
  const [yesterdayVerdict, setYesterdayVerdict] = useState<Verdict | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [prediction, verdicts] = await Promise.all([
        apiFetch<Demand>(`/homes/${id}/demand`),
        apiFetch<Verdict[]>(`/homes/${id}/verdicts?days=14`),
      ]);
      setDemand(prediction);
      setYesterdayVerdict(verdicts.find((item) => item.day === yesterday()) ?? null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load today’s estimate.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  if (loading) return <section className="home-content"><div className="loading-panel">Learning today’s energy estimate…</div></section>;

  const chartData = demand?.hourly_kw.map((load, hour) => ({
    hour: `${String(hour).padStart(2, "0")}:00`,
    load,
  })) ?? [];
  return (
    <section className="home-content today-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">TODAY’S ESTIMATE</p>
          <h1>Your energy outlook</h1>
          <p className="muted">Hourly estimate based on your appliances, check-ins, and weather.</p>
        </div>
        <div className="today-actions">
          <Link className="button button-quiet" href={`/homes/${id}/dashboard`}>Dashboard</Link>
          <Link className="button button-quiet" href={`/homes/${id}/plan`}>Daily plan</Link>
          <Link className="button button-primary" href={`/homes/${id}/checkin`}>Daily check-in</Link>
        </div>
      </div>
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {demand && (
        <>
          <div className="report-stats today-stats">
            <div className="report-stat"><span>Estimated today</span><strong>{demand.total_kwh.toFixed(1)} kWh</strong></div>
            <div className="report-stat"><span>Likely range</span><strong>{demand.low_kwh.toFixed(1)}–{demand.high_kwh.toFixed(1)} kWh</strong></div>
            <div className="report-stat"><span>Learning</span><strong>{demand.learning_days} days · {demand.confidence} confidence</strong></div>
          </div>
          <section className="report-panel today-panel">
            <div className="panel-heading">
              <div><p className="eyebrow">HOURLY LOAD</p><h2>Estimated grid energy by hour</h2></div>
              <span>kW average</span>
            </div>
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 4, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} interval={3} />
                  <YAxis tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(2)} kW`, "Estimate"]} />
                  <Bar dataKey="load" fill="#438665" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="report-panel today-panel">
            <div className="panel-heading"><div><p className="eyebrow">WHY THIS NUMBER</p><h2>What affects today’s estimate</h2></div></div>
            <ul className="driver-list">{demand.drivers.map((driver) => <li key={driver}>{driver}</li>)}</ul>
            <p className="forecast-source">
              Weather source: {demand.weather_source}{demand.weather_stale ? " · cached data may be stale" : ""}.
              {demand.weather_source === "normal" ? " Typical-weather fallback is approximate." : ""}
            </p>
          </section>
          <section className="report-panel today-panel">
            <div className="panel-heading"><div><p className="eyebrow">YESTERDAY</p><h2>Usage verdict</h2></div></div>
            {yesterdayVerdict ? (
              <>
                <span className={`verdict-badge verdict-${yesterdayVerdict.status}`}>{yesterdayVerdict.status}</span>
                <p className="muted">{yesterdayVerdict.reasons.join(" ")}</p>
              </>
            ) : <p className="muted">No check-in for yesterday yet. Add a meter reading to compare actual use.</p>}
          </section>
        </>
      )}
    </section>
  );
}
