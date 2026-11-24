import re
from typing import Any

from app.config import settings
from app.schemas import ALLOWED_TYPES, DetectedItem
from app.services.appliances import get_catalog
from app.services.catalog import match
from app.services.detect_vlm import DetectionError, detect_vlm
from app.services.detect_yolo import detect_yolo

FALLBACKS = {
    "ac": (1700.0, 0.65, 4.0, 8.0),
    "ceiling_fan": (75.0, 1.0, 1.3, 10.0),
    "pedestal_fan": (70.0, 1.0, 1.3, 6.0),
    "exhaust_fan": (45.0, 1.0, 1.3, 2.0),
    "air_cooler": (200.0, 1.0, 2.0, 8.0),
    "refrigerator": (150.0, 0.4, 3.5, 24.0),
    "deep_freezer": (230.0, 0.5, 4.0, 24.0),
    "microwave": (1250.0, 1.0, 1.2, 0.3),
    "electric_oven": (1800.0, 0.7, 1.2, 0.5),
    "water_dispenser": (525.0, 0.3, 3.0, 24.0),
    "electric_kettle": (1850.0, 1.0, 1.2, 0.3),
    "washing_machine": (400.0, 1.0, 2.5, 1.0),
    "iron": (1300.0, 0.7, 1.0, 0.5),
    "geyser": (2200.0, 0.4, 1.0, 2.0),
    "water_pump": (750.0, 1.0, 4.0, 1.0),
    "tv": (75.0, 1.0, 1.0, 5.0),
    "desktop_pc": (250.0, 1.0, 1.5, 5.0),
    "laptop": (65.0, 1.0, 1.2, 6.0),
    "router": (12.0, 1.0, 1.0, 24.0),
    "ups": (90.0, 1.0, 2.0, 24.0),
    "led_bulb": (12.0, 1.0, 1.0, 6.0),
    "tube_light": (24.0, 1.0, 1.0, 6.0),
    "phone_charger": (10.0, 1.0, 1.0, 3.0),
    "vacuum_cleaner": (1200.0, 1.0, 1.5, 0.3),
    "other": (100.0, 1.0, 1.0, 2.0),
}


def detect_with_backend(
    image_bytes: bytes, mime: str
) -> tuple[list[DetectedItem], str]:
    """Detect appliances in image bytes and apply catalog-backed post-processing."""
    backend = settings.detect_backend.lower()
    if backend == "vlm":
        raw_items = detect_vlm(image_bytes, mime)
        actual_backend = "vision AI"
    elif backend == "yolo":
        try:
            raw_items = detect_yolo(image_bytes, mime)
        except NotImplementedError as exc:
            raise DetectionError(str(exc)) from exc
        actual_backend = "our trained model"
    elif backend == "hybrid":
        try:
            raw_items = detect_yolo(image_bytes, mime)
            actual_backend = "our trained model"
        except DetectionError:
            raw_items = detect_vlm(image_bytes, mime)
            actual_backend = "vision AI"
    else:
        raise DetectionError("DETECT_BACKEND must be 'vlm', 'yolo', or 'hybrid'")
    return postprocess(raw_items, get_catalog()), actual_backend


def detect(image_bytes: bytes, mime: str) -> list[DetectedItem]:
    items, _ = detect_with_backend(image_bytes, mime)
    return items


def postprocess(
    raw_items: list[dict[str, Any]], catalog: list[dict[str, Any]]
) -> list[DetectedItem]:
    """Normalize vision output and attach catalog estimates with honest source tags."""
    merged: dict[tuple[Any, ...], DetectedItem] = {}
    for raw in raw_items:
        appliance_type = raw.get("type")
        if appliance_type not in ALLOWED_TYPES:
            appliance_type = "other"
        capacity_value, capacity_unit = parse_capacity(raw.get("capacity_text"))
        label_watts, power_note = parse_rated_power(raw.get("rated_power_text"))
        inverter_text = raw.get("inverter_text")
        inverter = (
            True
            if inverter_text and "inverter" in inverter_text.lower()
            else None
        )
        row, level = match(
            catalog,
            appliance_type,
            raw.get("brand"),
            raw.get("model"),
            capacity_value,
            capacity_unit,
            inverter,
        )
        fallback_watts, fallback_duty, fallback_surge, fallback_hours = FALLBACKS[
            appliance_type
        ]
        watts = label_watts if label_watts is not None else (
            row["rated_watts"] if row else fallback_watts
        )
        duty_factor = row["duty_factor"] if row else fallback_duty
        surge_factor = row["surge_factor"] if row else fallback_surge
        default_hours = row["default_hours"] if row else fallback_hours
        model_confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.5))))
        if label_watts is not None:
            source_tag = "label"
            confidence = min(0.95, model_confidence + 0.1)
        elif level == "exact":
            source_tag = "catalog"
            confidence = min(0.85, model_confidence)
        elif level in {"brand_capacity", "type_capacity"}:
            source_tag = "guess"
            confidence = min(0.6, model_confidence)
        else:
            source_tag = "guess"
            confidence = min(0.4, model_confidence)

        notes = raw.get("notes")
        if power_note:
            notes = _append_note(notes, power_note)
        if source_tag == "guess":
            notes = _append_note(notes, "Typical value, please confirm.")
        if appliance_type == "ac" and inverter is None:
            notes = _append_note(notes, "Inverter or not? Please confirm.")

        item = DetectedItem(
            type=appliance_type,
            brand=raw.get("brand"),
            model=raw.get("model"),
            capacity_value=capacity_value,
            capacity_unit=capacity_unit,
            inverter=inverter,
            count=max(1, min(50, int(raw.get("count", 1)))),
            watts=watts,
            duty_factor=duty_factor,
            surge_factor=surge_factor,
            default_hours=default_hours,
            confidence=confidence,
            source_tag=source_tag,
            label_text=raw.get("label_text"),
            bbox=normalized_bbox(raw.get("bbox")),
            notes=notes,
        )
        key = (
            item.type,
            (item.brand or "").strip().lower(),
            (item.model or "").strip().lower(),
            item.capacity_value,
            item.capacity_unit,
            item.inverter,
            item.watts,
        )
        if key in merged:
            existing = merged[key]
            merged[key] = existing.model_copy(
                update={"count": min(50, existing.count + item.count)}
            )
        else:
            merged[key] = item
    return sorted(merged.values(), key=lambda item: item.confidence, reverse=True)


def normalized_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        coordinates = [float(coordinate) for coordinate in value]
    except (TypeError, ValueError):
        return None
    if any(coordinate < 0 or coordinate > 1 for coordinate in coordinates):
        return None
    return coordinates


def parse_capacity(value: str | None) -> tuple[float | None, str | None]:
    if not value:
        return None, None
    normalized = value.lower().replace(",", "").replace("³", "3")
    match_result = re.search(
        r"(\d+(?:\.\d+)?)\s*(cu\.?\s*ft|btu|tons?|ton|inches?|inch|litres?|liters?|litre|l|kg|hp)\b",
        normalized,
    )
    if not match_result:
        return None, None
    amount = float(match_result.group(1))
    unit_text = match_result.group(2).replace(".", "").replace(" ", "")
    if unit_text == "btu":
        return amount / 12000, "ton"
    units = {
        "ton": "ton",
        "tons": "ton",
        "inch": "inch",
        "inches": "inch",
        "litre": "litre",
        "litres": "litre",
        "liter": "litre",
        "liters": "litre",
        "l": "litre",
        "kg": "kg",
        "hp": "hp",
        "cuft": "cu_ft",
    }
    return amount, units.get(unit_text, unit_text)


def parse_rated_power(value: str | None) -> tuple[float | None, str | None]:
    if not value:
        return None, None
    normalized = value.lower().replace(",", "")
    match_result = re.search(r"(\d+(?:\.\d+)?)\s*(kw|w|va)\b", normalized)
    if not match_result:
        return None, None
    power = float(match_result.group(1))
    unit = match_result.group(2)
    if unit == "kw":
        return power * 1000, None
    if unit == "va":
        return power, "VA is treated as watts for this estimate; please confirm."
    return power, None


def _append_note(existing: str | None, note: str) -> str:
    return f"{existing} {note}".strip() if existing else note
