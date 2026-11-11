Claude

















06 chunk6 frontend · MD
CHUNK 6 — Frontend: homes, photo capture, editable list, sizing report
(Paste MASTER BRIEF first, then this card. Needs chunk 1's web app in the repo. In this chat also paste chunk 5's HANDOFF NOTE (route examples) and web/src/lib/api.ts. If chunk 5 is not finished, build against the routes in MASTER BRIEF section 7 and mock the responses.)

Goal
A mobile-first website where a logged-in user creates a home, photographs appliances, reviews and corrects the detected list, adds missing items manually, and gets a sizing report. The user verifies everything; nothing is silently trusted.

Design rules
Mobile first (phone in portrait is the main device), large tap targets, one task per screen, bottom navigation inside a home: Appliances | Add | Report.
Plain language, English with a clear structure (Urdu labels can come later). Calm green/yellow palette with good contrast.
Every automatic value shows a source badge: Read from label (green), Matched in catalog (blue), Typical value, please confirm (orange), You entered (gray) plus confidence as a small percentage. Orange items must be confirmed before they count as verified.
Loading states everywhere (skeletons), friendly errors (including "server is waking up, this can take up to a minute" for the first call), empty states with a clear next action.
Pages and components (write one file at a time)
/dashboard — list of homes (name, city, number of appliances) + "Add home" form (name, city, family size). Tap a home to open it.
/homes/[id] layout with the bottom navigation.
Appliances tab (/homes/[id])
Grouped by room (collapsible). Each row: icon, "AC 1.5 ton, inverter", qty, hours/day, estimated kWh/day, source badge, verified check.
Tap to edit in a bottom sheet: type (dropdown from /catalog/types), brand, model, capacity + unit, inverter (yes/no/unknown), watts, qty stepper, hours/day slider (0–24 in 0.5 steps), time-of-day editor (24 small buttons or a simple "from–to" selector), essential during outage (toggle), room.
Delete with confirmation. Top summary: total estimated kWh/day, connected kW, count of unverified items, and warnings from the API if any.
Add tab (/homes/[id]/add) with three ways:
Photo: room selector (Living room, Bedroom 1..4, Kitchen, Lounge, Outside, Other); <input type="file" accept="image/*" capture="environment">; consent text on first use (images are analyzed by a third-party AI; delete after processing); upload to /detect; show progress.
Review screen after detection: one card per detected item with all editable fields, qty, hours/day, the source badge and a notes line (e.g. "inverter or not? please confirm"). A checkbox "Looks right" per card and "Add all ticked" button that calls bulk create and then /detections/{id}/finalize with the user's final values. Unticked cards are discarded. Buttons: "Photo was wrong, retry", "Add something that was missed" (opens manual form).
Manual add: search box with catalog autocomplete (/catalog/search), picking a result prefills all fields (source catalog), or choose a type and enter values (source user).
Quick counters for small items per room: LED bulbs, tube lights, ceiling fans, chargers (+/- steppers; creates appliances with typical values, tag guess).
Report tab (/homes/[id]/report)
Button "Calculate my solar system". Calls POST /size.
Result cards: daily kWh, peak kW, inverter kW, panel kW, battery kWh for each option (Off-grid, Hybrid, On-grid) with a one-line explanation of when each fits.
Hourly load chart (Recharts bar/area from load_profile_kw), night/day split, breakdown by appliance (top 8, horizontal bars).
"Assumptions" panel with editable fields (sun hours, battery type: lithium DoD 0.8 / lead-acid DoD 0.5, outage hours, autonomy) and "Recalculate".
Warnings from the API at the top, in yellow.
Disclaimer: "This is an estimate for planning, not an installation design. Please confirm with a qualified installer."
"Print / Save as PDF" button using the browser print dialog with a print stylesheet (proper PDF export comes later).
Shared components: SourceBadge, ApplianceForm, HoursEditor, Stat, EmptyState, Toast.
src/lib/types.ts mirroring the API shapes (DetectedItem, Appliance, SizingResult...).
State and data
Use simple fetch hooks (SWR or React Query). Revalidate after every change.
Keep the 24-hour editor simple: a row of 24 toggle cells plus quick presets (Morning, Afternoon, Evening, Night, All day).
Never block the user: if detection fails, show "Add manually instead" prominently.
Acceptance
 On an actual phone: sign in, create a home, take a photo, review, add 3 detected appliances, edit one value, add one manually, open Report, see numbers, change sun hours and recalculate.
 Orange (guess) items are visually obvious, and after editing they turn into "You entered".
 No horizontal scrolling on a 360 px wide screen; all buttons reachable with one thumb.
 Report numbers match what the API returns (no recalculation in the browser).
 Lighthouse mobile performance and accessibility each at least 80 (nice to have).
Handoff
HANDOFF NOTE: pages built, components list, screens still unfinished, API fields you needed that do not exist yet.


