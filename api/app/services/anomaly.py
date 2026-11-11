from __future__ import annotations

from typing import Any

from app.services.part2_config import ANOMALY_Z
from app.services.demand import robust_residual_std


def verdict_for_day(
    day: str,
    actual_kwh: float | None,
    expected_kwh: float,
    residual_std: float,
    *,
    n_days: int,
    ac_hours: float | None = None,
    expected_ac_hours: float | None = None,
    appliance_hours: dict[str, float] | None = None,
) -> dict[str, Any]:
    if actual_kwh is None or n_days < 5:
        return {
            "day": day,
            "actual_kwh": actual_kwh,
            "expected_kwh": round(expected_kwh, 2),
            "z": None,
            "status": "unknown",
            "reasons": ["More real usage history is needed before comparing this day."],
        }
    z = (actual_kwh - expected_kwh) / max(residual_std, 0.1 * expected_kwh, 1e-6)
    status = "high" if z > ANOMALY_Z else "low" if z < -ANOMALY_Z else "normal"
    reasons: list[str] = []
    if z > ANOMALY_Z:
        if (
            ac_hours is not None
            and expected_ac_hours is not None
            and ac_hours > expected_ac_hours
        ):
            reasons.append("AC hours were above the usual amount.")
        if appliance_hours:
            reasons.append("You reported appliance hours that differ from usual.")
        reasons.append(
            "Higher than expected for this weather; check for an unlisted appliance or longer use."
        )
    elif z < -ANOMALY_Z:
        reasons.append("Usage was lower than expected for this weather.")
    else:
        reasons.append("Usage was within the expected range for this weather.")
    return {
        "day": day,
        "actual_kwh": round(float(actual_kwh), 2),
        "expected_kwh": round(float(expected_kwh), 2),
        "z": round(z, 2),
        "status": status,
        "reasons": reasons,
    }


def verdicts_for_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    residual_rows = [
        row
        for row in rows
        if row.get("meter_kwh") is not None and row.get("predicted_kwh") is not None
    ]
    residuals = [
        float(row["meter_kwh"]) - float(row["predicted_kwh"])
        for row in residual_rows
    ]
    expected_values = [float(row["predicted_kwh"]) for row in residual_rows]
    residual_std = robust_residual_std(residuals, expected_values)
    n_days = len(residual_rows)
    output = []
    for row in rows:
        context = row.get("appliance_hours") or {}
        output.append(
            verdict_for_day(
                str(row["log_date"]),
                row.get("meter_kwh"),
                float(row.get("predicted_kwh") or 0),
                residual_std,
                n_days=n_days,
                ac_hours=row.get("ac_hours"),
                expected_ac_hours=row.get("expected_ac_hours"),
                appliance_hours=context,
            )
        )
    return output
