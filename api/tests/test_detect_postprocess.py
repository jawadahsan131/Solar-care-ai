from app.services.catalog import load_catalog, match
from app.services.appliances import configured_catalog_path
from app.services.detect import parse_capacity, parse_rated_power, postprocess


CATALOG = load_catalog(configured_catalog_path())


def test_label_power_overrides_catalog_watts() -> None:
    items = postprocess(
        [
            {
                "type": "ac",
                "capacity_text": "1.5 Ton",
                "rated_power_text": "1650W",
                "confidence": 0.8,
            }
        ],
        CATALOG,
    )
    assert items[0].watts == 1650
    assert items[0].source_tag == "label"
    assert items[0].capacity_value == 1.5
    assert items[0].capacity_unit == "ton"


def test_btu_capacity_is_converted_to_tons() -> None:
    assert parse_capacity("18000 BTU") == (1.5, "ton")


def test_unknown_brand_uses_a_low_confidence_guess() -> None:
    items = postprocess(
        [
            {
                "type": "ac",
                "brand": "Unknown Brand",
                "model": "Mystery",
                "capacity_text": "1.5 ton",
                "confidence": 0.9,
            }
        ],
        CATALOG,
    )
    assert items[0].source_tag == "guess"
    assert items[0].confidence <= 0.6


def test_unknown_types_are_normalized_and_duplicate_items_merged() -> None:
    items = postprocess(
        [
            {"type": "unlisted-appliance", "count": 1, "confidence": 0.6},
            {"type": "other", "count": 2, "confidence": 0.5},
        ],
        CATALOG,
    )
    assert len(items) == 1
    assert items[0].type == "other"
    assert items[0].count == 3


def test_catalog_capacity_tolerance_is_ten_percent() -> None:
    row, level = match(CATALOG, "ac", None, None, 1.6, "ton", False)
    assert row is not None
    assert level == "type_capacity"
    row, level = match(CATALOG, "ac", None, None, 1.7, "ton", False)
    assert row is not None
    assert level == "type_only"


def test_power_parser_handles_kw_and_va_note() -> None:
    assert parse_rated_power("1.2 kW") == (1200, None)
    watts, note = parse_rated_power("500 VA")
    assert watts == 500
    assert note is not None


def test_missing_catalog_uses_fallback(tmp_path) -> None:
    rows = load_catalog(tmp_path / "missing.csv")
    assert rows
    assert any(row["type"] == "ac" for row in rows)
