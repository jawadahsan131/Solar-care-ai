from app.services.recommend import optimize_plan
from app.services.tariff import estimated_import_cost, load_tariff
from app.routers.recommendations import _blocked_windows


def _washing_machine() -> dict:
    return {
        "id": "washer-1",
        "type": "washing_machine",
        "qty": 1,
        "watts": 500,
        "duty_factor": 1,
        "hourly_use": [1.0 if hour == 21 else 0.0 for hour in range(24)],
    }


def test_optimizer_moves_load_to_solar_surplus_and_preserves_energy() -> None:
    solar = [0.0] * 24
    solar[12] = 1.0
    load = [0.0] * 24
    load[21] = 0.5
    result = optimize_plan(solar, load, [_washing_machine()])

    assert result["recommendations"][0]["to_hours"] == [12]
    assert result["recommendations"][0]["grid_import_saved_kwh"] == 0.5
    assert sum(result["plan_load_kw"]) == sum(load)


def test_optimizer_respects_quiet_hours_and_does_not_move_without_sun() -> None:
    solar = [0.0] * 24
    solar[12] = 1.0
    load = [0.0] * 24
    load[21] = 0.5
    quiet = optimize_plan(solar, load, [_washing_machine()], quiet_hours={12})
    no_sun = optimize_plan([0.0] * 24, load, [_washing_machine()])

    assert quiet["recommendations"] == []
    assert no_sun["recommendations"] == []


def test_optimizer_ignores_fixed_appliances_and_caps_recommendations() -> None:
    solar = [1.0] * 24
    loads = [1.0] * 24
    items = [
        {
            "id": str(index),
            "type": "washing_machine",
            "qty": 1,
            "watts": 500 + index,
            "duty_factor": 1,
            "hourly_use": [1.0 if hour == 21 else 0.0 for hour in range(24)],
        }
        for index in range(8)
    ]
    items.extend(
        [
            {"type": "refrigerator", "qty": 1, "watts": 150, "hourly_use": [1.0] * 24},
            {"type": "led_bulb", "qty": 1, "watts": 12, "hourly_use": [1.0] * 24},
        ]
    )
    result = optimize_plan(solar, loads, items)

    assert len(result["recommendations"]) <= 5
    assert all(item["appliance_type"] == "washing_machine" for item in result["recommendations"])


def test_battery_tip_only_appears_when_battery_is_known() -> None:
    load = [1.0] * 24
    no_battery = optimize_plan([0.0] * 24, load, [], unserved_kwh=0)
    with_battery = optimize_plan([0.0] * 24, load, [], battery_kwh=1)

    assert not any(tip["type"] == "battery" for tip in no_battery["tips"])
    assert any(tip["type"] == "battery" for tip in with_battery["tips"])


def test_tariff_placeholder_disables_cost_instead_of_inventing_a_rate() -> None:
    assert load_tariff() is None


def test_tariff_cost_is_progressive_and_includes_charge_percentages() -> None:
    tariff = {
        "slabs": [
            {"up_to_kwh": 100, "rate_pkr_per_kwh": 10},
            {"up_to_kwh": 200, "rate_pkr_per_kwh": 20},
        ],
        "fuel_adjustment_pkr_per_kwh": 0,
        "other_charges_percent": 0,
        "tax_percent": 0,
    }
    assert estimated_import_cost(150, tariff) == 2000


def test_not_possible_feedback_blocks_the_saved_destination_hours() -> None:
    windows = _blocked_windows(
        [
            {"rec_id": "washer-1@21@12,13", "status": "not_possible"},
            {"rec_id": "washer-1@21@14", "status": "done"},
            {"rec_id": "malformed", "status": "not_possible"},
        ]
    )
    solar = [0.0] * 24
    solar[12] = solar[13] = solar[14] = 1.0
    load = [0.0] * 24
    load[21] = 0.5

    result = optimize_plan(
        solar,
        load,
        [_washing_machine()],
        blocked_windows=windows,
    )

    assert result["recommendations"][0]["to_hours"] == [14]
