"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiFetch } from "@/lib/api";
import type { Home } from "@/lib/types";
import SignOutButton from "./sign-out-button";

export default function DashboardClient({ email }: { email: string }) {
  const router = useRouter();
  const [homes, setHomes] = useState<Home[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;
    apiFetch<Home[]>("/homes")
      .then((loadedHomes) => {
        if (active) setHomes(loadedHomes);
      })
      .catch((error: unknown) => {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load homes.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function createHome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setBusy(true);
    setErrorMessage("");
    const form = new FormData(formElement);
    try {
      const home = await apiFetch<Home>("/homes", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"),
          city: form.get("city") || null,
          family_size: form.get("family_size")
            ? Number(form.get("family_size"))
            : null,
        }),
      });
      setHomes((existing) => [home, ...existing]);
      formElement.reset();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create home.");
    } finally {
      setBusy(false);
    }
  }

  async function createDemoHome() {
    setBusy(true);
    setErrorMessage("");
    let createdHome: Home | null = null;
    try {
      const currentHomes = await apiFetch<Home[]>("/homes");
      const existingDemo = currentHomes.find(
        (home) => home.name === "Solar Care Demo House",
      );
      if (existingDemo) {
        router.push(`/homes/${existingDemo.id}`);
        return;
      }

      createdHome = await apiFetch<Home>("/homes", {
        method: "POST",
        body: JSON.stringify({
          name: "Solar Care Demo House",
          city: "Lahore",
          family_size: 5,
        }),
      });

      await apiFetch(`/homes/${createdHome.id}/appliances/bulk`, {
        method: "POST",
        body: JSON.stringify({
          items: [
            { room: "Lounge", type: "ac", watts: 1200, duty_factor: 0.6, surge_factor: 2, qty: 1, hours_per_day: 8, is_essential: false, source_tag: "guess", confidence: 0.4 },
            { room: "Lounge", type: "ceiling_fan", watts: 75, duty_factor: 1, surge_factor: 1.5, qty: 3, hours_per_day: 12, is_essential: true, source_tag: "guess", confidence: 0.4 },
            { room: "Kitchen", type: "refrigerator", watts: 150, duty_factor: 0.4, surge_factor: 3, qty: 1, hours_per_day: 24, is_essential: true, source_tag: "guess", confidence: 0.4 },
            { room: "Lounge", type: "led_bulb", watts: 12, duty_factor: 1, surge_factor: 1, qty: 8, hours_per_day: 6, is_essential: true, source_tag: "guess", confidence: 0.4 },
            { room: "Lounge", type: "tv", watts: 75, duty_factor: 1, surge_factor: 1, qty: 1, hours_per_day: 5, is_essential: false, source_tag: "guess", confidence: 0.4 },
            { room: "Lounge", type: "router", watts: 12, duty_factor: 1, surge_factor: 1, qty: 1, hours_per_day: 24, is_essential: true, source_tag: "guess", confidence: 0.4 },
            { room: "Outside", type: "water_pump", watts: 750, duty_factor: 1, surge_factor: 4, qty: 1, hours_per_day: 1, is_essential: false, source_tag: "guess", confidence: 0.4 },
            { room: "Bedroom 1", type: "laptop", watts: 65, duty_factor: 1, surge_factor: 1.2, qty: 1, hours_per_day: 6, is_essential: false, source_tag: "guess", confidence: 0.4 },
            { room: "Kitchen", type: "washing_machine", watts: 400, duty_factor: 1, surge_factor: 2.5, qty: 1, hours_per_day: 1, is_essential: false, source_tag: "guess", confidence: 0.4 },
            { room: "Kitchen", type: "electric_kettle", watts: 1850, duty_factor: 1, surge_factor: 1.2, qty: 1, hours_per_day: 0.3, is_essential: false, source_tag: "guess", confidence: 0.4 },
          ],
        }),
      });
      const demoHome = createdHome;
      if (!demoHome) {
        throw new Error("The demo home was not created.");
      }
      await apiFetch(`/homes/${demoHome.id}/size`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setHomes((existing) => [
        { ...demoHome, appliance_count: 10 },
        ...existing,
      ]);
      router.push(`/homes/${demoHome.id}`);
    } catch (error) {
      if (createdHome) {
        try {
          await apiFetch(`/homes/${createdHome.id}`, { method: "DELETE" });
        } catch {
          setErrorMessage(
            "Demo setup was incomplete, and its partial home could not be removed. Open that home to review it or delete it.",
          );
          return;
        }
      }
      setErrorMessage(error instanceof Error ? error.message : "Could not create demo data.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <Link className="brand-lockup" href="/">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <div className="sign-out-wrap">
          <span className="user-email">{email}</span>
          <SignOutButton />
        </div>
      </header>
      <section className="dashboard-welcome">
        <p className="eyebrow">YOUR SOLAR PLAN</p>
        <h1>Let’s start with your home.</h1>
        <p className="muted">Add a home, then build a picture of the energy you use.</p>
      </section>

      <section className="homes-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">YOUR HOMES</p>
            <h2>Home profiles</h2>
          </div>
          <span className="count-pill">{homes.length} {homes.length === 1 ? "home" : "homes"}</span>
        </div>
        {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
        {loading ? (
          <div className="loading-panel">Loading your homes…</div>
        ) : homes.length ? (
          <div className="home-card-grid">
            {homes.map((home) => (
              <Link className="home-card" href={`/homes/${home.id}`} key={home.id}>
                <span className="home-card-icon" aria-hidden="true">⌂</span>
                <span className="home-card-copy">
                  <strong>{home.name}</strong>
                  <small>{home.city || "City not added"} · {home.appliance_count ?? 0} appliances</small>
                </span>
                <span className="home-card-arrow" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-panel homes-empty">
            <div className="empty-icon" aria-hidden="true">⌂</div>
            <h2>Your first home starts here</h2>
            <p className="muted">Create a profile to begin an appliance list and explore solar options.</p>
          </div>
        )}
      </section>

      <section className="create-home-card">
        <div className="create-home-heading">
          <span className="create-icon" aria-hidden="true">＋</span>
          <div>
            <h2>Add a home</h2>
            <p>Start with a name. You can update these details later.</p>
          </div>
        </div>
        <form className="home-create-form" onSubmit={createHome}>
          <label>
            Home name
            <input maxLength={100} name="name" placeholder="e.g. Family home" required />
          </label>
          <label>
            City
            <input maxLength={100} name="city" placeholder="e.g. Lahore" />
          </label>
          <label>
            Family size
            <input min={1} max={50} name="family_size" placeholder="Optional" type="number" />
          </label>
          <button className="button button-primary" disabled={busy}>
            {busy ? "Creating…" : "Create home"}
          </button>
        </form>
      </section>
      <section className="demo-home-card">
        <div>
          <p className="eyebrow">TRY THE FULL FLOW</p>
          <h2>Explore a sample home</h2>
          <p>
            Add a sample Lahore home with 10 typical appliances and a sizing
            report. You can edit or delete it anytime.
          </p>
        </div>
        <button
          className="button button-quiet"
          disabled={busy}
          onClick={() => void createDemoHome()}
        >
          {busy ? "Preparing sample…" : "Add sample home"}
        </button>
      </section>
    </main>
  );
}
