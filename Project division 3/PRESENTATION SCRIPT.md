# PRESENTATION SCRIPT: Solar Care AI (10 slides, about 10-12 minutes)
Fill every {{...}} with YOUR real numbers from `docs/yolo_eval.md`, `docs/demand_eval.md` and your own tests. If a number is missing, say so; do not invent one.

---
## Slide 1: Title
**Solar Care AI: from "what should I buy?" to "how should I use it?"**
*Say:* "Our project helps a household in Pakistan decide what solar system to buy, and then use it well."

## Slide 2: Problem and users
- Homeowners guess their load; wrong size means wasted money or power cuts.
- Users: households first; installers can use it for a quick estimate.
*Say:* "Most people don't know their watts. We make the first step as easy as taking a photo."

## Slide 3: Solution in one flow
Sign up, add home, photograph appliances, review and correct the list, sizing report, daily check-in, forecast and advice, what-if, printable report.
*Say:* "The user stays in control: every automatic value can be corrected."

## Slide 4: Architecture (use the diagram)
Website (Next.js) → API (FastAPI) → Database (Supabase); weather service; vision AI fallback; trained ML models.
*Say:* "Sizing is exact formulas, because they are explainable. Machine learning is used where formulas cannot learn: recognizing appliances and learning demand patterns."

## Slide 5: MODEL 1, appliance detector (YOLO)
- Data: {{N}} photos from {{K}} homes/shops, {{C}} classes, split by home (test homes never seen in training).
- Result: mAP@0.5 = {{x}}, best class {{name}} ({{ap}}), weakest class {{name}} ({{ap}}).
- Show: confusion matrix + 3 example detections + 1-2 failures.
*Say:* "We trained and tested this ourselves. It finds the appliance type; capacity and watts come from the catalog, the label, or the user, never from a guess presented as fact."

## Slide 6: MODEL 2, demand model
- Idea: predict a "day factor" (1.0 = a normal day for that home) from weather and calendar; multiply by the home's own base level.
- Data: {{public dataset, N days}}; time-ordered split.
- Table: gradient boosting vs "yesterday" vs "7-day average" vs linear model, MAE/MAPE.
*Say:* "We compare against simple baselines so you can see what the model adds. It learned from public data from another country, so each home is personalized by its own check-ins."

## Slide 7: MODEL 3, unusual-day detector
- Isolation Forest on prediction errors; tested on injected anomalies: precision {{x}}, recall {{y}}.
*Say:* "Real labeled anomalies don't exist yet, so we tested with injected ones and we say so."

## Slide 8: Human in the loop and honesty
- Source badges: read from label / matched in catalog / typical guess / entered by you.
- Ranges, not single numbers; consent before images go to AI; each user sees only their data.
- Money savings stay OFF until verified tariffs are entered.

## Slide 9: LIVE DEMO (3 minutes)
See the demo checklist below.

## Slide 10: Limits and next steps
- Evaluation so far: {{real data: how many homes/days}}; the rest is synthetic or public data.
- Next: more homes and weeks of real check-ins, verified catalog, inverter monitoring layer, installable phone app.
*Say:* "We would rather show honest numbers than impressive ones."

---
# DEMO CHECKLIST (rehearse twice)
1. Log in (already signed up). Open "Demo House".
2. Photo: upload 2 prepared photos. Show detected items, source badges, the backend label. Correct one value live.
3. Report: sizing results, three options, the hourly load chart, assumptions.
4. Today page: prediction with range, confidence label, "blended with a learned model".
5. Plan: show 2-3 recommendations and press Done on one.
6. /about-models: show the model cards.
Fallbacks: if the internet or AI service fails, say "hybrid mode falls back"; show the saved screenshots. Keep a recorded screen video as backup. If the live site sleeps (free hosting), open it 5 minutes before.

# LIKELY QUESTIONS AND HONEST ANSWERS
- **"Why not use ChatGPT/Gemini for everything?"** For detection we trained our own model so it runs without per-photo API cost and can be measured; the vision AI is a fallback. Sizing is exact formulas because sizing must be explainable.
- **"How accurate is it?"** Give the table numbers and the test setup (homes not seen in training). Say what the weak classes are.
- **"Where does the capacity/wattage come from?"** Label, catalog, or user. The photo alone cannot tell 1 ton from 1.5 ton, so we never claim that.
- **"Is the demand model trained on Pakistani data?"** Not yet: public data from another country plus per-home personalization. More local data is the next step.
- **"What if the user is wrong or lazy?"** Every value is editable; sanity warnings and the bill comparison catch large mismatches.
- **"Privacy?"** Consent before images go to AI; images not stored; each user can only access their own data.
- **"What did you build vs use?"** Built: detector training, demand and anomaly models, sizing engine, app. Used: YOLO and scikit-learn libraries, Supabase, Open-Meteo weather, a vision AI service as fallback.
- **"Real users?"** Give the honest number ({{households, days}}); if zero, say the pilot is the next step.