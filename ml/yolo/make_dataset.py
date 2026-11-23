"""Validate local YOLO data before dataset preparation."""

from pathlib import Path


if __name__ == "__main__":
    raw = Path("data/yolo_raw")
    if not raw.exists():
        raise SystemExit("No local labeled photo dataset is available.")
