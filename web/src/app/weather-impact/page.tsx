"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { Home } from "@/lib/types";
import { createClient } from "@/lib/supabase/client";

type WeatherDay = {
  day: string;
  source: "forecast" | "archive" | "normal";
  stale: boolean;
  normal_city: string | null;
  hourly: {
    temp_c: number[];
    cloud_pct: number[];
    ghi_wm2: number[];
  };
};

type WeatherState = {
  temperatureC: number;
  cloudCoverPct: number;
  condition: string;
  source: WeatherDay["source"] | "simulated";
  normalCity: string | null;
  stale: boolean;
};

const DEMO_WEATHER: WeatherState = {
  temperatureC: 25,
  cloudCoverPct: 80,
  condition: "Cloudy",
  source: "simulated",
  normalCity: null,
  stale: false,
};

function karachiToday(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Karachi",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: string) =>
    parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function karachiCurrentHour(): number {
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Karachi",
      hour: "numeric",
      hourCycle: "h23",
    }).format(new Date()),
  );
  return Math.min(23, Math.max(0, hour));
}

function describeCondition(cloudCoverPct: number, irradiance: number): string {
  if (cloudCoverPct >= 70) return "Cloudy";
  if (cloudCoverPct >= 30) return "Partly Cloudy";
  return irradiance > 20 ? "Sunny" : "Clear";
}

export default function WeatherImpactPage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [loadingWeather, setLoadingWeather] = useState(false);
  const [weather, setWeather] = useState<WeatherState>(DEMO_WEATHER);
  const [usingDemo, setUsingDemo] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadWeather(homeId: string | null) {
      setLoadingWeather(true);
      try {
        if (!homeId) {
          setWeather(DEMO_WEATHER);
          setUsingDemo(true);
          return;
        }

        const home = await apiFetch<Home>(`/homes/${homeId}`);
        if (!active) return;
        if (home.lat == null || home.lon == null) {
          setWeather(DEMO_WEATHER);
          setUsingDemo(true);
          return;
        }

        const forecasts = await apiFetch<WeatherDay[]>(
          `/homes/${homeId}/forecast?date=${karachiToday()}&days=1`,
        );
        if (!active) return;
        const forecast = forecasts[0];
        if (!forecast) {
          setWeather(DEMO_WEATHER);
          setUsingDemo(true);
          return;
        }

        const hour = karachiCurrentHour();
        const temperatureC = forecast.hourly.temp_c[hour];
        const cloudCoverPct = forecast.hourly.cloud_pct[hour];
        const irradiance = forecast.hourly.ghi_wm2[hour];
        if (
          !Number.isFinite(temperatureC) ||
          !Number.isFinite(cloudCoverPct) ||
          !Number.isFinite(irradiance)
        ) {
          setWeather(DEMO_WEATHER);
          setUsingDemo(true);
          return;
        }

        setWeather({
          temperatureC,
          cloudCoverPct,
          condition: describeCondition(cloudCoverPct, irradiance),
          source: forecast.source,
          normalCity: forecast.normal_city,
          stale: forecast.stale,
        });
        setUsingDemo(false);
      } catch {
        if (active) {
          setWeather(DEMO_WEATHER);
          setUsingDemo(true);
        }
      } finally {
        if (active) setLoadingWeather(false);
      }
    }

    async function checkAuthAndLoad() {
      try {
        const {
          data: { user },
          error,
        } = await createClient().auth.getUser();
        if (!active) return;
        if (error || !user) {
          router.replace(`/login?next=${encodeURIComponent("/weather-impact")}`);
          return;
        }
        setCheckingAuth(false);
        const homeId = new URLSearchParams(window.location.search).get("home_id");
        await loadWeather(homeId);
      } catch {
        if (active) {
          router.replace(`/login?next=${encodeURIComponent("/weather-impact")}`);
        }
      }
    }

    void checkAuthAndLoad();
    return () => {
      active = false;
    };
  }, [router]);

  if (checkingAuth) {
    return (
      <main className="app-shell min-h-screen px-4 pb-10">
        <p className="loading-panel" role="status">
          Checking your sign-in…
        </p>
      </main>
    );
  }

  const highImpact = weather.cloudCoverPct > 70;
  const isSunny = weather.condition === "Sunny" || weather.condition === "Clear";
  const impactTitle = highImpact
    ? "High Impact: Solar generation reduced by ~60%"
    : isSunny
      ? "Low Impact: Optimal generation"
      : "Moderate Impact: Some reduction in solar generation";
  const impactTip = isSunny
    ? "Tip: Great day to run heavy appliances like washing machines."
    : highImpact
      ? "Tip: Conserve battery power; heavy cloud cover can reduce solar generation today."
      : "Tip: Shift flexible appliance use toward daylight hours when solar output is available.";
  const sourceDescription =
    weather.source === "normal"
      ? `Typical-weather estimate for ${weather.normalCity ?? "a nearby city"}`
      : weather.source === "archive"
        ? "Open-Meteo historical data"
        : weather.source === "forecast"
          ? "Open-Meteo forecast"
          : "";

  return (
    <main className="app-shell min-h-screen px-4 pb-10">
      <header className="topbar">
        <Link className="brand-lockup" href="/dashboard">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <Link className="button button-quiet" href="/dashboard">
          All homes
        </Link>
      </header>

      <section className="mx-auto grid w-full max-w-5xl gap-5 pt-4 text-[var(--ink)]">
        <header>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--green)]">
            WEATHER + SOLAR
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
            Solar Weather Impact
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            See how today&apos;s weather affects your solar generation and battery
            usage.
          </p>
        </header>

        {loadingWeather && (
          <p className="text-sm text-[var(--muted)]" role="status">
            Loading today&apos;s weather…
          </p>
        )}

        {usingDemo && (
          <p className="text-xs text-[var(--muted)]" role="status">
            (Using simulated weather data for demo)
          </p>
        )}

        {weather.source !== "simulated" && (
          <p className="text-xs text-[var(--muted)]">
            {sourceDescription}
            {weather.stale ? " · cached data may be stale" : ""}
          </p>
        )}

        <div className="grid gap-5 md:grid-cols-2">
          <section className="grid content-start gap-4 rounded-2xl border border-[var(--line)] bg-white p-5 shadow-sm sm:p-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--green)]">
                CURRENT WEATHER
              </p>
              <h2 className="mt-1 text-xl font-bold">Today&apos;s conditions</h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-[var(--paper)] p-4">
                <p className="text-sm text-[var(--muted)]">Temperature</p>
                <p className="mt-1 text-2xl font-bold">
                  {weather.temperatureC.toFixed(1)}°C
                </p>
              </div>
              <div className="rounded-xl bg-[var(--paper)] p-4">
                <p className="text-sm text-[var(--muted)]">Cloud Cover</p>
                <p className="mt-1 text-2xl font-bold">
                  {weather.cloudCoverPct.toFixed(0)}%
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between rounded-xl bg-[var(--paper)] p-4">
              <p className="text-sm text-[var(--muted)]">Weather Condition</p>
              <p className="font-bold">{weather.condition}</p>
            </div>
          </section>

          <section
            aria-live="polite"
            className={`grid content-start gap-4 rounded-2xl border p-5 shadow-sm sm:p-6 ${
              highImpact
                ? "border-amber-300 bg-amber-50 text-amber-950"
                : "border-emerald-200 bg-emerald-50 text-emerald-950"
            }`}
          >
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em]">
                SOLAR IMPACT ANALYSIS
              </p>
              <h2 className="mt-2 text-xl font-bold">{impactTitle}</h2>
            </div>
            <p className="rounded-xl bg-white/70 p-4 text-sm leading-6">
              {impactTip}
            </p>
            <p className="text-xs leading-5 opacity-80">
              Estimate is based on current cloud cover and weather data; actual
              generation varies with system conditions.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
