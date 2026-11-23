from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any

import joblib

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "fault_model.joblib"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"

FEATURE_COLUMNS = [
    "voltage_v",
    "current_a",
    "power_w",
    "panel_temperature_c",
    "light_lux",
]
INPUT_FEATURES = [
    "voltage",
    "current",
    "power",
    "temperature",
    "light",
]


@lru_cache(maxsize=1)
def _load_model_artifacts() -> tuple[Any, Any]:
    if not MODEL_PATH.is_file() or not LABEL_ENCODER_PATH.is_file():
        raise FileNotFoundError(
            "Fault model artifacts are missing. Run ml/train_fault_model.py first."
        )
    return joblib.load(MODEL_PATH), joblib.load(LABEL_ENCODER_PATH)


def predict_fault(features: Mapping[str, object]) -> dict[str, str | float]:
    missing_features = [name for name in INPUT_FEATURES if name not in features]
    if missing_features:
        raise ValueError(
            "Missing sensor features: " + ", ".join(missing_features)
        )

    values: list[float] = []
    for name in INPUT_FEATURES:
        try:
            value = float(features[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Sensor feature {name} must be a number") from exc
        if not isfinite(value):
            raise ValueError(f"Sensor feature {name} must be finite")
        values.append(value)

    import pandas as pd

    model, label_encoder = _load_model_artifacts()
    model_input = pd.DataFrame([values], columns=FEATURE_COLUMNS)
    predicted_label = int(model.predict(model_input)[0])
    confidence = float(model.predict_proba(model_input)[0].max())
    fault_type = str(label_encoder.inverse_transform([predicted_label])[0])
    return {"fault_type": fault_type, "confidence": confidence}
