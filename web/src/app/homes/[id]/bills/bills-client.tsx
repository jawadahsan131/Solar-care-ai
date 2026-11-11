"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "@/lib/api";

type Bill = {
  id: string;
  month: string;
  units_kwh: number;
};

type ParsedBill = {
  month: string | null;
  units_kwh: number | null;
  confidence: number;
  warnings: string[];
};

function currentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

export default function BillsPage() {
  const { id } = useParams<{ id: string }>();
  const [bills, setBills] = useState<Bill[]>([]);
  const [month, setMonth] = useState(currentMonth);
  const [units, setUnits] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [parsed, setParsed] = useState<ParsedBill | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const loadBills = useCallback(async () => {
    try {
      const saved = await apiFetch<Bill[]>(`/homes/${id}/bills`);
      setBills(saved);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load bills.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void Promise.resolve().then(loadBills);
  }, [loadBills]);

  const chartBills = useMemo(() => {
    const ordered = [...bills].sort((a, b) => a.month.localeCompare(b.month)).slice(-12);
    const maxUnits = Math.max(1, ...ordered.map((bill) => Number(bill.units_kwh)));
    return ordered.map((bill) => ({
      ...bill,
      height: Math.max(4, (Number(bill.units_kwh) / maxUnits) * 100),
    }));
  }, [bills]);

  async function previewImage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setNotice("");
    if (!image) {
      setErrorMessage("Choose a bill image first.");
      return;
    }
    if (!consent) {
      setErrorMessage("Confirm the image-sharing notice before requesting bill reading.");
      return;
    }
    setBusy(true);
    try {
      const form = new FormData();
      form.set("image", image);
      form.set("consent", "true");
      const result = await apiFetch<{ parsed: ParsedBill }>("/homes/" + id + "/bill", {
        method: "POST",
        body: form,
      });
      setParsed(result.parsed);
      if (result.parsed.month) setMonth(result.parsed.month.slice(0, 7));
      if (result.parsed.units_kwh !== null) setUnits(String(result.parsed.units_kwh));
      setNotice("Review and edit the detected values, then save them below.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not read this bill image.");
    } finally {
      setBusy(false);
    }
  }

  async function saveBill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setErrorMessage("");
    setNotice("");
    try {
      await apiFetch<Bill>(`/homes/${id}/bills`, {
        method: "POST",
        body: JSON.stringify({ month: `${month}-01`, units_kwh: Number(units) }),
      });
      setNotice("Bill saved. Your calibration is now updated.");
      setParsed(null);
      await loadBills();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save this bill.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteBill(bill: Bill) {
    if (!window.confirm(`Delete the ${bill.month.slice(0, 7)} bill?`)) return;
    setErrorMessage("");
    try {
      await apiFetch<void>(`/bills/${bill.id}`, { method: "DELETE" });
      setBills((items) => items.filter((item) => item.id !== bill.id));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not delete this bill.");
    }
  }

  return (
    <section className="home-content bills-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">BILL HISTORY</p>
          <h1>Your electricity bills</h1>
          <p className="muted">Enter a bill manually or review values read from a photo.</p>
        </div>
        <Link className="button button-quiet" href={`/homes/${id}/report`}>View report</Link>
      </div>

      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}

      <section className="report-panel bill-entry-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">OPTIONAL PHOTO READING</p><h2>Review a bill photo</h2></div>
        </div>
        <form className="bill-photo-form" onSubmit={(event) => void previewImage(event)}>
          <label>
            Bill image
            <input
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => setImage(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
          <label className="privacy-check">
            <input
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
              type="checkbox"
            />
            <span>
              I agree to send this image to Google Gemini to read the bill. The app
              does not store the image; Google may process it under its service policy.
            </span>
          </label>
          <button className="button button-quiet" disabled={busy || !image || !consent} type="submit">
            {busy ? "Reading…" : "Read bill photo"}
          </button>
        </form>
        {parsed?.warnings?.length ? (
          <div className="warning-list" aria-label="Bill reading notes">
            {parsed.warnings.map((warning) => <p key={warning}><span aria-hidden="true">!</span>{warning}</p>)}
          </div>
        ) : null}
        {parsed && <p className="muted bill-confidence">Reading confidence: {Math.round(parsed.confidence * 100)}%. Confirm every value before saving.</p>}
      </section>

      <section className="report-panel bill-entry-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">ALWAYS AVAILABLE</p><h2>Enter or correct bill details</h2></div>
        </div>
        <form className="bill-manual-form" onSubmit={(event) => void saveBill(event)}>
          <label>
            Billing month
            <input
              max={currentMonth()}
              onChange={(event) => setMonth(event.target.value)}
              required
              type="month"
              value={month}
            />
          </label>
          <label>
            Units consumed (kWh)
            <input
              max="5000"
              min="0"
              onChange={(event) => setUnits(event.target.value)}
              required
              step="0.01"
              type="number"
              value={units}
            />
          </label>
          <button className="button button-primary" disabled={busy} type="submit">
            {busy ? "Saving…" : "Save bill"}
          </button>
        </form>
      </section>

      <section className="report-panel bill-history-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">SAVED MONTHS</p><h2>Usage history</h2></div>
          <span>kWh per month</span>
        </div>
        {loading ? (
          <p className="muted">Loading your saved bills…</p>
        ) : bills.length === 0 ? (
          <p className="muted">No bills saved yet. Your entries stay editable and can be replaced for the same month.</p>
        ) : (
          <>
            <div className="bill-chart" role="img" aria-label="Bar chart of monthly electricity use">
              {chartBills.map((bill) => (
                <div className="bill-bar-column" key={bill.id} title={`${bill.month.slice(0, 7)}: ${bill.units_kwh} kWh`}>
                  <strong>{Number(bill.units_kwh).toLocaleString()}</strong>
                  <div className="bill-bar-track"><i style={{ height: `${bill.height}%` }} /></div>
                  <span>{bill.month.slice(0, 7)}</span>
                </div>
              ))}
            </div>
            <ul className="bill-list">
              {bills.map((bill) => (
                <li key={bill.id}>
                  <span>{new Date(`${bill.month.slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</span>
                  <strong>{Number(bill.units_kwh).toLocaleString()} kWh</strong>
                  <button className="button button-quiet" onClick={() => void deleteBill(bill)} type="button">Delete</button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
      <p className="disclaimer">
        Calibration uses only monthly kWh, not the bill amount. Image reading can miss details;
        always check and correct the month and units before saving.
      </p>
    </section>
  );
}
