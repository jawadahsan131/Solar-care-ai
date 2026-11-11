from typing import Any

from app.services.detect_vlm import DetectionError


def detect_yolo(image_bytes: bytes, mime: str) -> list[dict[str, Any]]:
    """YOLO integration point; training and model deployment are not yet available."""
    raise NotImplementedError(
        "The YOLO backend is not configured yet; use DETECT_BACKEND=vlm"
    )
