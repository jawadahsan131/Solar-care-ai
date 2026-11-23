from pathlib import Path
from typing import Any

from app.services.detect_vlm import DetectionError


def detect_raw(image_bytes: bytes, mime: str) -> list[dict[str, Any]]:
    """Return YOLO detections when a deployed weights file and runtime are available."""
    root = Path(__file__).resolve().parents[2]
    weights = root / "models" / "best.pt"
    if not weights.exists():
        raise DetectionError("The trained YOLO model is not available; use the vision AI backend")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise DetectionError("The YOLO runtime is not installed") from exc

    model = YOLO(str(weights))
    results = model(image_bytes)
    return [
        {
            "type": model.names[int(box.cls)],
            "confidence": float(box.conf),
            "count": 1,
            "bbox": [float(value) for value in box.xyxy[0].tolist()],
        }
        for result in results
        for box in result.boxes
    ]


def detect_yolo(image_bytes: bytes, mime: str) -> list[dict[str, Any]]:
    return detect_raw(image_bytes, mime)
