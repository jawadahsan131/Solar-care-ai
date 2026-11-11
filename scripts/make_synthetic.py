from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.services.demand import demand_components  # noqa: E402

SYNTHETIC_APPLIANCES = [
    {"id": "ac", "type": "ac", "qty": 1, "watts": 1500, "duty_factor": 0.75, "hourly_use": [1.0 if 13 <= hour < 21 else 0.0 for hour in range(24)]},
    {"id": "fan", "type": "ceiling_fan", "qty": 2, "watts": 70, "duty_factor": 1.0, "hourly_use": [1.0 if 8 <= hour < 23 else 0.0 for hour in range(24)]},
    {"id": "fridge", "type": "refrigerator", "qty": 1, "watts": 180, "duty_factor": 0.4, "hourly_use": [1.0] * 24},
    {"id": "lights", "type": "led_bulb", "qty": 8, "watts": 12, "duty_factor": 1.0, "hourly_use": [1.0 if 18 <= hour < 24 else 0.0 for hour in range(24)]},
    {"id": "tv", "type": "tv", "qty": 1, "watts": 100, "duty_factor": 1.0, "hourly_use": [1.0 if 19 <= hour < 23 else 0.0 for hour in range(24)]},
    {"id": "pump", "type": "water_pump", "qty": 1, "watts": 500, "duty_factor": 1.0, "hourly_use": [1.0 if 7 <= hour < 8 else 0.0 for hour in range(24)]},
    {"id": "washing", "type": "washing_machine", "qty": 1, "watts": 500, "duty_factor": 1.0, "hourly_use": [1.0 if 10 <= hour < 11 else 0.0 for hour in range(24)]},
    {"id": "router", "type": "router", "qty": 1, "watts": 15, "duty_factor": 1.0, "hourly_use": [1.0] * 24},
]


def _synthetic_weather(index: int, total_days: int) -> dict[str, list[float]]:
    seasonal_mean = 23 + 12 * (index / max(1, total_days - 1))
    temperatures = [
        seasonal_mean + 7 * math.cos(2 * math.pi * (hour - 15) / 24)
        for hour in range(24)
    ]
    ghi = [
        max(0.0, 700 * math.sin(math.pi * (hour - 6) / 12))
        for hour in range(24)
    ]
    return {
        "temp_c": temperatures,
        "humidity_pct": [50.0] * 24,
        "cloud_pct": [20.0] * 24,
        "ghi_wm2": ghi,
    }


def make_synthetic_dataset(
    *,
    days: int = 40,
    seed: int = 71,
    hidden_s_ac: float = 1.25,
    hidden_s_other: float = 0.9,
) -> dict[str, Any]:
    randomizer = random.Random(seed)
    start = date(2026, 1, 1)
    rows = []
    abnormal_indexes = {days // 2, days * 3 // 4, days - 4}
    for index in range(days):
        weather = _synthetic_weather(index, days)
        components = demand_components(
            SYNTHETIC_APPLIANCES,
            weather,
            cdh_reference=55,
            context={},
        )
        fixed = components["fixed_kwh"]
        comfort = components["comfort_kwh"]
        expected = fixed * hidden_s_other + comfort * hidden_s_ac
        actual = expected * (1 + randomizer.gauss(0, 0.06))
        is_abnormal = index in abnormal_indexes
        if is_abnormal:
            actual *= 1.4
        rows.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "source": "synthetic",
                "weather": weather,
                "fixed_kwh": fixed,
                "comfort_kwh": comfort,
                "predicted_kwh": expected,
                "meter_kwh": actual,
                "is_abnormal": is_abnormal,
            }
        )
    return {
        "source": "synthetic",
        "hidden_scales": {"s_ac": hidden_s_ac, "s_other": hidden_s_other},
        "appliances": SYNTHETIC_APPLIANCES,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate clearly labelled Part 2 synthetic data.")
    parser.add_argument("--days", type=int, default=40)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 15 <= args.days <= 365:
        parser.error("--days must be between 15 and 365")
    generated = make_synthetic_dataset(days=args.days)
    output = json.dumps(generated, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
