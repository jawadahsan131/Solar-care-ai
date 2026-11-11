import pytest

from app.services.schedules import default_hourly_use
from app.services.sizing import LoadItem, SizingAssumptions, size_system


def worked_example() -> list[LoadItem]:
    return [
        LoadItem(
            type="ac",
            watts=1200,
            duty_factor=0.6,
            surge_factor=2,
            hourly_use=[1.0 if 13 <= hour <= 20 else 0.0 for hour in range(24)],
        ),
        LoadItem(
            type="ceiling_fan",
            qty=3,
            watts=75,
            surge_factor=1.5,
            hourly_use=[1.0 if 10 <= hour <= 21 else 0.0 for hour in range(24)],
            is_essential=True,
        ),
        LoadItem(
            type="refrigerator",
            watts=150,
            duty_factor=0.4,
            surge_factor=3,
            hourly_use=[1.0] * 24,
            is_essential=True,
        ),
        LoadItem(
            type="led_bulb",
            qty=8,
            watts=12,
            hourly_use=[1.0 if 18 <= hour <= 23 else 0.0 for hour in range(24)],
            is_essential=True,
        ),
    ]


def option(result, kind):
    return next(system for system in result.options if system.kind == kind)


def test_worked_example_matches_master_brief() -> None:
    result = size_system(worked_example())

    assert result.daily_kwh == pytest.approx(10.476)
    assert result.night_kwh == pytest.approx(4.416)
    assert result.running_profile_kw[18] == pytest.approx(1.671)
    assert result.peak_kw == pytest.approx(2.871)
    assert option(result, "on_grid").panel_kw == pytest.approx(2.79)
    assert option(result, "off_grid").panel_kw == pytest.approx(3.21)
    assert option(result, "off_grid").battery_kwh == pytest.approx(6.13)
    assert option(result, "hybrid").battery_kwh == pytest.approx(2.62)
    assert option(result, "hybrid").panel_kw == pytest.approx(3.07)
    assert all(system.inverter_kw == 3.6 for system in result.options)


def test_empty_loads_return_warning_and_zeros() -> None:
    result = size_system([])
    assert result.daily_kwh == 0
    assert "No appliances added yet." in result.warnings
    assert all(system.panel_kw == 0 for system in result.options)


@pytest.mark.parametrize(
    "hourly_use",
    [[0.0] * 23, [0.0] * 23 + [1.1],
     [0.0] * 23 + [-0.1]],
)
def test_invalid_hourly_use_is_rejected(hourly_use: list[float]) -> None:
    with pytest.raises(ValueError):
        LoadItem(type="fan", watts=75, hourly_use=hourly_use)


def test_default_schedule_wraps_and_supports_fractional_hours() -> None:
    ac_schedule = default_hourly_use("ac", 8)
    assert sum(ac_schedule) == pytest.approx(8)
    assert ac_schedule[15:23] == [1.0] * 8
    assert ac_schedule[23] == 0
    assert sum(default_hourly_use("ac", 2.5)) == pytest.approx(2.5)
    assert default_hourly_use("refrigerator", 24) == [1.0] * 24


def test_more_sun_hours_reduce_panel_size() -> None:
    standard = size_system(worked_example())
    sunny = size_system(worked_example(), SizingAssumptions(peak_sun_hours=6))
    assert option(sunny, "on_grid").panel_kw < option(standard, "on_grid").panel_kw


def test_result_is_json_serializable() -> None:
    result = size_system(worked_example())
    assert result.model_dump()["daily_kwh"] == pytest.approx(10.476)


def test_large_inverter_uses_five_kw_steps_and_warns() -> None:
    result = size_system(
        [
            LoadItem(
                type="other",
                watts=18000,
                hourly_use=[1.0] + [0.0] * 23,
            )
        ]
    )
    assert result.options[0].inverter_kw == 25
    assert "Inverter needs custom/3-phase design." in result.warnings
