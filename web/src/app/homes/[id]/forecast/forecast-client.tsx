"use client";

import {
  ComposedChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { Home } from "@/lib/types";

type City = { name: string; lat: number; lon: number };
type HourlyWeather = {
  temp_c: number[];
  humidity_pct: number[];
  cloud_pct: number[];
  ghi_wm2: number[];
};
type Forecast = {
  day: string;
  source: "forecast" | "archive" | "normal";
  stale: boolean;
  normal_city: string | null;
  hourly: HourlyWeather;
  pv_kw_per_kwp: number[];
  sun_hours: number;
  cdh: number;
  summary: string;
};

function localDay(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function ForecastPage() {
  const { id } = useParams<{ id: string }>();
  const [home, setHome] = useState<Home | null>(null);
  const [cities, setCities] = useState<City[]>([]);
  const [selectedCity, setSelectedCity] = useState("");
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [selectedDay, setSelectedDay] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadForecast = useCallback(async () => {
    setErrorMessage("");
    try {
      const result = await apiFetch<Forecast[]>(
        `/homes/${id}/forecast?date=${localDay()}&days=7`,
      );
      setForecasts(result);
      setSelectedDay((current) => current || result[0]?.day || "");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load the forecast.");
      setForecasts([]);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiFetch<Home>(`/homes/${id}`),
      apiFetch<City[]>("/cities"),
    ])
      .then(([homeData, cityData]) => {
        if (!active) return;
        setHome(homeData);
        setCities(cityData);
        const matchingCity = cityData.find(
          (city) => city.name.toLowerCase() === (homeData.city ?? "").toLowerCase(),
        );
        if (matchingCity) setSelectedCity(matchingCity.name);
      })
      .catch((error: unknown) => {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load your home.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (home?.lat !== null && home?.lat !== undefined && home?.lon !== null && home?.lon !== undefined) {
      void Promise.resolve().then(loadForecast);
    }
  }, [home?.lat, home?.lon, loadForecast]);

  const activeForecast = forecasts.find((item) => item.day === selectedDay) ?? forecasts[0];
  const chartData = useMemo(() => {
    if (!activeForecast) return [];
    return activeForecast.hourly.temp_c.map((temperature, hour) => ({
      hour: `${String(hour).padStart(2, "0")}:00`,
      temperature,
      solar: activeForecast.pv_kw_per_kwp[hour] * (home?.system_kw ?? 1),
    }));
  }, [activeForecast, home?.system_kw]);

  async function saveCity() {
    const city = cities.find((item) => item.name === selectedCity);
    if (!city) return;
    setBusy(true);
    setErrorMessage("");
    setNotice("");
    try {
      const updated = await apiFetch<Home>(`/homes/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ city: city.name, lat: city.lat, lon: city.lon }),
      });
      setHome(updated);
      setNotice(`Weather location saved as ${city.name}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save your city.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshForecast() {
    setBusy(true);
    await loadForecast();
    setBusy(false);
  }

  if (loading) {
    return <section className="home-content"><div className="loading-panel">Loading weather forecast…</div></section>;
  }

  return (
    <section className="home-content forecast-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">WEATHER + SOLAR</p>
          <h1>Forecast for your home</h1>
          <p className="muted">Weather-adjusted solar generation estimate for the next seven days.</p>
        </div>
        <button className="button button-quiet" disabled={busy || !forecasts.length} onClick={() => void refreshForecast()} type="button">
          {busy ? "Updating…" : "Refresh"}
        </button>
      </div>

      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}

      <section className="report-panel forecast-location">
        <div className="panel-heading">
          <div><p className="eyebrow">WEATHER LOCATION</p><h2>{home?.city || "Choose your city"}</h2></div>
        </div>
        <div className="forecast-city-form">
          <label>
            City
            <select onChange={(event) => setSelectedCity(event.target.value)} value={selectedCity}>
              <option value="">Select a Pakistani city</option>
              {cities.map((city) => <option key={city.name} value={city.name}>{city.name}</option>)}
            </select>
          </label>
          <button className="button button-primary" disabled={busy || !selectedCity} onClick={() => void saveCity()} type="button">
            Save location
          </button>
        </div>
        <p className="muted">Coordinates are used to request weather. Forecast estimates are not appliance measurements.</p>
      </section>

      {forecasts.length > 0 && (
        <>
          <div className="forecast-day-list" aria-label="Choose forecast day">
            {forecasts.map((forecast) => (
              <button
                aria-pressed={selectedDay === forecast.day}
                className={`forecast-day-button${selectedDay === forecast.day ? " selected" : ""}`}
                key={forecast.day}
                onClick={() => setSelectedDay(forecast.day)}
                type="button"
              >
                <strong>{new Date(`${forecast.day}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" })}</strong>
                <span>{new Date(`${forecast.day}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
              </button>
            ))}
          </div>

          {activeForecast && (
            <section className="report-panel forecast-panel">
              <div className="forecast-summary-row">
                <div>
                  <p className="eyebrow">{new Date(`${activeForecast.day}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</p>
                  <h2>{activeForecast.summary}</h2>
                </div>
                <div className="forecast-metrics">
                  <strong>{activeForecast.sun_hours.toFixed(1)} h<span>Sun hours</span></strong>
                  <strong>{activeForecast.cdh.toFixed(0)}<span>Cooling degree hours</span></strong>
                </div>
              </div>
              <p className="forecast-source">
                {activeForecast.source === "forecast"
                  ? "Open-Meteo live forecast"
                  : activeForecast.source === "archive"
                    ? "Open-Meteo historical archive"
                    : `Typical-weather estimate for ${activeForecast.normal_city ?? home?.city ?? "nearby city"}`}
                {activeForecast.stale ? " · cached data may be stale" : ""}
              </p>
              <div className="chart-wrap forecast-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                    <CartesianGrid stroke="#e8ecdf" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="hour" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} interval={3} />
                    <YAxis yAxisId="temperature" tick={{ fill: "#718074", fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="solar" orientation="right" tick={{ fill: "#a77a17", fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Line yAxisId="temperature" dataKey="temperature" name="Temperature (°C)" stroke="#438665" strokeWidth={2} dot={false} />
                    <Line yAxisId="solar" dataKey="solar" name={home?.system_kw ? "Solar output (kW)" : "Solar output (kW per kWp)"} stroke="#d2a931" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="muted forecast-assumption">
                Solar line uses {home?.system_kw ? `${home.system_kw} kWp installed` : "one kWp"} and assumes 0.75 performance ratio and 3% soiling loss.
              </p>
            </section>
          )}
        </>
      )}
      <p className="disclaimer">
        Weather may change. Typical-weather fallback values are approximate planning normals, not a local measurement or guarantee.
      </p>
    </section>
  );
}
