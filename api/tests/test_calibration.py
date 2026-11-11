import pytest

from app.services.calibration import (
    calibration_ratio,
    calibration_verdict,
    estimate_monthly_kwh,
    monthly_index,
    overall_calibration_ratio,
    suggest_scaling,
)


def test_estimate_monthly_kwh_uses_daily_x_30_and_seasonal_factor() -> None:
    items = [{"type": "ac", "qty": 1, "watts": 1200, "hourly_use": [0.0] * 24, "hours_per_day": 8}]
    items[0]["hourly_use"] = [1.0 if 15 <= hour <= 22 else 0.0 for hour in range(24)]
    assert estimate_monthly_kwh(items, 1.0) == pytest.approx(9.6 * 30)
    assert estimate_monthly_kwh(items, 1.2) == pytest.approx((9.6 * 30) * 1.2)


def test_ratio_and_verdict_boundaries() -> None:
    assert calibration_ratio(120, 100) == pytest.approx(1.2)
    assert calibration_verdict(1.2)["band"] == "check hours/quantities"
    assert calibration_verdict(1.7)["band"] == "estimate is far from your bill"
    assert calibration_verdict(0.85)["band"] == "good match"


def test_suggest_scaling_never_targets_protected_loads() -> None:
    items = [
        {"type": "ac", "watts": 1200, "hours_per_day": 8},
        {"type": "refrigerator", "watts": 150, "hours_per_day": 24},
        {"type": "led_bulb", "watts": 12, "hours_per_day": 6},
    ]
    proposals = suggest_scaling(items, 1.4)
    assert proposals
    assert all(prop["type"] in {"ac"} for prop in proposals)
    assert all("refrigerator" not in prop["type"] for prop in proposals)
    assert all("led_bulb" not in prop["type"] for prop in proposals)


def test_monthly_index_requires_six_months() -> None:
    assert monthly_index([100, 120, 110, 130, 105, 90]) == pytest.approx(0.824, abs=0.01)
    assert monthly_index([50, 60, 70]) is None


def test_overall_ratio_uses_median_of_last_three_bills() -> None:
    history = [100, 120, 140, 160]
    estimated = 120
    assert overall_calibration_ratio(history, estimated) == pytest.approx(1.1666666667, abs=1e-4)
