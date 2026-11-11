import sys
from pathlib import Path

from statistics import mean

from app.services.anomaly import verdict_for_day
from app.services.demand import demand_components, fit_personal_scales, robust_residual_std

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.make_synthetic import make_synthetic_dataset


def test_synthetic_model_recovers_scales_and_flags_injected_days() -> None:
    generated = make_synthetic_dataset(days=40)
    rows = generated["rows"]
    training = [row for row in rows[:30] if not row["is_abnormal"]]
    fitted = fit_personal_scales(
        [
            {
                "fixed_kwh": row["fixed_kwh"],
                "comfort_kwh": row["comfort_kwh"],
                "actual_kwh": row["meter_kwh"],
            }
            for row in training
        ]
    )

    assert abs(fitted["s_ac"] - generated["hidden_scales"]["s_ac"]) < 0.15
    assert abs(fitted["s_other"] - generated["hidden_scales"]["s_other"]) < 0.15

    normal_rows = [row for row in rows if not row["is_abnormal"]]
    residuals = [
        row["meter_kwh"]
        - row["fixed_kwh"] * fitted["s_other"]
        - row["comfort_kwh"] * fitted["s_ac"]
        for row in normal_rows
    ]
    residual_std = robust_residual_std(
        residuals,
        [row["predicted_kwh"] for row in normal_rows],
    )
    injected = [row for row in rows if row["is_abnormal"]]
    verdicts = [
        verdict_for_day(
            row["date"],
            row["meter_kwh"],
            row["fixed_kwh"] * fitted["s_other"] + row["comfort_kwh"] * fitted["s_ac"],
            residual_std,
            n_days=30,
        )
        for row in injected
    ]

    assert all(verdict["status"] == "high" for verdict in verdicts)


def test_weather_model_beats_past_week_average_on_holdout_days() -> None:
    generated = make_synthetic_dataset(days=40)
    rows = generated["rows"]
    training = [row for row in rows[:25] if not row["is_abnormal"]]
    fitted = fit_personal_scales(
        [
            {
                "fixed_kwh": row["fixed_kwh"],
                "comfort_kwh": row["comfort_kwh"],
                "actual_kwh": row["meter_kwh"],
            }
            for row in training
        ]
    )
    model_errors = []
    baseline_errors = []
    for index in range(31, len(rows)):
        row = rows[index]
        if row["is_abnormal"]:
            continue
        model_parts = demand_components(
            generated["appliances"],
            row["weather"],
            cdh_reference=55,
        )
        model_prediction = (
            model_parts["fixed_kwh"] * fitted["s_other"]
            + model_parts["comfort_kwh"] * fitted["s_ac"]
        )
        model_errors.append(abs(row["meter_kwh"] - model_prediction))
        baseline = mean(item["meter_kwh"] for item in rows[index - 7 : index])
        baseline_errors.append(abs(row["meter_kwh"] - baseline))

    assert mean(model_errors) < mean(baseline_errors)
