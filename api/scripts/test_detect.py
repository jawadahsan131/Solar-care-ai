import sys
from pathlib import Path

from app.services.detect import detect
from app.services.detect_vlm import DetectionError


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_detect.py <photo.jpg>")
        return 2
    image_path = Path(sys.argv[1])
    if not image_path.is_file():
        print(f"Image not found: {image_path}")
        return 2
    try:
        items = detect(image_path.read_bytes(), "image/jpeg")
    except (DetectionError, OSError) as exc:
        print(f"Detection failed: {exc}")
        return 1
    if not items:
        print("No appliances detected.")
        return 0

    print(f"{'TYPE':<20} {'BRAND / MODEL':<28} {'WATTS':>8} {'SOURCE':<9} CONF")
    for item in items:
        name = " ".join(part for part in (item.brand, item.model) if part) or "—"
        print(
            f"{item.type:<20} {name[:28]:<28} {item.watts:>8.0f} "
            f"{item.source_tag:<9} {item.confidence:.0%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
