# THE NEXT COPILOT PROMPT (use once, in agent mode)

## Before pasting (2 minutes, you do this)
1. Copy `tools/check_status.py` from this kit into your repo as `tools/check_status.py`.
2. Copy `COPILOT_PROMPT.md` from the earlier model kit into your repo as `docs/COPILOT_PROMPT.md` (the prompt points to it).
3. Run `python tools/check_status.py` yourself first and send me `status_report.txt`. I will tell you which steps below you can skip. If you cannot wait, paste the prompt as it is: it decides by itself.

## Prompt
```
You are working in the existing Solar Care AI repo. Do not rewrite what works, do not audit, do not explain. Keep replies short. Do the steps in order.

STEP 0 - STATUS. Run `python tools/check_status.py` and read its output. Use it to decide steps 1-2. If any line says ALERT (secret in git, .env not ignored), fix that FIRST (update .gitignore; if a real key is in a tracked file, tell me to rotate that key, never print the key) and stop for confirmation.

STEP 1 - INTEGRATION (only for items the status marks MISSING in sections 2 and 4). Read docs/COPILOT_PROMPT.md and execute ONLY the TASKS needed for those items. Never overwrite api/app/services/detect_yolo.py, demand_ml.py or demand_features.py with anything other than the files already given; only adapt imports if paths differ.

STEP 2 - MODEL TRANSPARENCY. Add GET /models/info (auth required) returning: detector {backend_setting, weights_present, classes from models/yolo_classes.json}; demand {available, synthetic, n_days, date_range, data label, from models/demand_features.json}; eval_docs {yolo: exists?, demand: exists?}. Add a web page /about-models with three small cards, a link to the app Today page, and a visible "SYNTHETIC - not real accuracy" badge when demand.synthetic is true. No new dependencies.

STEP 3 - HONESTY LABELS. (a) On the photo review screen show which backend detected the items ("our trained model" / "vision AI"). (b) On the Today page show "physics model" or "blended with a learned model". (c) Never display money savings while data/tariff.json has no verified rates. (d) Any result computed from synthetic data must show a SYNTHETIC badge.

STEP 4 - CHECKS. Run pytest, npm run lint, npx tsc --noEmit, npm run build. Show only the final summary line of each plus any failure; fix failures you caused.

STEP 5 - Do NOT commit. List changed file names only. Confirm that no .env value or key was printed or added.
```

## What this prompt deliberately does NOT do (to save your Copilot quota)
- It does not retrain models, label photos or collect data: those are your commands (see `README_FIRST.md`).
- It does not re-audit ownership checks (do the two-account test by hand).
- It does not build new Part 3 / inverter features.