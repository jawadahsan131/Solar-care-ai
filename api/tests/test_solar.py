import pytest

from app.services.solar import cdh, daily_summary, pv_curve, pv_kw_per_kwp, sun_hours


def test_pv_curve_is_zero_at_night_and_peaks_at_midday() -> None:
    ghi = [0.0] * 24
    ghi[9:16] = [100, 300, 500, 700, 800, 700, 400]
    temperatures = [25.0] * 24
    curve = pv_curve(ghi, temperatures)

    assert curve[0] == 0
    assert max(curve) == curve[13]


def test_hot_cell_temperature_reduces_pv_output() -> None:
    assert pv_kw_per_kwp(800, 45) < pv_kw_per_kwp(800, 25)


def test_sun_hours_and_cdh_match_hand_calculation() -> None:
    ghi = [0.0] * 24
    ghi[11:13] = [500, 700]
    temperatures = [24.0] * 24
    temperatures[12] = 30

    assert sun_hours(ghi) == pytest.approx(1.2)
    assert cdh(temperatures) == pytest.approx(6.0)


def test_daily_summary_is_explainable() -> None:
    summary = daily_summary(
        {
            "temp_c": [25.0] * 24,
            "humidity_pct": [50.0] * 24,
            "cloud_pct": [10.0] * 24,
            "ghi_wm2": [250.0] * 24,
        }
    )
    assert summary["sun_hours"] == 6.0
    assert "Sunny" in summary["text"]
