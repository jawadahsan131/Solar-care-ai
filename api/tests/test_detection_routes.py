from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.deps import get_owned_home
from app.main import app


def test_detection_rejects_non_image_without_storage_or_ai() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "test-user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_owned_home] = lambda: {
        "id": "test-home",
        "user_id": "test-user",
    }
    try:
        response = TestClient(app).post(
            "/homes/test-home/detect",
            data={"room": "Kitchen"},
            files={"image": ("document.pdf", b"%PDF-1.7", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_detection_rejects_oversized_image_before_processing() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "test-user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_owned_home] = lambda: {
        "id": "test-home",
        "user_id": "test-user",
    }
    try:
        response = TestClient(app).post(
            "/homes/test-home/detect",
            data={"room": "Kitchen"},
            files={
                "image": (
                    "large.png",
                    b"x" * (8 * 1024 * 1024 + 1),
                    "image/png",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"
