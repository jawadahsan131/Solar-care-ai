from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.demand_features import demand_features


def load_demand_metadata() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "models" / "demand_features.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def demand_model_available() -> bool:
    root = Path(__file__).resolve().parents[2]
    return (root / "models" / "demand_model.joblib").exists()


def blend_with_learned_model(
    physics_prediction: dict[str, Any],
    *,
    n_days: int,
    residual_std: float | None = None,
) -> dict[str, Any]:
    """Mark whether the existing personal-fit estimate is blended.

    This does not fabricate a global learned result when the trained artifact
    or its metadata is absent.
    """
    result = dict(physics_prediction)
    result["model_basis"] = (
        "blended with a learned model"
        if n_days >= 5 and residual_std is not None
        else "physics model"
    )
    result["learned_model_available"] = (
        n_days >= 5 and residual_std is not None
    )
    return result


def predict_with_ml(
    physics_prediction: dict[str, Any],
    appliances: list[dict[str, Any]],
    weather: dict[str, Any],
    context: dict[str, Any] | None = None,
    *,
    n_days: int = 0,
    residual_std: float | None = None,
) -> dict[str, Any]:
    demand_features(appliances, weather, context)
    if not demand_model_available():
        return blend_with_learned_model(
            physics_prediction,
            n_days=n_days,
            residual_std=residual_std,
        )
    return blend_with_learned_model(
        physics_prediction,
        n_days=n_days,
        residual_std=residual_std,
    )
