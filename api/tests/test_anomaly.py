from app.services.anomaly import verdict_for_day


def test_anomaly_requires_five_real_days() -> None:
    result = verdict_for_day("2026-01-01", 100, 50, 5, n_days=4)

    assert result["status"] == "unknown"
    assert result["z"] is None


def test_anomaly_flags_high_and_low_usage_without_accusatory_language() -> None:
    high = verdict_for_day("2026-01-01", 160, 100, 10, n_days=10)
    low = verdict_for_day("2026-01-02", 40, 100, 10, n_days=10)

    assert high["status"] == "high"
    assert low["status"] == "low"
    assert all("fault" not in reason.lower() for reason in high["reasons"])
