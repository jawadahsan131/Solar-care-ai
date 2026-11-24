"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { DragEvent, FormEvent } from "react";

import SourceBadge from "@/components/source-badge";
import { apiFetch } from "@/lib/api";
import type { ApplianceType, DetectedItem, SourceTag } from "@/lib/types";

const ROOMS = [
  "Living room",
  "Bedroom 1",
  "Bedroom 2",
  "Bedroom 3",
  "Bedroom 4",
  "Kitchen",
  "Lounge",
  "Outside",
  "Other",
];
const APPLIANCE_TYPES: ApplianceType[] = [
  "ac", "ceiling_fan", "pedestal_fan", "exhaust_fan", "air_cooler",
  "refrigerator", "deep_freezer", "microwave", "electric_oven",
  "water_dispenser", "electric_kettle", "washing_machine", "iron",
  "geyser", "water_pump", "tv", "desktop_pc", "laptop", "router",
  "ups", "led_bulb", "tube_light", "phone_charger", "vacuum_cleaner", "other",
];

type ReviewItem = DetectedItem & {
  selected: boolean;
  watts: number;
  default_hours: number;
  source_tag: SourceTag;
};

// The API only accepts label, catalog, guess, and user source tags.
const DEMO_ITEMS: DetectedItem[] = [
  {
    type: "ac",
    brand: null,
    model: null,
    capacity_value: 1.5,
    capacity_unit: "ton",
    inverter: true,
    count: 1,
    watts: 1500,
    duty_factor: 0.7,
    surge_factor: 1.2,
    default_hours: 6,
    confidence: 0.5,
    source_tag: "guess",
    label_text: "1.5 Ton Inverter AC",
    notes: "Demo detection sample. Confirm the estimate before adding.",
  },
  {
    type: "ceiling_fan",
    brand: null,
    model: null,
    capacity_value: 56,
    capacity_unit: "inch",
    inverter: null,
    count: 1,
    watts: 75,
    duty_factor: 1,
    surge_factor: 1.3,
    default_hours: 8,
    confidence: 0.5,
    source_tag: "guess",
    label_text: "56-inch Ceiling Fan",
    notes: "Demo detection sample. Confirm the estimate before adding.",
  },
];

export default function AddAppliancesPage({ homeId }: { homeId: string }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [room, setRoom] = useState("Living room");
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [detectionId, setDetectionId] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [usingDemo, setUsingDemo] = useState(false);
  const [addingReviewed, setAddingReviewed] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [editingItems, setEditingItems] = useState<number[]>([]);
  const [consent, setConsent] = useState(false);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [retainPhoto, setRetainPhoto] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [detectionBackendLabel, setDetectionBackendLabel] = useState(
    (process.env.NEXT_PUBLIC_DETECT_BACKEND ?? "vlm") === "yolo"
      ? "our trained model"
      : "vision AI",
  );

  function applyDetectionItems(items: DetectedItem[]) {
    setReviewItems(
      items.map((item) => ({
        ...item,
        selected: true,
        watts: item.watts ?? 100,
        default_hours: item.default_hours ?? 2,
        source_tag: item.source_tag,
      })),
    );
    setEditingItems([]);
  }

  function chooseFile(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file);
    setErrorMessage("");
    setNotice("");
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  async function handlePhoto() {
    const file = selectedFile;
    if (!file) {
      setErrorMessage("Choose a photo first.");
      return;
    }
    if (!consentAccepted && !consent) {
      setErrorMessage("Please read and accept the photo analysis notice to continue.");
      return;
    }

    setDetecting(true);
    setUsingDemo(false);
    setErrorMessage("");
    setNotice("");
    setReviewItems([]);
    setDetectionId("");
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (!consentAccepted) {
      localStorage.setItem("solar-photo-consent", "accepted");
      setConsentAccepted(true);
    }

    const body = new FormData();
    body.set("image", file);
    body.set("room", room);
    body.set("retain_image", String(retainPhoto));
    try {
      const result = await apiFetch<{
        detection_id: string;
        image_path: string | null;
        items: DetectedItem[];
        backend: "our trained model" | "vision AI";
      }>(`/homes/${homeId}/detect`, { method: "POST", body });
      setDetectionBackendLabel(result.backend);
      setDetectionId(result.detection_id);
      applyDetectionItems(result.items);
      if (!result.items.length) setNotice("No appliances found. Add one manually below.");
    } catch {
      setDetectionBackendLabel("demo photo");
      applyDetectionItems(DEMO_ITEMS);
      setNotice("Live AI unavailable. Showing simulated result.");
    } finally {
      setDetecting(false);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function runDemoPhoto() {
    if (detecting) return;
    setDetecting(true);
    setUsingDemo(true);
    setErrorMessage("");
    setNotice("");
    setReviewItems([]);
    setDetectionId("");
    await new Promise((resolve) => window.setTimeout(resolve, 900));
    setDetectionBackendLabel("demo photo");
    applyDetectionItems(DEMO_ITEMS);
    setNotice("Demo photo analyzed. Review the sample estimates before adding them.");
    setDetecting(false);
  }

  function updateReview(index: number, patch: Partial<ReviewItem>) {
    const edited = Object.keys(patch).some((key) => key !== "selected");
    setReviewItems((items) =>
      items.map((item, current) =>
        current === index
          ? { ...item, ...patch, source_tag: edited ? "user" : item.source_tag }
          : item,
      ),
    );
  }

  async function addReviewedItems() {
    if (addingReviewed) return;
    const chosen = reviewItems.filter((item) => item.selected);
    if (!chosen.length) {
      setErrorMessage("Select at least one appliance to add.");
      return;
    }
    setErrorMessage("");
    setAddingReviewed(true);
    try {
      await apiFetch(`/homes/${homeId}/appliances/bulk`, {
        method: "POST",
        body: JSON.stringify({
          items: chosen.map((item) => ({
            room,
            type: item.type,
            brand: item.brand,
            model: item.model,
            capacity_value: item.capacity_value,
            capacity_unit: item.capacity_unit,
            inverter: item.inverter,
            watts: item.watts,
            duty_factor: item.duty_factor,
            surge_factor: item.surge_factor,
            qty: item.count,
            hours_per_day: item.default_hours,
            is_essential: false,
            source_tag: item.source_tag,
            confidence: item.confidence,
            user_verified: true,
          })),
        }),
      });
      setReviewItems([]);
      setNotice(`${chosen.length} appliance ${chosen.length === 1 ? "was" : "were"} added.`);
      if (detectionId) {
        try {
          await apiFetch(`/detections/${detectionId}/finalize`, {
            method: "POST",
            body: JSON.stringify({
              final_items: chosen.map((item) => ({
                type: item.type,
                brand: item.brand,
                model: item.model,
                capacity_value: item.capacity_value,
                capacity_unit: item.capacity_unit,
                inverter: item.inverter,
                count: item.count,
                watts: item.watts,
                duty_factor: item.duty_factor,
                surge_factor: item.surge_factor,
                default_hours: item.default_hours,
                confidence: item.confidence,
                source_tag: item.source_tag,
                label_text: item.label_text,
                bbox: item.bbox,
                notes: item.notes,
              })),
            }),
          });
        } catch {
          setNotice("Appliances were added, but the correction could not be saved for review.");
        }
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not add these appliances.");
    } finally {
      setAddingReviewed(false);
    }
  }

  return (
    <section className="home-content">
      <div className="home-page-heading">
        <div>
          <p className="eyebrow">BUILD YOUR LIST</p>
          <h1>Add appliances</h1>
          <p className="muted">Use a photo or add details yourself. Review every estimate.</p>
        </div>
        <Link className="button button-quiet" href={`/homes/${homeId}`}>View list</Link>
      </div>
      {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
      {notice && <p className="inline-notice" role="status">{notice}</p>}

      <section className="add-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">OPTION 1</p>
            <h2>Take a photo</h2>
          </div>
          <span className="option-chip">Review before adding</span>
        </div>
        <form
          className="photo-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handlePhoto();
          }}
        >
          <label>
            Room
            <select onChange={(event) => setRoom(event.target.value)} value={room}>
              {ROOMS.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <div
              aria-label="Upload an appliance photo"
              className={`flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition ${
                isDragging
                  ? "border-emerald-500 bg-emerald-50"
                  : "border-[var(--line)] bg-white hover:border-emerald-500 hover:bg-emerald-50/50"
              }`}
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setIsDragging(false);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleDrop}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              role="button"
              tabIndex={0}
            >
              <span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
                <svg aria-hidden="true" fill="none" height="28" viewBox="0 0 24 24" width="28">
                  <path d="M4 7.5h3l1.5-2h7l1.5 2h3A1.5 1.5 0 0 1 21.5 9v9a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18V9A1.5 1.5 0 0 1 4 7.5Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
                  <circle cx="12" cy="13" r="3.25" stroke="currentColor" strokeWidth="1.7" />
                </svg>
              </span>
              <strong className="text-base font-bold text-[var(--ink)]">
                Drag &amp; drop a photo of your appliance here, or click to browse.
              </strong>
              <small className="mt-2 text-sm text-[var(--muted)]">
                {selectedFile ? selectedFile.name : "JPEG, PNG, or WebP · up to 8 MB"}
              </small>
            </div>
            <input
              accept="image/*"
              capture="environment"
              className="sr-only"
              name="image"
              onChange={(event) => chooseFile(event.target.files?.[0])}
              ref={fileInputRef}
              type="file"
            />
            <div className="flex flex-col justify-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5">
              <span aria-hidden="true" className="text-2xl">✨</span>
              <strong className="text-sm font-bold text-[var(--ink)]">Ready for a live demo?</strong>
              <p className="text-sm leading-5 text-[var(--muted)]">
                Try the sample photo flow without relying on an AI service.
              </p>
              <button
                className="button button-quiet w-full"
                disabled={detecting}
                onClick={() => void runDemoPhoto()}
                type="button"
              >
                Use Demo Photo
              </button>
            </div>
          </div>

          {!consentAccepted && (
            <label className="privacy-check">
              <input checked={consent} onChange={(event) => setConsent(event.target.checked)} type="checkbox" />
              <span>
                I understand this photo is sent to a third-party AI service to identify appliances.
                Avoid including people, documents, or addresses.
                Review the provider&apos;s current data-use terms before uploading private photos.
              </span>
            </label>
          )}
          <label className="privacy-check retention-check">
            <input checked={retainPhoto} onChange={(event) => setRetainPhoto(event.target.checked)} type="checkbox" />
            <span>Keep a private copy of this photo with my home. Otherwise it is deleted after analysis.</span>
          </label>
          <button className="button button-primary" disabled={detecting || !selectedFile}>
            {detecting ? "Looking for appliances…" : "Analyze photo"}
          </button>
        </form>

        {detecting && (
          <div
            aria-live="polite"
            className="my-5 flex animate-pulse items-center gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-5 text-emerald-950"
            role="status"
          >
            <span className="h-8 w-8 shrink-0 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-700" />
            <span>
              <strong className="block text-base font-bold">
                {usingDemo ? "Preparing demo appliance results..." : "Gemini AI is analyzing your image..."}
              </strong>
              <small className="mt-1 block text-sm text-emerald-800">
                {usingDemo
                  ? "Demo mode is active; no image or API request is needed."
                  : "Identifying appliances and estimating their details."}
              </small>
            </span>
          </div>
        )}

        {reviewItems.length > 0 && (
          <div className="mt-6 rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm sm:p-6">
            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="eyebrow">YOUR REVIEW</p>
                <h3 className="mt-1 text-xl font-bold tracking-tight text-[var(--ink)]">
                  {reviewItems.length} possible {reviewItems.length === 1 ? "appliance" : "appliances"}
                </h3>
              </div>
              <span className="text-sm text-[var(--muted)]">
                Detected by {detectionBackendLabel}. Review every estimate before adding.
              </span>
            </div>
            <div className="grid gap-4">
              {reviewItems.map((item, index) => (
                <article
                  className={`rounded-2xl border p-4 sm:p-5 ${
                    item.selected ? "border-[var(--line)] bg-white" : "border-slate-200 bg-slate-50 opacity-70"
                  }`}
                  key={`${item.type}-${index}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <label className="mt-1 flex items-center" aria-label="Include this appliance">
                        <input
                          checked={item.selected}
                          className="h-4 w-4 accent-emerald-700"
                          onChange={(event) => updateReview(index, { selected: event.target.checked })}
                          type="checkbox"
                        />
                      </label>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-base font-bold capitalize text-[var(--ink)]">
                            {item.label_text || item.type.replaceAll("_", " ")}
                          </h4>
                          <SourceBadge source={item.source_tag} confidence={item.confidence} />
                        </div>
                        <p className="mt-1 text-sm text-[var(--muted)]">
                          Appliance type: {item.type.replaceAll("_", " ")} · {item.brand ? `Brand: ${item.brand}` : "Brand not detected"}
                        </p>
                        <p className="mt-1 text-sm text-[var(--muted)]">
                          Estimated watts: {item.watts} W · Quantity: {item.count}
                        </p>
                      </div>
                    </div>
                    <button
                      className="button button-quiet min-h-9 px-3 text-sm"
                      onClick={() => setEditingItems((items) =>
                        items.includes(index) ? items.filter((itemIndex) => itemIndex !== index) : [...items, index],
                      )}
                      type="button"
                    >
                      {editingItems.includes(index) ? "Done editing" : "Edit"}
                    </button>
                  </div>
                  {editingItems.includes(index) && (
                    <div className="mt-5 grid gap-4 border-t border-[var(--line)] pt-4 sm:grid-cols-2 lg:grid-cols-3">
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Appliance type
                        <select
                          className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal"
                          onChange={(event) => updateReview(index, { type: event.target.value as ApplianceType })}
                          value={item.type}
                        >
                          {APPLIANCE_TYPES.map((type) => (
                            <option key={type} value={type}>{type.replaceAll("_", " ")}</option>
                          ))}
                        </select>
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Brand
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" onChange={(event) => updateReview(index, { brand: event.target.value || null })} value={item.brand ?? ""} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Model
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" onChange={(event) => updateReview(index, { model: event.target.value || null })} value={item.model ?? ""} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Capacity
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" max={100000} min={0} onChange={(event) => updateReview(index, { capacity_value: event.target.value ? Number(event.target.value) : null })} step="any" type="number" value={item.capacity_value ?? ""} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Capacity unit
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" onChange={(event) => updateReview(index, { capacity_unit: event.target.value || null })} placeholder="ton, litre, inch…" value={item.capacity_unit ?? ""} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Inverter
                        <select
                          className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal"
                          onChange={(event) => updateReview(index, {
                            inverter: event.target.value === "unknown" ? null : event.target.value === "yes",
                          })}
                          value={item.inverter === null ? "unknown" : item.inverter ? "yes" : "no"}
                        >
                          <option value="unknown">Unknown / check</option>
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                        </select>
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Estimated watts
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" max={20000} min={0} onChange={(event) => updateReview(index, { watts: Number(event.target.value) })} type="number" value={item.watts} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Quantity
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" max={50} min={1} onChange={(event) => updateReview(index, { count: Number(event.target.value) })} type="number" value={item.count} />
                      </label>
                      <label className="grid gap-1.5 text-sm font-semibold text-[var(--ink)]">Hours / day
                        <input className="min-h-10 rounded-lg border border-[var(--line)] bg-white px-3 font-normal" max={24} min={0} onChange={(event) => updateReview(index, { default_hours: Number(event.target.value) })} step={0.5} type="number" value={item.default_hours} />
                      </label>
                    </div>
                  )}
                  {item.notes && <p className="mt-3 text-sm text-[var(--muted)]">{item.notes}</p>}
                </article>
              ))}
            </div>
            <button
              className="button button-primary mt-5 min-h-12 w-full sm:w-auto"
              disabled={addingReviewed}
              onClick={() => void addReviewedItems()}
              type="button"
            >
              {addingReviewed ? "Adding to inventory…" : "Confirm & Add to Inventory"}
            </button>
          </div>
        )}
      </section>

      <section className="add-section manual-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">OPTION 2</p>
            <h2>Add one manually</h2>
          </div>
          <span className="option-chip">No photo needed</span>
        </div>
        <ManualApplianceForm
          homeId={homeId}
          onAdded={(name) => setNotice(`${name} added to your home.`)}
          room={room}
          setError={setErrorMessage}
        />
        <QuickCounters
          homeId={homeId}
          onAdded={(count) => setNotice(`${count} quick-count appliance types added.`)}
          room={room}
          setError={setErrorMessage}
        />
      </section>
    </section>
  );
}

const QUICK_ITEMS = [
  { type: "led_bulb", label: "LED bulbs", watts: 12, hours: 6, surge: 1 },
  { type: "tube_light", label: "Tube lights", watts: 24, hours: 6, surge: 1 },
  { type: "ceiling_fan", label: "Ceiling fans", watts: 80, hours: 10, surge: 1.3 },
  { type: "phone_charger", label: "Phone chargers", watts: 10, hours: 3, surge: 1 },
] as const;

function QuickCounters({
  homeId,
  room,
  onAdded,
  setError,
}: {
  homeId: string;
  room: string;
  onAdded: (count: number) => void;
  setError: (message: string) => void;
}) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  async function addCounts() {
    const items = QUICK_ITEMS.filter((item) => (counts[item.type] ?? 0) > 0);
    if (!items.length) {
      setError("Choose a quantity for at least one quick-count item.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiFetch(`/homes/${homeId}/appliances/bulk`, {
        method: "POST",
        body: JSON.stringify({
          items: items.map((item) => ({
            room,
            type: item.type,
            watts: item.watts,
            qty: counts[item.type],
            duty_factor: 1,
            surge_factor: item.surge,
            hours_per_day: item.hours,
            is_essential: false,
            source_tag: "guess",
            confidence: 0.35,
            user_verified: false,
          })),
        }),
      });
      onAdded(items.length);
      setCounts({});
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not add these appliances.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="quick-counter-panel">
      <div>
        <p className="eyebrow">QUICK COUNTS</p>
        <h3>Small items in this room</h3>
        <p>Typical values are estimates. You can edit them in your appliance list.</p>
      </div>
      <div className="quick-counter-grid">
        {QUICK_ITEMS.map((item) => (
          <div className="quick-counter" key={item.type}>
            <span><strong>{item.label}</strong><small>{item.watts} W · typical</small></span>
            <div className="counter-controls">
              <button
                aria-label={`Remove one ${item.label}`}
                disabled={(counts[item.type] ?? 0) === 0}
                onClick={() => setCounts((values) => ({
                  ...values,
                  [item.type]: Math.max(0, (values[item.type] ?? 0) - 1),
                }))}
                type="button"
              >−</button>
              <output>{counts[item.type] ?? 0}</output>
              <button
                aria-label={`Add one ${item.label}`}
                onClick={() => setCounts((values) => ({
                  ...values,
                  [item.type]: Math.min(50, (values[item.type] ?? 0) + 1),
                }))}
                type="button"
              >+</button>
            </div>
          </div>
        ))}
      </div>
      <button className="button button-quiet" disabled={busy} onClick={() => void addCounts()} type="button">
        {busy ? "Adding…" : "Add selected counts"}
      </button>
    </div>
  );
}

function ManualApplianceForm({
  homeId,
  room,
  onAdded,
  setError,
}: {
  homeId: string;
  room: string;
  onAdded: (name: string) => void;
  setError: (message: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [searchResults, setSearchResults] = useState<Record<string, unknown>[]>([]);
  const [busy, setBusy] = useState(false);
  const [type, setType] = useState<ApplianceType>("ac");

  useEffect(() => {
    if (!query.trim() || selected) {
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      void apiFetch<Record<string, unknown>[]>(
        `/catalog/search?q=${encodeURIComponent(query)}&limit=8`,
      ).then((results) => {
        if (active) setSearchResults(results);
      }).catch((error: unknown) => {
        if (active) setError(error instanceof Error ? error.message : "Catalog search failed.");
      });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query, selected, setError]);

  async function addManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const applianceType = (selected?.type as ApplianceType | undefined) ?? type;
    setBusy(true);
    setError("");
    try {
      await apiFetch(`/homes/${homeId}/appliances`, {
        method: "POST",
        body: JSON.stringify({
          room,
          type: applianceType,
          brand: (selected?.brand as string | null | undefined) ?? (form.get("brand") || null),
          model: (selected?.model as string | null | undefined) ?? (form.get("model") || null),
          capacity_value: selected?.capacity_value ?? null,
          capacity_unit: selected?.capacity_unit ?? null,
          inverter: selected?.inverter ?? null,
          watts: Number(form.get("watts")),
          qty: Number(form.get("qty")),
          hours_per_day: Number(form.get("hours_per_day")),
          is_essential: form.get("is_essential") === "on",
          source_tag: selected ? "catalog" : "user",
          user_verified: true,
        }),
      });
      formElement.reset();
      setQuery("");
      setSelected(null);
      setSearchResults([]);
      onAdded(applianceType.replaceAll("_", " "));
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not add this appliance.");
    } finally {
      setBusy(false);
    }
  }

  const suggestedHours = Number(selected?.default_hours ?? 2);
  const suggestedWatts = Number(selected?.rated_watts ?? 100);

  return (
    <form className="manual-form" onSubmit={addManual}>
      <div className="catalog-search">
        <label htmlFor="catalog-search">Find a typical appliance</label>
        <input
          autoComplete="off"
          id="catalog-search"
          onChange={(event) => {
            setQuery(event.target.value);
            setSelected(null);
            setSearchResults([]);
          }}
          placeholder="Search appliance type"
          value={query}
        />
        {searchResults.length > 0 && !selected && (
          <ul className="catalog-results">
            {searchResults.map((result, index) => (
              <li key={`${String(result.type)}-${index}`}>
                <button
                  onClick={() => {
                    setSelected(result);
                    setType(result.type as ApplianceType);
                    setQuery(
                      [result.brand, result.model, result.type]
                        .filter(Boolean)
                        .join(" "),
                    );
                    setSearchResults([]);
                  }}
                  type="button"
                >
                  <strong>{String(result.type).replaceAll("_", " ")}</strong>
                  <span>{result.brand ? `${String(result.brand)} ` : ""}{String(result.rated_watts)} W · Typical</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="manual-fields">
        <label>Type
          <select onChange={(event) => {
            setType(event.target.value as ApplianceType);
            setSelected(null);
          }} value={type}>
            {APPLIANCE_TYPES.map((applianceType) => (
              <option key={applianceType} value={applianceType}>{applianceType.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>
        <label>Brand<input defaultValue={String(selected?.brand ?? "")} key={String(selected?.brand ?? "brand")} name="brand" /></label>
        <label>Model<input defaultValue={String(selected?.model ?? "")} key={String(selected?.model ?? "model")} name="model" /></label>
        <label>Running watts
          <input defaultValue={suggestedWatts} key={suggestedWatts} max={20000} min={0} name="watts" required type="number" />
        </label>
        <label>Quantity<input defaultValue={1} max={50} min={1} name="qty" required type="number" /></label>
        <label>Hours / day
          <input defaultValue={suggestedHours} key={suggestedHours} max={24} min={0} name="hours_per_day" required step={0.5} type="number" />
        </label>
      </div>
      <label className="checkbox-label">
        <input name="is_essential" type="checkbox" /> Essential during an outage
      </label>
      <button className="button button-primary" disabled={busy}>
        {busy ? "Adding…" : "Add appliance"}
      </button>
    </form>
  );
}
