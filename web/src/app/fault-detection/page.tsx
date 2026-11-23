"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type SensorValues = {
  voltage: string;
  current: string;
  power: string;
  temperature: string;
  light: string;
};

type FaultPrediction = {
  fault_type: string;
  confidence: number;
};

const EMPTY_VALUES: SensorValues = {
  voltage: "",
  current: "",
  power: "",
  temperature: "",
  light: "",
};

const NORMAL_SCENARIO: SensorValues = {
  voltage: "12.5",
  current: "5.0",
  power: "62.5",
  temperature: "25",
  light: "800",
};

const FAULT_SCENARIO: SensorValues = {
  voltage: "4.2",
  current: "0.5",
  power: "2.1",
  temperature: "45",
  light: "850",
};

const SENSOR_FIELDS: {
  name: keyof SensorValues;
  label: string;
  unit: string;
}[] = [
  { name: "voltage", label: "Voltage", unit: "V" },
  { name: "current", label: "Current", unit: "A" },
  { name: "power", label: "Power", unit: "W" },
  { name: "temperature", label: "Panel Temperature", unit: "°C" },
  { name: "light", label: "Light", unit: "Lux" },
];

export default function FaultDetectionPage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [values, setValues] = useState<SensorValues>(EMPTY_VALUES);
  const [prediction, setPrediction] = useState<FaultPrediction | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    createClient()
      .auth.getUser()
      .then(({ data, error }) => {
        if (!active) return;
        if (error || !data.user) {
          router.replace(`/login?next=${encodeURIComponent("/fault-detection")}`);
          return;
        }
        setCheckingAuth(false);
      })
      .catch(() => {
        if (active) {
          router.replace(`/login?next=${encodeURIComponent("/fault-detection")}`);
        }
      });

    return () => {
      active = false;
    };
  }, [router]);

  function loadScenario(scenario: SensorValues) {
    setValues(scenario);
    setPrediction(null);
    setErrorMessage("");
  }

  async function submitPrediction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const payload = {
      voltage: Number(values.voltage),
      current: Number(values.current),
      power: Number(values.power),
      temperature: Number(values.temperature),
      light: Number(values.light),
    };
    if (
      Object.values(values).some((value) => !value.trim()) ||
      Object.values(payload).some((value) => !Number.isFinite(value))
    ) {
      setErrorMessage("Enter a valid number for each sensor field.");
      return;
    }

    setErrorMessage("");
    setPrediction(null);
    setSubmitting(true);
    try {
      const result = await apiFetch<FaultPrediction>("/fault/predict", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setPrediction(result);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The prediction service could not respond. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (checkingAuth) {
    return (
      <main className="app-shell min-h-screen px-4 pb-10">
        <p className="loading-panel" role="status">
          Checking your sign-in…
        </p>
      </main>
    );
  }

  const isNormal = prediction?.fault_type.toLowerCase().includes("normal") ?? false;

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

      <section className="mx-auto grid w-full max-w-4xl gap-5 pt-4 text-[var(--ink)]">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--green)]">
              SOLAR CARE AI · LIVE DEMO
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
              Inverter/PV Fault Detection
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
              Enter live telemetry data to predict system health. (Demo based on
              synthetic PV dataset)
            </p>
          </div>
        </header>

        <form
          className="grid gap-5 rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm sm:p-6"
          onSubmit={submitPrediction}
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SENSOR_FIELDS.map((field) => (
              <label className="grid gap-1.5 text-sm font-semibold" key={field.name}>
                {field.label} ({field.unit})
                <input
                  className="min-h-11 rounded-lg border border-[var(--line)] bg-white px-3 text-sm font-normal outline-none focus:border-[var(--green)] focus:ring-2 focus:ring-[var(--green)]/15"
                  name={field.name}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [field.name]: event.target.value,
                    }))
                  }
                  required
                  step="any"
                  type="number"
                  value={values[field.name]}
                />
              </label>
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              className="button button-quiet"
              onClick={() => loadScenario(NORMAL_SCENARIO)}
              type="button"
            >
              Load Normal Scenario
            </button>
            <button
              className="button button-quiet"
              onClick={() => loadScenario(FAULT_SCENARIO)}
              type="button"
            >
              Load Fault Scenario
            </button>
            <button
              className="button button-primary sm:ml-auto"
              disabled={submitting}
              type="submit"
            >
              {submitting ? "Analyzing telemetry..." : "Predict Health"}
            </button>
          </div>
        </form>

        {submitting && (
          <p className="text-sm text-[var(--muted)]" role="status">
            Analyzing telemetry...
          </p>
        )}

        {errorMessage && (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            role="alert"
          >
            {errorMessage}
          </p>
        )}

        {prediction && (
          <section
            aria-live="polite"
            className={`rounded-2xl border p-5 shadow-sm ${
              isNormal
                ? "border-emerald-200 bg-emerald-50 text-emerald-950"
                : "border-amber-300 bg-amber-50 text-amber-950"
            }`}
            aria-label="Fault prediction result"
          >
            <div className="flex items-start gap-3">
              {!isNormal && (
                <span aria-hidden="true" className="text-2xl">
                  ⚠
                </span>
              )}
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em]">
                  Predicted fault type
                </p>
                <h2 className="mt-1 text-2xl font-bold">
                  {prediction.fault_type}
                </h2>
                <p className="mt-2 text-sm font-semibold">
                  Confidence: {(prediction.confidence * 100).toFixed(1)}%
                </p>
                {!isNormal && (
                  <p className="mt-2 text-sm">
                    Potential anomaly detected. Verify sensor readings and consult
                    a qualified installer before taking action.
                  </p>
                )}
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
