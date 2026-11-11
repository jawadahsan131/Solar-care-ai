import logging
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome, get_owned_home
from app.schemas import FinalizeIn
from app.services.detect import detect
from app.services.detect_vlm import DetectionError, resize_for_detection
from app.services.image_rate_limit import enforce_image_rate_limit

router = APIRouter(tags=["detection"])
logger = logging.getLogger("solar_care.detection")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_MIME_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


@router.post("/homes/{home_id}/detect")
async def detect_home(
    home: OwnedHome,
    user: AuthenticatedUser,
    image: UploadFile = File(...),
    room: str = Form(..., min_length=1, max_length=80),
    retain_image: bool = Form(default=False),
) -> dict:
    enforce_image_rate_limit(user["id"])
    mime = (image.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    expected_format = ALLOWED_MIME_FORMATS.get(mime)
    if expected_format is None:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")

    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller")
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format != expected_format:
                raise HTTPException(
                    status_code=415,
                    detail="Image content does not match its file type",
                )
            source.verify()
        stored_bytes = resize_for_detection(
            image_bytes, max_side=1600, quality=88
        )
    except HTTPException:
        raise
    except (OSError, ValueError, UnidentifiedImageError, DetectionError) as exc:
        raise HTTPException(status_code=415, detail="The uploaded image is invalid") from exc
    finally:
        await image.close()

    image_path = f'{user["id"]}/{home["id"]}/{uuid4().hex}.jpg'
    client = get_supabase()
    client.storage.from_("appliance-images").upload(
        image_path,
        stored_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "false"},
    )
    persisted = False
    try:
        try:
            items = await run_in_threadpool(detect, image_bytes, mime)
        except DetectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        inserted = (
            client.table("detections")
            .insert(
                {
                    "home_id": home["id"],
                    "room": room.strip(),
                    "image_path": image_path if retain_image else None,
                    "backend": settings.detect_backend,
                    "predicted": [item.model_dump() for item in items],
                }
            )
            .execute()
        )
        if not inserted.data:
            raise HTTPException(
                status_code=500, detail="Detection result could not be saved"
            )
        persisted = True
        return {
            "detection_id": inserted.data[0]["id"],
            "image_path": image_path if retain_image else None,
            "items": [item.model_dump() for item in items],
        }
    finally:
        if not persisted or not retain_image:
            try:
                client.storage.from_("appliance-images").remove([image_path])
            except Exception:
                logger.exception("Could not remove failed detection image")


@router.post("/detections/{detection_id}/finalize")
def finalize_detection(
    detection_id: str,
    payload: FinalizeIn,
    user: AuthenticatedUser,
) -> dict:
    client = get_supabase()
    response = (
        client.table("detections")
        .select("*")
        .eq("id", detection_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Detection not found")
    detection_row = response.data[0]
    get_owned_home(detection_row["home_id"], user)
    final_items = [item.model_dump() for item in payload.final_items]
    updated = (
        client.table("detections")
        .update({"final": final_items})
        .eq("id", detection_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Detection not found")
    return {"detection_id": detection_id, "final_items": final_items}
