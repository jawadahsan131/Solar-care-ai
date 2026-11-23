from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user
from app.config import settings

router = APIRouter(prefix="/models", tags=["models"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


@router.get("/info")
async def get_model_info(user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    repo_root = _repo_root()
    models_dir = repo_root / "models"
    classes_path = models_dir / "yolo_classes.json"
    demand_path = models_dir / "demand_features.json"
    demand_meta = _read_json(demand_path) or {}

    detector_classes: list[str] = []
    if classes_path.exists():
        try:
            detector_classes = json.loads(classes_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            detector_classes = []

    date_range = demand_meta.get("date_range")
    if isinstance(date_range, dict):
        normalized_range = {
            "start": date_range.get("start"),
            "end": date_range.get("end"),
        }
    else:
        normalized_range = None

    demand_label = (
        demand_meta.get("data_label")
        or demand_meta.get("label")
        or ("synthetic" if bool(demand_meta.get("synthetic")) else "unknown")
    )

    return {
        "detector": {
            "backend_setting": settings.detect_backend,
            "weights_present": (models_dir / "best.pt").exists(),
            "classes": detector_classes,
        },
        "demand": {
            "available": demand_path.exists(),
            "synthetic": bool(demand_meta.get("synthetic")),
            "n_days": int(demand_meta.get("n_days") or 0),
            "date_range": normalized_range,
            "data_label": demand_label,
        },
        "eval_docs": {
            "yolo": (repo_root / "docs" / "yolo_eval.md").exists(),
            "demand": (repo_root / "docs" / "demand_eval.md").exists(),
        },
    }
