from math import floor


START_HOURS = {
    "ac": 15,
    "ceiling_fan": 10,
    "pedestal_fan": 10,
    "exhaust_fan": 18,
    "air_cooler": 12,
    "refrigerator": 0,
    "deep_freezer": 0,
    "microwave": 19,
    "electric_oven": 19,
    "water_dispenser": 0,
    "electric_kettle": 7,
    "washing_machine": 10,
    "iron": 9,
    "geyser": 6,
    "water_pump": 6,
    "tv": 19,
    "desktop_pc": 10,
    "laptop": 10,
    "router": 0,
    "ups": 0,
    "led_bulb": 18,
    "tube_light": 18,
    "phone_charger": 22,
    "vacuum_cleaner": 10,
    "other": 12,
}


def default_hourly_use(type: str, hours_per_day: float) -> list[float]:
    """Build a 24-hour fractional schedule from an appliance type and daily hours."""
    if hours_per_day < 0:
        raise ValueError("hours_per_day cannot be negative")
    if hours_per_day > 24:
        raise ValueError("hours_per_day cannot exceed 24")
    if hours_per_day == 24:
        return [1.0] * 24
    if hours_per_day == 0:
        return [0.0] * 24

    start_hour = START_HOURS.get(type, START_HOURS["other"])
    result = [0.0] * 24
    whole_hours = floor(hours_per_day)
    fraction = hours_per_day - whole_hours
    for offset in range(whole_hours):
        result[(start_hour + offset) % 24] = 1.0
    if fraction:
        result[(start_hour + whole_hours) % 24] = fraction
    return result
