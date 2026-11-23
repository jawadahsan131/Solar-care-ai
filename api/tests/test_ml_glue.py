from app.services.demand_features import demand_features
from app.services.demand_ml import blend_with_learned_model


def test_demand_features_are_numeric_and_complete() -> None:
    features = demand_features(
        [{"watts": 1200, "count": 1}],
        {"temp_c": [30.0] * 24},
        {"ac_hours": 6},
    )

    assert features["mean_temp_c"] == 30.0
    assert features["total_watts"] == 1200.0
    assert features["ac_hours"] == 6.0


def test_blend_label_is_not_learned_without_residual_evidence() -> None:
    prediction = {"total_kwh": 10.0}

    result = blend_with_learned_model(
        prediction,
        n_days=4,
        residual_std=None,
    )

    assert result["model_basis"] == "physics model"
    assert result["learned_model_available"] is False
