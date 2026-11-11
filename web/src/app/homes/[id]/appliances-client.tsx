"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "next/navigation";

import SourceBadge from "@/components/source-badge";
import { apiFetch } from "@/lib/api";
import type { Appliance, Home } from "@/lib/types";

export default function HomeAppliancesPage() {
  const { id } = useParams<{ id: string }>();
  const [home, setHome] = useState<Home | null>(null);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const loadData = useCallback(async () => {
    setErrorMessage("");
    try {
      const [homeData, applianceData] = await Promise.all([
        apiFetch<Home>(`/homes/${id}`),
        apiFetch<Appliance[]>(`/homes/${id}/appliances`),
      ]);
      setHome(homeData);
      setAppliances(applianceData);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load this home.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<Home>(`/homes/${id}`),
      apiFetch<Appliance[]>(`/homes/${id}/appliances`),
    ])
      .then(([homeData, applianceData]) => {
        if (active) {
          setHome(homeData);
          setAppliances(applianceData);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load this home.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  const totals = useMemo(() => {
    const energy = appliances.reduce(
      (sum, item) =>
        sum +
        (item.qty * item.watts * item.duty_factor * item.hours_per_day) / 1000,
      0,
    );
    const connected = appliances.reduce(
      (sum, item) => sum + (item.qty * item.watts) / 1000,
      0,
    );
    return {
      energy,
      connected,
      unverified: appliances.filter((item) => !item.user_verified).length,
    };
  }, [appliances]);

  const grouped = useMemo(() => {
    const groups = new Map<string, Appliance[]>();
    for (const appliance of appliances) {
      const room = appliance.room || "Other";
      groups.set(room, [...(groups.get(room) ?? []), appliance]);
    }
    return [...groups.entries()];
  }, [appliances]);

  async function updateAppliance(appliance: Appliance, updates: Record<string, unknown>) {
    setErrorMessage("");
    try {
      await apiFetch<Appliance>(`/appliances/${appliance.id}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
      await loadData();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update appliance.");
    }
  }

  async function deleteAppliance(appliance: Appliance) {
    if (!window.confirm(`Remove this ${appliance.type.replaceAll("_", " ")}?`)) return;
    setErrorMessage("");
    try {
      await apiFetch<void>(`/appliances/${appliance.id}`, { method: "DELETE" });
      setAppliances((items) => items.filter((item) => item.id !== appliance.id));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not remove appliance.");
    }
  }

  return (
    <section className="home-content">
      {loading ? (
        <div className="loading-panel">Loading your appliances…</div>
      ) : (
        <>
          <div className="home-page-heading">
            <div>
              <p className="eyebrow">{home?.city || "HOME PROFILE"}</p>
              <h1>{home?.name || "Your home"}</h1>
              <p className="muted">Check the list. You can edit any value before sizing.</p>
            </div>
            <Link className="button button-primary" href={`/homes/${id}/add`}>＋ Add appliances</Link>
          </div>

          {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}

          <div className="stats-grid">
            <Stat label="Estimated daily use" value={`${totals.energy.toFixed(2)} kWh`} />
            <Stat label="Connected load" value={`${totals.connected.toFixed(2)} kW`} />
            <Stat label="Need your review" value={`${totals.unverified}`} accent={totals.unverified > 0} />
          </div>

          {appliances.length === 0 ? (
            <div className="empty-panel homes-empty">
              <div className="empty-icon" aria-hidden="true">⌁</div>
              <h2>Your appliance list is empty</h2>
              <p className="muted">Add appliances manually or take a photo to get started.</p>
              <Link className="button button-primary" href={`/homes/${id}/add`}>Add your first appliance</Link>
            </div>
          ) : (
            <div className="room-list">
              {grouped.map(([room, roomItems]) => (
                <section className="room-section" key={room}>
                  <div className="room-heading">
                    <h2>{room}</h2>
                    <span>{roomItems.length} {roomItems.length === 1 ? "item" : "items"}</span>
                  </div>
                  <div className="appliance-list">
                    {roomItems.map((appliance) => (
                      <ApplianceCard
                        appliance={appliance}
                        key={appliance.id}
                        onDelete={() => void deleteAppliance(appliance)}
                        onSave={(updates) => void updateAppliance(appliance, updates)}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
          <p className="disclaimer">
            Appliance energy values are estimates. Check labels and your actual usage before making a system decision.
          </p>
        </>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className={`stat-card${accent ? " stat-attention" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ApplianceCard({
  appliance,
  onSave,
  onDelete,
}: {
  appliance: Appliance;
  onSave: (updates: Record<string, unknown>) => void;
  onDelete: () => void;
}) {
  const [scheduleOverride, setScheduleOverride] = useState<number[] | null>(null);
  const title = [
    appliance.type.replaceAll("_", " "),
    appliance.capacity_value != null && appliance.capacity_unit
      ? `${appliance.capacity_value} ${appliance.capacity_unit}`
      : "",
    appliance.inverter ? "inverter" : "",
  ]
    .filter(Boolean)
    .join(" · ");

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const updates: Record<string, unknown> = {
      room: form.get("room") || null,
      brand: form.get("brand") || null,
      model: form.get("model") || null,
      watts: Number(form.get("watts")),
      qty: Number(form.get("qty")),
      hours_per_day: Number(form.get("hours_per_day")),
      is_essential: form.get("is_essential") === "on",
    };
    if (scheduleOverride) {
      delete updates.hours_per_day;
      updates.hourly_use = scheduleOverride;
    }
    onSave(updates);
  }

  function applySchedule(hours: number[]) {
    setScheduleOverride(hours);
  }

  return (
    <article className="appliance-card">
      <div className="appliance-main">
        <span className="appliance-icon" aria-hidden="true">⚡</span>
        <div className="appliance-description">
          <h3>{title}</h3>
          <p>
            {appliance.qty} × {appliance.watts} W · {appliance.hours_per_day.toFixed(1)} h/day
            {appliance.brand ? ` · ${appliance.brand}` : ""}
          </p>
          <div className="appliance-meta">
            <SourceBadge source={appliance.source_tag} confidence={appliance.confidence} />
            {appliance.user_verified ? (
              <span className="verified-mark">✓ Confirmed</span>
            ) : (
              <span className="review-mark">Review values</span>
            )}
          </div>
        </div>
        <strong className="appliance-energy">
          {((appliance.qty * appliance.watts * appliance.duty_factor * appliance.hours_per_day) / 1000).toFixed(2)}
          <small>kWh/day</small>
        </strong>
      </div>
      <details className="edit-details">
        <summary>Edit appliance</summary>
        <form className="appliance-edit-form" onSubmit={submitEdit}>
          <label>Room<input defaultValue={appliance.room ?? ""} name="room" /></label>
          <label>Brand<input defaultValue={appliance.brand ?? ""} name="brand" /></label>
          <label>Model<input defaultValue={appliance.model ?? ""} name="model" /></label>
          <label>Running watts<input defaultValue={appliance.watts} min={0} max={20000} name="watts" type="number" /></label>
          <label>Quantity<input defaultValue={appliance.qty} min={1} max={50} name="qty" type="number" /></label>
          <label>Hours per day<input defaultValue={appliance.hours_per_day} max={24} min={0} name="hours_per_day" onChange={() => setScheduleOverride(null)} step={0.5} type="number" /></label>
          <label className="checkbox-label">
            <input defaultChecked={appliance.is_essential} name="is_essential" type="checkbox" />
            Essential during an outage
          </label>
          <div className="hours-editor">
            <div className="hours-editor-heading">
              <strong>Time-of-day schedule</strong>
              <span>{(scheduleOverride ?? appliance.hourly_use).reduce((sum, hour) => sum + hour, 0).toFixed(1)} hours</span>
            </div>
            <div className="schedule-presets">
              <button onClick={() => applySchedule(scheduleForHours([7, 8, 9, 10, 11, 12]))} type="button">Morning</button>
              <button onClick={() => applySchedule(scheduleForHours([12, 13, 14, 15, 16, 17]))} type="button">Afternoon</button>
              <button onClick={() => applySchedule(scheduleForHours([18, 19, 20, 21, 22, 23]))} type="button">Evening</button>
              <button onClick={() => applySchedule(scheduleForHours([18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6]))} type="button">Night</button>
              <button onClick={() => applySchedule(Array(24).fill(1))} type="button">All day</button>
            </div>
            <div className="hour-cells" aria-label="Toggle appliance use by hour">
              {(scheduleOverride ?? appliance.hourly_use).map((fraction, hour) => (
                <button
                  aria-label={`${String(hour).padStart(2, "0")}:00 ${fraction > 0 ? "on" : "off"}`}
                  aria-pressed={fraction > 0}
                  className={fraction > 0 ? "hour-cell hour-on" : "hour-cell"}
                  key={hour}
                  onClick={() => {
                    const schedule = [...(scheduleOverride ?? appliance.hourly_use)];
                    schedule[hour] = schedule[hour] > 0 ? 0 : 1;
                    applySchedule(schedule);
                  }}
                  type="button"
                >
                  {String(hour).padStart(2, "0")}
                </button>
              ))}
            </div>
          </div>
          <div className="form-actions">
            <button className="button button-primary">Save changes</button>
            <button className="button button-danger" onClick={onDelete} type="button">Remove</button>
          </div>
        </form>
      </details>
    </article>
  );
}

function scheduleForHours(hours: number[]) {
  return Array.from({ length: 24 }, (_, hour) => Number(hours.includes(hour)));
}
