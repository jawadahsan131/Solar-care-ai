import pytest

from app.services.demand import demand_components, fit_personal_scales, predict_demand


def _weather(temp: float) -> dict[str, list[float]]:
    return {
        "temp_c": [temp] * 24,
        "humidity_pct": [50.0] * 24,
        "cloud_pct": [10.0] * 24,
        "ghi_wm2": [0.0] * 24,
    }


def _items() -> list[dict]:
    return [
        {
            "type": "ac",
            "qty": 1,
            "watts": 1200,
            "duty_factor": 0.7,
            "hourly_use": [1.0 if 14 <= hour < 22 else 0.0 for hour in range(24)],
        },
        {
            "type": "refrigerator",
            "qty": 1,
            "watts": 150,
            "duty_factor": 0.4,
            "hourly_use": [1.0] * 24,
        },
    ]


def test_demand_returns_24_hours_and_consistent_totals() -> None:
    result = predict_demand(_items(), _weather(35), cdh_reference=100, n_days=0)

    assert len(result["hourly_kw"]) == 24
    assert sum(result["by_type"].values()) == pytest.approx(result["total_kwh"], abs=0.01)
    assert result["confidence"] == "low"
    assert result["low_kwh"] <= result["total_kwh"] <= result["high_kwh"]


def test_weather_and_user_context_change_demand_explainably() -> None:
    usual = demand_components(_items(), _weather(25), cdh_reference=80)
    hot = demand_components(
        _items(),
        _weather(35),
        cdh_reference=80,
        context={"ac_hours": 10, "guests": True},
    )

    assert hot["potential_kwh"] > usual["potential_kwh"]


def test_outage_reduces_meter_prediction_and_reports_unserved_energy() -> None:
    usual = predict_demand(_items(), _weather(35), cdh_reference=80)
    outage = predict_demand(
        _items(),
        _weather(35),
        cdh_reference=80,
        context={"outage_hours": 6},
    )

    assert outage["total_kwh"] < usual["total_kwh"]
    assert outage["unserved_kwh"] > 0


def test_ridge_fit_recovers_personal_scales() -> None:
    observations = [
        {
            "fixed_kwh": 3.0 + day * 0.05,
            "comfort_kwh": 2.0 + day * 0.25,
            "actual_kwh": (3.0 + day * 0.05) * 0.9 + (2.0 + day * 0.25) * 1.25,
        }
        for day in range(20)
    ]
    result = fit_personal_scales(observations)

    assert abs(result["s_ac"] - 1.25) < 0.15
    assert abs(result["s_other"] - 0.9) < 0.15
