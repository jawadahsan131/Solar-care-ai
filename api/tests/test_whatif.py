from app.services.solar import pv_curve
from app.services.whatif import compare_scenarios, simulate_day


def _weather() -> dict[str, list[float]]:
    ghi = [0.0] * 24
    ghi[11:14] = [700.0, 900.0, 700.0]
    return {
        "temp_c": [25.0] * 24,
        "humidity_pct": [50.0] * 24,
        "cloud_pct": [20.0] * 24,
        "ghi_wm2": ghi,
    }


def _monthly_weather() -> list[tuple[int, dict[str, list[float]]]]:
    return [(month, _weather()) for month in range(1, 13)]


def test_larger_panel_does_not_reduce_solar_coverage() -> None:
    weather = _weather()
    solar_per_kw = pv_curve(weather["ghi_wm2"], weather["temp_c"])
    load = [0.0] * 24
    load[12] = 1.0
    essential = list(load)
    smaller = simulate_day(
        [value * 3 for value in solar_per_kw],
        load,
        essential,
        battery_kwh=0,
        inverter_kw=3,
        outage_hours=0,
    )
    larger = simulate_day(
        [value * 5 for value in solar_per_kw],
        load,
        essential,
        battery_kwh=0,
        inverter_kw=5,
        outage_hours=0,
    )

    assert larger["grid_import_kwh"] <= smaller["grid_import_kwh"]


def test_battery_increases_evening_solar_coverage() -> None:
    solar = [0.0] * 24
    solar[12] = 2.0
    load = [0.0] * 24
    load[21] = 1.0
    without_battery = simulate_day(
        solar,
        load,
        load,
        battery_kwh=0,
        inverter_kw=2,
        outage_hours=0,
    )
    with_battery = simulate_day(
        solar,
        load,
        load,
        battery_kwh=2,
        inverter_kw=2,
        outage_hours=0,
    )

    assert without_battery["evening_battery_kwh"] == 0
    assert with_battery["evening_battery_kwh"] > 0
    assert with_battery["grid_import_kwh"] < without_battery["grid_import_kwh"]


def test_outage_coverage_uses_stored_energy_and_never_exceeds_requested_hours() -> None:
    solar = [0.0] * 24
    solar[12] = 2.0
    load = [0.0] * 24
    load[18:22] = [0.2] * 4
    without_battery = simulate_day(
        solar,
        load,
        load,
        battery_kwh=0,
        inverter_kw=2,
        outage_hours=4,
    )
    with_battery = simulate_day(
        solar,
        load,
        load,
        battery_kwh=1,
        inverter_kw=2,
        outage_hours=4,
    )

    assert without_battery["outage_coverage_hours"] == 0
    assert 0 < with_battery["outage_coverage_hours"] <= 4


def test_zero_panel_size_returns_zero_generation_without_errors() -> None:
    result = compare_scenarios(
        _monthly_weather(),
        [],
        panel_kw=0,
        battery_kwh=0,
        inverter_kw=None,
        outage_hours=0,
        cost_per_kw_pkr=None,
        tariff=None,
    )

    assert len(result["scenarios"]) == 3
    assert all(
        scenario["sensitivity"]["base"]["yearly_solar_kwh"] == 0
        for scenario in result["scenarios"]
    )
    assert all(
        scenario["sensitivity"]["base"]["solar_coverage_pct"] == 0
        for scenario in result["scenarios"]
    )
