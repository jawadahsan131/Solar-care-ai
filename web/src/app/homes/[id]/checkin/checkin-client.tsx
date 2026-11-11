"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { ApplianceType } from "@/lib/types";

type Checkin = {
  log_date: string;
  ac_hours: number | null;
  outage_hours: number | null;
  guests: boolean | null;
  meter_kwh: number | null;
  appliance_hours: Record<string, number> | null;
};

const applianceTypes: ApplianceType[] = [
  "ac", "air_cooler", "ceiling_fan", "pedestal_fan", "geyser",
  "washing_machine", "iron", "water_pump", "electric_oven", "vacuum_cleaner",
];

function localDay(offsetDays = 0): string {
  const now = new Date();
  now.setDate(now.getDate() + offsetDays);
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export default function CheckinClient() {
  const { id } = useParams<{ id: string }>();
  const [checkins, setCheckins] = useState<Checkin[]>([]);
  const [logDate, setLogDate] = useState(localDay);
  const [acHours, setAcHours] = useState("");
  const [outageHours, setOutageHours] = useState("");
  const [guests, setGuests] = useState(false);
  const [meterKwh, setMeterKwh] = useState("");
  const [applianceType, setApplianceType] = useState<ApplianceType>("ac");
  const [applianceHourValue, setApplianceHourValue] = useState("");
  const [applianceHours, setApplianceHours] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadCheckins = useCallback(async () => {
    try {
      const recent = await apiFetch<Checkin[]>(`/homes/${id}/checkins?days=30`);
      setCheckins(recent);
      if (recent[0]) {
        setAcHours(recent[0].ac_hours === null ? "" : String(recent[0].ac_hours));
        setOutageHours(recent[0].outage_hours === null ? "" : String(recent[0].outage_hours));
        setGuests(Boolean(recent[0].guests));
        setApplianceHours(recent[0].appliance_hours ?? {});
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load check-in history.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void Promise.resolve().then(loadCheckins);
  }, [loadCheckins]);

  const streak = useMemo(() => {
    const dates = new Set(checkins.map((item) => item.log_date));
    let count = 0;
    const cursor = new Date(`${localDay()}T12:00:00`);
    while (dates.has(`${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-${String(cursor.getDate()).padStart(2, "0")}`)) {
      count += 1;
      cursor.setDate(cursor.getDate() - 1);
    }
    return count;
  }, [checkins]);

  async function submitCheckin(event?: FormEvent<HTMLFormElement>, useUsual = false) {
    event?.preventDefault();
    const usual = checkins[0];
    setBusy(true);
    setErrorMessage("");
    setNotice("");
    try {
      const payload = {
        date: logDate,
        ac_hours: Number(acHours) || 0,
        outage_hours: Number(outageHours) || 0,
        guests: useUsual && usual ? Boolean(usual.guests) : guests,
        meter_kwh: meterKwh === "" ? null : Number(meterKwh),
        appliance_hours: Object.keys(applianceHours).length ? applianceHours : null,
      };
      if (useUsual && usual) {
        payload.ac_hours = usual.ac_hours ?? 0;
        payload.outage_hours = usual.outage_hours ?? 0;
        payload.guests = Boolean(usual.guests);
        payload.appliance_hours = usual.appliance_hours;
      }
      await apiFetch(`/homes/${id}/checkin`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setNotice("Check-in saved. Your estimate will use this information.");
      setLogDate(localDay());
      await loadCheckins();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save your check-in.");
    } finally {
      setBusy(false);
    }
  }

  function addApplianceHours() {
    if (applianceHourValue === "") return;
    setApplianceHours((current) => ({ ...current, [applianceType]: Number(applianceHourValue) }));
    setApplianceHourValue("");
  }

  return (
    <section className="home-content checkin-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">DAILY CHECK-IN</p>
          <h1>How was today?</h1>
          <p className="muted">A quick check-in helps the estimate learn your home’s pattern.</p>
        </div>
        <span className="count-pill">{streak} day streak</span>
      </div>
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}
      {loading ? <div className="loading-panel">Loading your recent routine…</div> : (
        <>
          <button
            className="button button-primary usual-button"
            disabled={busy}
            onClick={() => void submitCheckin(undefined, true)}
            type="button"
          >
            Same as usual — save today’s check-in
          </button>
          <section className="report-panel checkin-panel">
            <form className="checkin-form" onSubmit={(event) => void submitCheckin(event)}>
              <label>
                Date
                <input max={localDay()} min={localDay(-7)} onChange={(event) => setLogDate(event.target.value)} type="date" value={logDate} />
              </label>
              <label>
                AC hours today
                <input max="24" min="0" onChange={(event) => setAcHours(event.target.value)} step="0.5" type="number" value={acHours} />
              </label>
              <label>
                Power outage hours
                <input max="24" min="0" onChange={(event) => setOutageHours(event.target.value)} step="0.5" type="number" value={outageHours} />
              </label>
              <label className="checkin-guests">
                <input checked={guests} onChange={(event) => setGuests(event.target.checked)} type="checkbox" />
                <span>Guests at home today</span>
              </label>
              <label>
                Optional meter usage (kWh)
                <input max="5000" min="0" onChange={(event) => setMeterKwh(event.target.value)} placeholder="Leave blank if unknown" step="0.01" type="number" value={meterKwh} />
              </label>
              <details className="checkin-extra">
                <summary>Something different today?</summary>
                <div className="checkin-extra-fields">
                  <label>
                    Appliance
                    <select onChange={(event) => setApplianceType(event.target.value as ApplianceType)} value={applianceType}>
                      {applianceTypes.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
                    </select>
                  </label>
                  <label>
                    Hours today
                    <input max="24" min="0" onChange={(event) => setApplianceHourValue(event.target.value)} step="0.5" type="number" value={applianceHourValue} />
                  </label>
                  <button className="button button-quiet" onClick={addApplianceHours} type="button">Add adjustment</button>
                </div>
                {Object.entries(applianceHours).map(([type, hours]) => (
                  <p className="checkin-adjustment" key={type}>
                    {type.replaceAll("_", " ")}: {hours} h
                    <button onClick={() => setApplianceHours((current) => {
                      const next = { ...current };
                      delete next[type];
                      return next;
                    })} type="button">Remove</button>
                  </p>
                ))}
              </details>
              <button className="button button-primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save check-in"}</button>
            </form>
          </section>
          <p className="disclaimer">
            Outage timing is not recorded, so its effect is estimated across the day. Meter readings are optional and used to improve your model.
          </p>
          <Link className="text-link" href={`/homes/${id}/today`}>See today’s energy estimate</Link>
        </>
      )}
    </section>
  );
}
