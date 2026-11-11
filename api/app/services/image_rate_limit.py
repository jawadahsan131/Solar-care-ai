import time

from fastapi import HTTPException

WINDOW_SECONDS = 3600
MAX_IMAGE_REQUESTS_PER_WINDOW = 10
_image_requests: dict[str, list[float]] = {}


def enforce_image_rate_limit(user_id: str) -> None:
    now = time.monotonic()
    recent = [
        timestamp
        for timestamp in _image_requests.get(user_id, [])
        if now - timestamp < WINDOW_SECONDS
    ]
    if len(recent) >= MAX_IMAGE_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="Photo limit reached for this hour. Please enter details manually or try later.",
        )
    recent.append(now)
    if recent:
        _image_requests[user_id] = recent
    else:
        _image_requests.pop(user_id, None)
