from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool

from app.db.mongo import panels_collection, inspections_collection
from app.routers.auth import get_current_user
from app.services.prediction_service import prediction_service, InvalidImageError

router = APIRouter(tags=["inspections"])

# Images are stored inline in the inspection document; MongoDB caps a
# document at 16 MB, so keep well under that.
MAX_IMAGE_BYTES = 5 * 1024 * 1024


async def _owned_panel(panel_id: str, user: dict) -> dict:
    panel = await panels_collection.find_one({"panel_id": panel_id, "owner_email": user["email"]})
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")
    return panel


async def _read_image(image: Optional[UploadFile]) -> Optional[bytes]:
    if image is None or not image.filename:
        return None
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files can be attached")
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 5 MB")
    return data or None


def _check_readings(voltage: float, current: float, temperature: float):
    if not (0 <= voltage <= 100):
        raise HTTPException(status_code=422, detail="Voltage must be between 0 and 100 V")
    if not (0 <= current <= 30):
        raise HTTPException(status_code=422, detail="Current must be between 0 and 30 A")
    if not (-40 <= temperature <= 120):
        raise HTTPException(status_code=422, detail="Temperature must be between -40 and 120 °C")


@router.post("/upload-inspection")
async def upload_inspection(
    panel_id: str = Form(...),
    voltage: float = Form(...),
    current: float = Form(...),
    temperature: float = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    """Stores a raw inspection record without running the models.
    Use /predict-defect to upload and analyze in one step."""
    _check_readings(voltage, current, temperature)
    panel = await _owned_panel(panel_id, current_user)
    image_bytes = await _read_image(image)

    doc = {
        "panel_id": panel_id,
        "owner_email": current_user["email"],
        "created_at": datetime.utcnow(),
        "voltage": voltage,
        "current": current,
        "temperature": temperature,
        "rated_power": panel["rated_power"],
        "image_bytes": image_bytes,
        "analyzed": False,
    }
    result = await inspections_collection.insert_one(doc)
    return {"inspection_id": str(result.inserted_id), "status": "uploaded"}


@router.post("/predict-defect")
async def predict_defect(
    panel_id: str = Form(...),
    voltage: float = Form(...),
    current: float = Form(...),
    temperature: float = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    """Runs the full CNN -> MLP -> Bi-LSTM pipeline and persists the result."""
    _check_readings(voltage, current, temperature)
    panel = await _owned_panel(panel_id, current_user)
    image_bytes = await _read_image(image)

    # This panel's health history (oldest first) feeds the forecast
    history_cursor = inspections_collection.find(
        {"panel_id": panel_id, "analyzed": True},
        {"created_at": 1, "health_score": 1},
    ).sort("created_at", 1)
    history = [(doc["created_at"], doc["health_score"]) async for doc in history_cursor]

    # Torch inference is CPU-bound; keep it off the event loop
    try:
        result = await run_in_threadpool(
            prediction_service.run_inspection,
            image_bytes=image_bytes,
            voltage=voltage,
            current=current,
            temperature=temperature,
            rated_power=panel["rated_power"],
            history=history,
        )
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    inspection_doc = {
        "panel_id": panel_id,
        "owner_email": current_user["email"],
        "created_at": datetime.utcnow(),
        "voltage": voltage,
        "current": current,
        "temperature": temperature,
        "has_image": image_bytes is not None,
        **result,
        "analyzed": True,
    }
    inserted = await inspections_collection.insert_one(inspection_doc)
    inspection_doc["id"] = str(inserted.inserted_id)
    inspection_doc.pop("_id", None)
    return inspection_doc
