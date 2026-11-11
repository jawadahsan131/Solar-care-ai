from collections.abc import Sequence

from app.services.part2_config import (
    COMFORT_SETPOINT_C,
    PV_PERFORMANCE_RATIO,
    PV_TEMP_COEFF,
    SOILING_LOSS,
)


def pv_kw_per_kwp(
    ghi_wm2: float,
    temp_c: float,
    soiling_loss: float = SOILING_LOSS,
) -> float:
    ghi = max(0.0, float(ghi_wm2))
    cell_temp = float(temp_c) + 20.0 * (ghi / 800.0)
    temperature_factor = max(0.0, 1 + PV_TEMP_COEFF * (cell_temp - 25))
    cleanliness_factor = min(1.0, max(0.0, 1 - soiling_loss))
    return max(0.0, ghi / 1000 * PV_PERFORMANCE_RATIO * temperature_factor * cleanliness_factor)


def pv_curve(
    ghi_series: Sequence[float],
    temp_series: Sequence[float],
    soiling_loss: float = SOILING_LOSS,
) -> list[float]:
    if len(ghi_series) != 24 or len(temp_series) != 24:
        raise ValueError("GHI and temperature series must contain 24 hourly values")
    return [
        pv_kw_per_kwp(ghi, temperature, soiling_loss)
        for ghi, temperature in zip(ghi_series, temp_series, strict=True)
    ]


def sun_hours(ghi_series: Sequence[float]) -> float:
    if len(ghi_series) != 24:
        raise ValueError("GHI series must contain 24 hourly values")
    return round(sum(max(0.0, float(value)) for value in ghi_series) / 1000, 2)


def cdh(
    temp_series: Sequence[float],
    setpoint_c: float = COMFORT_SETPOINT_C,
) -> float:
    if len(temp_series) != 24:
        raise ValueError("Temperature series must contain 24 hourly values")
    return round(sum(max(0.0, float(value) - setpoint_c) for value in temp_series), 2)


def hdh(temp_series: Sequence[float], setpoint_c: float = 18.0) -> float:
    if len(temp_series) != 24:
        raise ValueError("Temperature series must contain 24 hourly values")
    return round(sum(max(0.0, setpoint_c - float(value)) for value in temp_series), 2)


def daily_summary(hourly: dict[str, Sequence[float]]) -> dict[str, float | str]:
    temperatures = hourly["temp_c"]
    ghi = hourly["ghi_wm2"]
    if len(temperatures) != 24 or len(ghi) != 24:
        raise ValueError("Hourly weather must contain 24 temperature and GHI values")
    maximum = max(temperatures)
    minimum = min(temperatures)
    mean_cloud = sum(hourly["cloud_pct"]) / 24
    hours_of_sun = sun_hours(ghi)
    degree_hours = cdh(temperatures)
    if maximum >= 35 and hours_of_sun >= 5:
        description = "Hot and sunny"
    elif maximum >= 35:
        description = "Hot with limited sunshine"
    elif hours_of_sun >= 5:
        description = "Sunny"
    else:
        description = "Mild or cloudy"
    text = (
        f"{description}: {maximum:.0f} C max, about {hours_of_sun:.1f} sun hours"
    )
    return {
        "tmax": round(maximum, 1),
        "tmin": round(minimum, 1),
        "mean_cloud": round(mean_cloud, 1),
        "sun_hours": hours_of_sun,
        "cdh": degree_hours,
        "text": text,
    }
