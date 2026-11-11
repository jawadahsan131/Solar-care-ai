from __future__ import annotations

import argparse
import csv
import html
import math
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.services.anomaly import verdict_for_day  # noqa: E402
from app.services.demand import fit_personal_scales, robust_residual_std  # noqa: E402
from make_synthetic import make_synthetic_dataset  # noqa: E402

BEGIN_MARKER = "<!-- BEGIN GENERATED RESULTS -->"
END_MARKER = "<!-- END GENERATED RESULTS -->"


def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _require_columns(
    rows: list[dict[str, str]], required: set[str], label: str
) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [name for name in sorted(required) if not row.get(name, "").strip()]
        if missing:
            raise ValueError(
                f"{label} row {index} is missing required values: {', '.join(missing)}"
            )


def _number(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "").strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must contain a number; received {value!r}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{key} must be finite")
    return parsed


def _error_metrics(actual: list[float], predicted: list[float]) -> dict[str, float | int | None]:
    pairs = [
        (truth, estimate)
        for truth, estimate in zip(actual, predicted, strict=True)
        if truth >= 0
    ]
    if not pairs:
        return {"n": 0, "mae": None, "mape": None}
    absolute = [abs(truth - estimate) for truth, estimate in pairs]
    percentage = [
        error / truth * 100
        for (truth, _), error in zip(pairs, absolute, strict=True)
        if truth > 0
    ]
    return {
        "n": len(pairs),
        "mae": statistics.mean(absolute),
        "mape": statistics.mean(percentage) if percentage else None,
    }


def _synthetic_demand_metrics(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = dataset["rows"]
    actual: list[float] = []
    model: list[float] = []
    yesterday: list[float] = []
    past_week: list[float] = []
    predictions: list[float] = []
    anomalies: list[bool] = []
    anomaly_flags: list[bool] = []

    for index in range(7, len(rows)):
        history = rows[max(0, index - 30) : index]
        fitted = fit_personal_scales(
            [
                {
                    "fixed_kwh": row["fixed_kwh"],
                    "comfort_kwh": row["comfort_kwh"],
                    "actual_kwh": row["meter_kwh"],
                }
                for row in history
            ]
        )
        current = rows[index]
        expected = (
            current["fixed_kwh"] * fitted["s_other"]
            + current["comfort_kwh"] * fitted["s_ac"]
        )
        actual.append(float(current["meter_kwh"]))
        model.append(expected)
        yesterday.append(float(rows[index - 1]["meter_kwh"]))
        past_week.append(
            statistics.mean(float(row["meter_kwh"]) for row in rows[index - 7 : index])
        )
        predictions.append(expected)

    for index in range(7, len(rows)):
        history = rows[max(0, index - 30) : index]
        fitted = fit_personal_scales(
            [
                {
                    "fixed_kwh": row["fixed_kwh"],
                    "comfort_kwh": row["comfort_kwh"],
                    "actual_kwh": row["meter_kwh"],
                }
                for row in history
            ]
        )
        residuals = [
            float(row["meter_kwh"])
            - (
                float(row["fixed_kwh"]) * fitted["s_other"]
                + float(row["comfort_kwh"]) * fitted["s_ac"]
            )
            for row in history
        ]
        expected_history = [
            float(row["fixed_kwh"]) * fitted["s_other"]
            + float(row["comfort_kwh"]) * fitted["s_ac"]
            for row in history
        ]
        residual_std = robust_residual_std(residuals, expected_history)
        current = rows[index]
        expected = (
            float(current["fixed_kwh"]) * fitted["s_other"]
            + float(current["comfort_kwh"]) * fitted["s_ac"]
        )
        verdict = verdict_for_day(
            current["date"],
            float(current["meter_kwh"]),
            expected,
            residual_std,
            n_days=len(history),
        )
        anomalies.append(bool(current["is_abnormal"]))
        anomaly_flags.append(verdict["status"] == "high")

    true_positive = sum(actual_flag and predicted_flag for actual_flag, predicted_flag in zip(anomalies, anomaly_flags, strict=True))
    false_positive = sum(not actual_flag and predicted_flag for actual_flag, predicted_flag in zip(anomalies, anomaly_flags, strict=True))
    false_negative = sum(actual_flag and not predicted_flag for actual_flag, predicted_flag in zip(anomalies, anomaly_flags, strict=True))
    return {
        "model": _error_metrics(actual, model),
        "yesterday": _error_metrics(actual, yesterday),
        "past_week": _error_metrics(actual, past_week),
        "anomaly": {
            "n": len(anomalies),
            "precision": true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0,
            "recall": true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0,
        },
    }


def _real_daily_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    _require_columns(rows, {"date", "actual_kwh", "predicted_kwh"}, "Daily CSV")
    for index, row in enumerate(rows, start=1):
        try:
            date.fromisoformat(row["date"])
        except ValueError as exc:
            raise ValueError(f"Daily CSV row {index} date must use YYYY-MM-DD") from exc
        if (_number(row, "actual_kwh") or 0) < 0 or (_number(row, "predicted_kwh") or 0) < 0:
            raise ValueError(f"Daily CSV row {index} energy values cannot be negative")
    rows = sorted(rows, key=lambda row: row.get("date", ""))
    if len({row["date"] for row in rows}) != len(rows):
        raise ValueError("Daily CSV must contain at most one row per date")
    actual: list[float] = []
    model: list[float] = []
    yesterday: list[float] = []
    past_week: list[float] = []
    for index in range(1, len(rows)):
        truth = _number(rows[index], "actual_kwh")
        prediction = _number(rows[index], "predicted_kwh")
        if truth is None:
            continue
        prior_actuals = [
            _number(row, "actual_kwh")
            for row in rows[max(0, index - 7) : index]
        ]
        values = [value for value in prior_actuals if value is not None]
        if prediction is None or not values:
            continue
        actual.append(truth)
        model.append(prediction)
        yesterday.append(values[-1])
        past_week.append(statistics.mean(values))
    return {
        "model": _error_metrics(actual, model),
        "yesterday": _error_metrics(actual, yesterday),
        "past_week": _error_metrics(actual, past_week),
    }


def _binary_metrics(expected: list[str], predicted: list[str], positive: str) -> dict[str, Any]:
    truth_positive = [value.casefold() == positive.casefold() for value in expected]
    predicted_positive = [value.casefold() == positive.casefold() for value in predicted]
    tp = sum(actual and guess for actual, guess in zip(truth_positive, predicted_positive, strict=True))
    fp = sum(not actual and guess for actual, guess in zip(truth_positive, predicted_positive, strict=True))
    fn = sum(actual and not guess for actual, guess in zip(truth_positive, predicted_positive, strict=True))
    return {
        "n": len(expected),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
    }


def _real_anomaly_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    _require_columns(rows, {"actual_abnormal", "predicted_high"}, "Anomaly CSV")
    truth_values = [row.get("actual_abnormal", "").strip().casefold() for row in rows]
    predicted_values = [row.get("predicted_high", "").strip().casefold() for row in rows]
    accepted = {"1", "true", "yes", "high", "abnormal"}
    rejected = {"0", "false", "no", "normal"}
    if any(value not in accepted | rejected for value in truth_values + predicted_values):
        raise ValueError("Anomaly CSV values must be yes/no, true/false, 1/0, or high/normal")
    expected = ["high" if value in accepted else "normal" for value in truth_values]
    predicted = ["high" if value in accepted else "normal" for value in predicted_values]
    return _binary_metrics(expected, predicted, "high")


def _chart(path: Path, title: str, values: list[tuple[str, float | None]], unit: str) -> None:
    width, height = 760, 340
    left, right, top, bottom = 64, 24, 55, 68
    usable_width = width - left - right
    usable_height = height - top - bottom
    present = [value for _, value in values if value is not None and value >= 0]
    maximum = max(present, default=1.0) or 1.0
    bar_width = min(74, usable_width / max(1, len(values)) * 0.55)
    spacing = usable_width / max(1, len(values))
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="30" fill="#1d3028" font-family="Arial" font-size="18" font-weight="700">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top + usable_height}" x2="{width - right}" y2="{top + usable_height}" stroke="#cbd4c8"/>',
    ]
    for index, (label, value) in enumerate(values):
        x = left + spacing * index + (spacing - bar_width) / 2
        if value is None:
            pieces.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{top + usable_height / 2:.1f}" text-anchor="middle" fill="#718074" font-family="Arial" font-size="11">No data</text>'
            )
        else:
            bar_height = usable_height * max(0.0, value) / maximum
            y = top + usable_height - bar_height
            pieces.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="4" fill="#438665"/>'
            )
            pieces.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{max(top + 14, y - 7):.1f}" text-anchor="middle" fill="#1d3028" font-family="Arial" font-size="11">{value:.1f}{html.escape(unit)}</text>'
            )
        pieces.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 29}" text-anchor="middle" fill="#526357" font-family="Arial" font-size="10">{html.escape(label)}</text>'
        )
    if not present:
        pieces.append(
            f'<text x="{width / 2}" y="{top + usable_height / 2}" text-anchor="middle" fill="#718074" font-family="Arial" font-size="13">No real sample available</text>'
        )
    pieces.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(pieces) + "\n", encoding="utf-8")


def _fmt(value: float | int | None, suffix: str = "") -> str:
    return "Not available" if value is None else f"{value:.2f}{suffix}"


def _build_results(
    synthetic: dict[str, Any],
    daily: dict[str, Any],
    bills: list[dict[str, str]],
    detections: list[dict[str, str]],
    edits: list[dict[str, str]],
    sources: list[dict[str, str]],
    real_anomalies: list[dict[str, str]],
    feedback: list[dict[str, str]],
    user_study: list[dict[str, str]],
    figures: Path,
) -> str:
    _require_columns(
        bills,
        {"estimated_monthly_kwh", "bill_units_kwh"},
        "Bills CSV",
    )
    _require_columns(detections, {"true_type", "predicted_type"}, "Detection CSV")
    _require_columns(edits, {"changed_items", "total_items", "seconds"}, "Edits CSV")
    _require_columns(sources, {"source_tag"}, "Sources CSV")
    _require_columns(feedback, {"status", "kwh_moved"}, "Recommendations CSV")
    _require_columns(
        user_study,
        {"usefulness", "trust", "days_observed"},
        "User study CSV",
    )
    allowed_sources = {"label", "catalog", "guess", "user"}
    if any(row["source_tag"].strip() not in allowed_sources for row in sources):
        raise ValueError("Sources CSV source_tag must be label, catalog, guess, or user")
    for index, row in enumerate(bills, start=1):
        if (_number(row, "estimated_monthly_kwh") or 0) < 0 or (_number(row, "bill_units_kwh") or 0) < 0:
            raise ValueError(f"Bills CSV row {index} energy values cannot be negative")
    for index, row in enumerate(edits, start=1):
        changed = _number(row, "changed_items")
        total = _number(row, "total_items")
        seconds = _number(row, "seconds")
        if changed is None or total is None or seconds is None or min(changed, total, seconds) < 0 or changed > total:
            raise ValueError(f"Edits CSV row {index} must have nonnegative counts, with changed_items <= total_items")
    allowed_statuses = {"done", "skipped", "not_possible"}
    for index, row in enumerate(feedback, start=1):
        amount = _number(row, "kwh_moved")
        status = row["status"].strip().casefold()
        if amount is None or amount < 0 or status not in allowed_statuses:
            raise ValueError(f"Recommendations CSV row {index} has an invalid status or kwh_moved")
        rating = _number(row, "rating")
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError(f"Recommendations CSV row {index} rating must be in 1..5")
        if row.get("date", "").strip():
            try:
                date.fromisoformat(row["date"])
            except ValueError as exc:
                raise ValueError(f"Recommendations CSV row {index} date must use YYYY-MM-DD") from exc
    for index, row in enumerate(user_study, start=1):
        for field in ("usefulness", "trust"):
            rating = _number(row, field)
            if rating is None or not 1 <= rating <= 5:
                raise ValueError(f"User study CSV row {index} {field} rating must be in 1..5")
        observed_days = _number(row, "days_observed")
        if observed_days is None or observed_days < 0:
            raise ValueError(f"User study CSV row {index} days_observed cannot be negative")
        answer = row.get("would_use", "").strip().casefold()
        if answer and answer not in {"yes", "y", "true", "1", "no", "n", "false", "0"}:
            raise ValueError(f"User study CSV row {index} would_use must be yes or no")

    real_bill_actual = [_number(row, "bill_units_kwh") for row in bills]
    real_bill_estimate = [_number(row, "estimated_monthly_kwh") for row in bills]
    bill_pairs = [
        (actual, estimate)
        for actual, estimate in zip(real_bill_actual, real_bill_estimate, strict=True)
        if actual is not None and estimate is not None
    ]
    bill_mape = (
        statistics.mean(abs(actual - estimate) / actual * 100 for actual, estimate in bill_pairs if actual > 0)
        if any(actual > 0 for actual, _ in bill_pairs)
        else None
    )
    bill_within_15 = (
        100
        * sum(abs(actual - estimate) / actual <= 0.15 for actual, estimate in bill_pairs if actual > 0)
        / sum(actual > 0 for actual, _ in bill_pairs)
        if any(actual > 0 for actual, _ in bill_pairs)
        else None
    )
    detection_expected = [row.get("true_type", "") for row in detections]
    detection_predicted = [row.get("predicted_type", "") for row in detections]
    detection_accuracy = (
        sum(a.casefold() == b.casefold() for a, b in zip(detection_expected, detection_predicted, strict=True))
        / len(detections)
        if detections
        else None
    )
    photo_ids = {
        row.get("photo_id", "").strip() for row in detections if row.get("photo_id", "").strip()
    }
    edit_changed = sum(_number(row, "changed_items") or 0 for row in edits)
    edit_total = sum(_number(row, "total_items") or 0 for row in edits)
    edit_effort_pct = 100 * edit_changed / edit_total if edit_total else None
    completion_times = [_number(row, "seconds") for row in edits]
    completion_times = [value for value in completion_times if value is not None]
    done_count = sum(row.get("status", "").casefold() == "done" for row in feedback)
    moved = [_number(row, "kwh_moved") for row in feedback]
    moved = [value for value in moved if value is not None]
    moved_by_day: dict[str, float] = {}
    for row in feedback:
        day = row.get("date", "").strip()
        amount = _number(row, "kwh_moved")
        if day and amount is not None:
            moved_by_day[day] = moved_by_day.get(day, 0.0) + amount
    mean_moved_per_day = (
        statistics.mean(moved_by_day.values())
        if moved_by_day
        else statistics.mean(moved)
        if moved
        else None
    )
    ratings = [_number(row, "rating") for row in feedback]
    ratings = [value for value in ratings if value is not None and 1 <= value <= 5]
    usefulness = [_number(row, "usefulness") for row in user_study]
    trust = [_number(row, "trust") for row in user_study]
    usefulness = [value for value in usefulness if value is not None and 1 <= value <= 5]
    trust = [value for value in trust if value is not None and 1 <= value <= 5]
    would_use_values = [
        row.get("would_use", "").strip().casefold()
        for row in user_study
        if row.get("would_use", "").strip()
    ]
    would_use_pct = (
        100
        * sum(value in {"yes", "y", "true", "1"} for value in would_use_values)
        / len(would_use_values)
        if would_use_values
        else None
    )
    qualifying_households = sum(
        (_number(row, "days_observed") or 0) >= 7 for row in user_study
    )
    confusion_responses = sum(bool(row.get("confusing", "").strip()) for row in user_study)
    real_anomaly = _real_anomaly_metrics(real_anomalies)
    source_counts: dict[str, int] = {}
    for row in sources:
        source = row.get("source_tag", "").strip()
        if source:
            source_counts[source] = source_counts.get(source, 0) + 1

    _chart(
        figures / "daily-demand-error.svg",
        "Daily prediction error (MAPE, lower is better)",
        [
            ("Synthetic model", synthetic["model"]["mape"]),
            ("Synthetic yesterday", synthetic["yesterday"]["mape"]),
            ("Synthetic 7-day", synthetic["past_week"]["mape"]),
            ("Real model", daily["model"]["mape"]),
            ("Real yesterday", daily["yesterday"]["mape"]),
            ("Real 7-day", daily["past_week"]["mape"]),
        ],
        "%",
    )
    _chart(
        figures / "anomaly-detection.svg",
        "Anomaly detection precision and recall",
        [
            ("Synthetic precision", synthetic["anomaly"]["precision"] * 100),
            ("Synthetic recall", synthetic["anomaly"]["recall"] * 100),
            ("Real precision", real_anomaly["precision"] * 100 if real_anomalies else None),
            ("Real recall", real_anomaly["recall"] * 100 if real_anomalies else None),
        ],
        "%",
    )
    _chart(figures / "detection-accuracy.svg", "Appliance type accuracy", [("Real labelled items", detection_accuracy * 100 if detection_accuracy is not None else None)], "%")
    _chart(figures / "bill-calibration.svg", "Bill estimate accuracy (MAPE)", [("Real homes", bill_mape)], "%")
    _chart(figures / "bill-within-15.svg", "Bill estimates within 15%", [("Real home-months", bill_within_15)], "%")
    _chart(figures / "edit-effort.svg", "Appliance items changed", [("Real lists", edit_effort_pct)], "%")
    _chart(figures / "completion-time.svg", "Mean appliance-list completion time", [("Real lists", statistics.mean(completion_times) if completion_times else None)], " s")
    _chart(figures / "source-tags.svg", "Appliance source-tag coverage", [(tag, 100 * count / sum(source_counts.values())) for tag, count in sorted(source_counts.items())] or [("Real items", None)], "%")
    _chart(figures / "detection-class-metrics.svg", "Per-class appliance detection", [(f"{label} P", _binary_metrics(detection_expected, detection_predicted, label)["precision"] * 100) for label in sorted(set(detection_expected))] + [(f"{label} R", _binary_metrics(detection_expected, detection_predicted, label)["recall"] * 100) for label in sorted(set(detection_expected))] or [("Real labels", None)], "%")
    _chart(figures / "recommendation-feedback.svg", "Recommendations marked done", [("Real feedback", 100 * done_count / len(feedback) if feedback else None)], "%")
    _chart(figures / "recommendation-energy.svg", "Estimated kWh moved per day", [("Real feedback", mean_moved_per_day)], " kWh")
    _chart(figures / "recommendation-rating.svg", "Recommendation usefulness rating", [("Real feedback", statistics.mean(ratings) if ratings else None)], " / 5")
    _chart(figures / "user-study.svg", "User study ratings (1-5)", [("Usefulness", statistics.mean(usefulness) if usefulness else None), ("Trust", statistics.mean(trust) if trust else None)], " / 5")

    per_class = []
    for label in sorted(set(detection_expected)):
        class_metrics = _binary_metrics(detection_expected, detection_predicted, label)
        per_class.append(
            f"| {label} | {_fmt(class_metrics['precision'], '%')} | {_fmt(class_metrics['recall'], '%')} | {class_metrics['n']} |"
        )
    if not per_class:
        per_class = ["| No labelled classes supplied | Not available | Not available | 0 |"]

    source_rows = [
        f"| {html.escape(source)} | {100 * count / sum(source_counts.values()):.1f}% | {count} |"
        for source, count in sorted(source_counts.items())
    ] or ["| No source-tag sample supplied | Not available | 0 |"]

    return f"""## Generated evaluation results

This section is refreshed by `python scripts/evaluate.py`. No real household or photo dataset is bundled.

### Daily energy prediction

| Dataset / method | MAE (kWh/day) | MAPE | Evaluated days |
|---|---:|---:|---:|
| Synthetic weather-aware model | {_fmt(synthetic['model']['mae'])} | {_fmt(synthetic['model']['mape'], '%')} | {synthetic['model']['n']} |
| Synthetic yesterday baseline | {_fmt(synthetic['yesterday']['mae'])} | {_fmt(synthetic['yesterday']['mape'], '%')} | {synthetic['yesterday']['n']} |
| Synthetic past-7-day baseline | {_fmt(synthetic['past_week']['mae'])} | {_fmt(synthetic['past_week']['mape'], '%')} | {synthetic['past_week']['n']} |
| Optional real model | {_fmt(daily['model']['mae'])} | {_fmt(daily['model']['mape'], '%')} | {daily['model']['n']} |
| Optional real yesterday baseline | {_fmt(daily['yesterday']['mae'])} | {_fmt(daily['yesterday']['mape'], '%')} | {daily['yesterday']['n']} |
| Optional real past-7-day baseline | {_fmt(daily['past_week']['mae'])} | {_fmt(daily['past_week']['mape'], '%')} | {daily['past_week']['n']} |

![Daily prediction errors](./figs/daily-demand-error.svg)

Evaluation is time-ordered. Synthetic model parameters are fit only on rows preceding each evaluated day; the real CSV is sorted by date and likewise uses only prior actual values for baselines.

### Anomaly detection

| Dataset | Precision | Recall | Evaluated days |
|---|---:|---:|---:|
| Injected synthetic abnormal days | {_fmt(synthetic['anomaly']['precision'] * 100, '%')} | {_fmt(synthetic['anomaly']['recall'] * 100, '%')} | {synthetic['anomaly']['n']} |
| Real user-feedback-labelled days | {_fmt(real_anomaly['precision'] * 100, '%') if real_anomalies else 'Not available'} | {_fmt(real_anomaly['recall'] * 100, '%') if real_anomalies else 'Not available'} | {real_anomaly['n']} |

![Synthetic anomaly metrics](./figs/anomaly-detection.svg)

### Detection and sizing sanity

| Measure | Result | Sample |
|---|---:|---:|
| Real appliance type accuracy | {_fmt(detection_accuracy * 100 if detection_accuracy is not None else None, '%')} | {len(detections)} labelled items / {len(photo_ids)} photos |
| Real bill MAPE | {_fmt(bill_mape, '%')} | {len(bill_pairs)} home-months |
| Real estimates within 15% of bills | {_fmt(bill_within_15, '%')} | {len(bill_pairs)} home-months |
| User-edited appliance fields / items | {_fmt(edit_effort_pct, '%')} | {edit_total:.0f} appliance items |
| Mean list completion time | {_fmt(statistics.mean(completion_times) if completion_times else None, ' seconds')} | {len(completion_times)} lists |

#### Per-class detection

| Appliance type | Precision | Recall | Labelled items |
|---|---:|---:|---:|
{chr(10).join(per_class)}

#### Source-tag coverage

| Source tag | Share | Items |
|---|---:|---:|
{chr(10).join(source_rows)}

![Detection accuracy](./figs/detection-accuracy.svg)

![Bill calibration error](./figs/bill-calibration.svg)

![Bill estimates within 15 percent](./figs/bill-within-15.svg)

![Per-class detection precision and recall](./figs/detection-class-metrics.svg)

![Appliance edit effort](./figs/edit-effort.svg)

![Appliance list completion time](./figs/completion-time.svg)

![Appliance source tags](./figs/source-tags.svg)

### Recommendations and user study

| Measure | Result | Sample |
|---|---:|---:|
| Recommendations marked done | {_fmt(100 * done_count / len(feedback) if feedback else None, '%')} | {len(feedback)} feedback rows |
| Estimated kWh moved per day | {_fmt(mean_moved_per_day, ' kWh/day')} | {len(moved_by_day) if moved_by_day else len(moved)} days/feedback rows |
| Recommendation usefulness rating (1-5) | {_fmt(statistics.mean(ratings) if ratings else None)} | {len(ratings)} ratings |
| User usefulness rating (1-5) | {_fmt(statistics.mean(usefulness) if usefulness else None)} | {len(usefulness)} households |
| User trust rating (1-5) | {_fmt(statistics.mean(trust) if trust else None)} | {len(trust)} households |
| Households with at least 7 observed days | {qualifying_households} | {len(user_study)} households |
| Households reporting something confusing | {confusion_responses} | {len(user_study)} households |
| Would use before buying solar | {_fmt(would_use_pct, '%')} | {len(would_use_values)} responses |

![Recommendation feedback](./figs/recommendation-feedback.svg)

![Estimated energy shifted](./figs/recommendation-energy.svg)

![Recommendation rating](./figs/recommendation-rating.svg)

![User study ratings](./figs/user-study.svg)

"""


def _update_report(path: Path, generated: str) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    block = f"{BEGIN_MARKER}\n{generated}\n{END_MARKER}"
    if BEGIN_MARKER in content and END_MARKER in content:
        start = content.index(BEGIN_MARKER)
        end = content.index(END_MARKER) + len(END_MARKER)
        content = content[:start] + block + content[end:]
    else:
        content = content.rstrip() + "\n\n" + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate synthetic demand data and optional de-identified CSV samples."
    )
    parser.add_argument("--daily-csv", type=Path, help="date,actual_kwh,predicted_kwh")
    parser.add_argument("--bills-csv", type=Path, help="estimated_monthly_kwh,bill_units_kwh")
    parser.add_argument("--detections-csv", type=Path, help="true_type,predicted_type[,photo_id]")
    parser.add_argument("--edits-csv", type=Path, help="changed_items,total_items,seconds")
    parser.add_argument("--sources-csv", type=Path, help="one source_tag row per appliance item")
    parser.add_argument("--anomaly-csv", type=Path, help="actual_abnormal,predicted_high")
    parser.add_argument("--recommendations-csv", type=Path, help="status,kwh_moved[,rating]")
    parser.add_argument("--user-study-csv", type=Path, help="usefulness,trust[,confusing,would_use]")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "evaluation.md")
    parser.add_argument("--figures", type=Path, default=ROOT / "docs" / "figs")
    args = parser.parse_args()

    synthetic_dataset = make_synthetic_dataset(days=40)
    result = _build_results(
        _synthetic_demand_metrics(synthetic_dataset),
        _real_daily_metrics(_read_csv(args.daily_csv)),
        _read_csv(args.bills_csv),
        _read_csv(args.detections_csv),
        _read_csv(args.edits_csv),
        _read_csv(args.sources_csv),
        _read_csv(args.anomaly_csv),
        _read_csv(args.recommendations_csv),
        _read_csv(args.user_study_csv),
        args.figures,
    )
    _update_report(args.output, result)
    print(f"Updated {args.output}")
    print(f"Generated charts in {args.figures}")


if __name__ == "__main__":
    main()
