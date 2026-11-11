from app.services.bill_ocr import parse_bill_text


def test_parse_bill_text_handles_common_month_formats() -> None:
    payload = "Billing month: OCT 25\nCurrent units: 421.3\nTotal amount: PKR 14,250\n"
    result = parse_bill_text(payload)
    assert result["month"] == "2025-10-01"
    assert result["units_kwh"] == 421.3
    assert result["amount_pkr"] == 14250.0
    assert result["confidence"] >= 0.7


def test_parse_bill_text_ignores_impossible_values() -> None:
    payload = "Billing month: 10/2025\nCurrent units: 7000\nHistory: Oct-2025 4000, Sep-2025 5100\n"
    result = parse_bill_text(payload)
    assert result["units_kwh"] is None
    assert len(result["history"]) >= 1
    assert result["warnings"]


def test_parse_bill_text_falls_back_to_history_when_units_missing() -> None:
    payload = "Month: Oct-2025\nHistory: Sep-2025 410, Aug-2025 420\n"
    result = parse_bill_text(payload)
    assert result["month"] == "2025-10-01"
    assert result["units_kwh"] == 410
