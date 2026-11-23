#!/usr/bin/env python
"""Read-only status check for the Solar Care AI repo.

Run from the repo root:   python tools/check_status.py
It prints a short table (OK / MISSING / WARN) and saves it to status_report.txt.
SAFE: it never prints the contents of .env files or any secret value. It only prints file names and yes/no.
Send the output (or the file) to Claude so it knows exactly where you are.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
LINES: list[str] = []


def out(tag: str, msg: str) -> None:
    line = f"[{tag:<7}] {msg}"
    LINES.append(line)
    print(line)


def head(title: str) -> None:
    LINES.append("")
    print()
    out("-----", title)


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def read(rel: str) -> str:
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def check(rel: str, why: str = "") -> bool:
    ok = exists(rel)
    out("OK" if ok else "MISSING", f"{rel}" + (f"  ({why})" if why and not ok else ""))
    return ok


def git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def grep_any(globs: list[str], needle: str) -> bool:
    for g in globs:
        for p in ROOT.glob(g):
            if p.is_file() and needle in p.read_text(encoding="utf-8", errors="ignore"):
                return True
    return False


def main() -> None:
    print(f"Repo: {ROOT}\n")

    head("1. APP BASICS")
    check("api/app/main.py"); check("web/package.json"); check("sql/schema.sql")
    check("sql/migrations/002_part2.sql", "Part 2 tables")
    tests = list((ROOT / "api" / "tests").glob("test_*.py")) if exists("api/tests") else []
    out("OK" if tests else "MISSING", f"API test files: {len(tests)}")
    cat = ROOT / "data/catalog/appliance_catalog.csv"
    if cat.exists():
        n = max(0, sum(1 for _ in cat.open(encoding="utf-8", errors="ignore")) - 1)
        out("OK" if n >= 60 else "WARN", f"catalog rows: {n} (aim for 60+; values are typical, verify on real labels)")
    else:
        out("MISSING", "data/catalog/appliance_catalog.csv")

    head("2. MODEL CODE (the ML kit)")
    for rel in ["ml/yolo/train.py", "ml/yolo/make_dataset.py", "ml/demand/train_demand.py", "api/app/services/demand_features.py",
                "api/app/services/demand_ml.py", "api/tests/test_ml_glue.py"]:
        check(rel, "copy from the model kit")
    dy = read("api/app/services/detect_yolo.py")
    if not dy:
        out("MISSING", "api/app/services/detect_yolo.py")
    elif "def detect_raw" in dy:
        out("OK", "detect_yolo.py is the real implementation")
    else:
        out("WARN", "detect_yolo.py looks like the old stub: replace it with the kit version")

    head("3. TRAINED MODEL FILES")
    for rel in ["models/best.pt", "models/yolo_classes.json", "models/demand_model.joblib", "models/anomaly_model.joblib",
                "models/demand_features.json"]:
        check(rel, "train it, see README_FIRST")
    meta = read("models/demand_features.json")
    if meta:
        out("WARN" if '"synthetic": true' in meta else "OK",
            "demand model is SYNTHETIC (must not be shown as real accuracy)" if '"synthetic": true' in meta else "demand model is not marked synthetic")

    head("4. INTEGRATION INTO THE APP")
    svc = ["api/app/**/*.py"]
    out("OK" if grep_any(svc, "hybrid") else "MISSING", "detect backend supports 'hybrid'")
    out("OK" if grep_any(svc, "demand_ml") else "MISSING", "API imports demand_ml (ensemble / anomaly)")
    out("OK" if grep_any(["web/src/**/*.tsx"], "about-models") or exists("web/src/app/about-models") else "MISSING", "web /about-models page")

    head("5. EVIDENCE DOCS")
    for rel in ["docs/yolo_eval.md", "docs/demand_eval.md"]:
        txt = read(rel)
        if not txt:
            out("MISSING", rel)
        else:
            flags = [w for w in ("SYNTHETIC", "LEAKY") if w in txt]
            out("WARN" if flags else "OK", f"{rel}" + (f"  contains: {', '.join(flags)} (say so in the report)" if flags else ""))
    check("docs/evaluation.md"); check("README.md"); check("docs/HANDOFF.md")

    head("6. YOLO DATA (local photos)")
    raw = ROOT / "data/yolo_raw"
    if raw.exists():
        homes = [d for d in raw.iterdir() if d.is_dir()]
        imgs = labeled = 0
        for d in homes:
            for p in d.rglob("*"):
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    imgs += 1
                    labeled += p.with_suffix(".txt").exists()
        out("OK" if len(homes) >= 5 and labeled >= 400 else "WARN",
            f"home folders: {len(homes)} | images: {imgs} | labeled: {labeled}  (target: 5+ homes, 400-600+ labeled images)")
    else:
        out("MISSING", "data/yolo_raw (no local photos yet)")
    check("data/yolo/data.yaml", "run make_dataset.py")

    head("7. SAFETY AND GIT")
    for envf in ["api/.env", "web/.env.local"]:
        if exists(envf):
            r = git("check-ignore", envf)
            out("OK" if r else "ALERT", f"{envf} is {'ignored by git' if r else 'NOT ignored: add it to .gitignore NOW'}")
        else:
            out("INFO", f"{envf} not found (fine if you have not set up env yet)")
    tracked = (git("ls-files") or "").splitlines()
    bad_env = [t for t in tracked if re.search(r"(^|/)\.env(\.|$)", t) and not t.endswith((".example", ".sample"))]
    out("ALERT" if bad_env else "OK", f"tracked .env files: {bad_env if bad_env else 'none'}")

    patterns = {
        "JWT-like token (Supabase key?)": re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
        "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
        "Supabase secret key": re.compile(r"sb_secret_[A-Za-z0-9_-]{10,}"),
        "generic sk- key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    }
    hits = []
    for t in tracked:
        p = ROOT / t
        try:
            if not p.is_file() or p.stat().st_size > 1_000_000 or p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pt", ".joblib", ".zip", ".mp4", ".pdf"}:
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, rx in patterns.items():
            if rx.search(txt):
                hits.append(f"{t} ({name})")   # file name and kind only, NEVER the value
    out("ALERT" if hits else "OK", f"possible secrets in tracked files: {hits if hits else 'none found'}")
    gi = read(".gitignore")
    gi_lines = {l.strip() for l in gi.splitlines()}
    env_rule = bool(gi_lines & {".env", "*.env", ".env*", "**/.env", "api/.env"})   # exact lines: ".env.local" alone does not cover api/.env
    out("OK" if env_rule else "WARN", ".gitignore has a rule covering '.env' files")
    for needle in ["models/*.pt", "data/yolo_raw", "runs/"]:
        out("OK" if needle in gi else "WARN", f".gitignore has '{needle}'")

    st = git("status", "--short")
    if st is None:
        out("INFO", "not a git repo or git not installed")
    else:
        n = len([l for l in st.splitlines() if l.strip()])
        out("INFO", f"uncommitted changes: {n} file(s)")
        last = (git("log", "-1", "--oneline") or "").strip()
        out("INFO", f"last commit: {last or 'none yet'}")

    print()
    summary = {k: sum(1 for l in LINES if l.startswith(f"[{k:<7}]")) for k in ("OK", "MISSING", "WARN", "ALERT")}
    out("SUMMARY", " | ".join(f"{k}={v}" for k, v in summary.items()))
    (ROOT / "status_report.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\nSaved status_report.txt  ->  send it (or this output) to Claude. It contains no secrets.")


if __name__ == "__main__":
    main()