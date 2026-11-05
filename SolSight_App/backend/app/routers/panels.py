from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.mongo import panels_collection, inspections_collection
from app.db.schemas import PanelCreate, PanelOut
from app.routers.auth import get_current_user

router = APIRouter(prefix="/panels", tags=["panels"])

# Records saved by /upload-inspection haven't been through the models yet and
# have no health_score/status. Everything that reads results filters on this.
ANALYZED = {"analyzed": True}


def _serialize_panel(doc) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


async def _owned_panel(panel_id: str, user: dict) -> dict:
    doc = await panels_collection.find_one({"panel_id": panel_id, "owner_email": user["email"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Panel not found")
    return doc


async def _latest_by_panel(panel_ids: List[str]) -> Dict[str, dict]:
    """Latest analyzed inspection for each panel, in one round trip."""
    if not panel_ids:
        return {}
    pipeline = [
        {"$match": {"panel_id": {"$in": panel_ids}, **ANALYZED}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$panel_id",
            "health_score": {"$first": "$health_score"},
            "status": {"$first": "$status"},
            "created_at": {"$first": "$created_at"},
        }},
    ]
    return {d["_id"]: d async for d in inspections_collection.aggregate(pipeline)}


def _with_latest(panel: dict, latest: dict) -> dict:
    panel["latest_health_score"] = latest.get("health_score") if latest else None
    panel["latest_status"] = latest.get("status") if latest else None
    panel["last_inspected_at"] = latest.get("created_at") if latest else None
    return panel


@router.post("", response_model=PanelOut, status_code=status.HTTP_201_CREATED)
async def create_panel(payload: PanelCreate, current_user: dict = Depends(get_current_user)):
    existing = await panels_collection.find_one({"panel_id": payload.panel_id})
    if existing:
        raise HTTPException(status_code=400, detail="A panel with this panel_id already exists")

    doc = payload.model_dump()
    doc["owner_email"] = current_user["email"]
    doc["created_at"] = datetime.utcnow()
    result = await panels_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _with_latest(_serialize_panel(doc), None)


@router.get("", response_model=List[PanelOut])
async def list_panels(current_user: dict = Depends(get_current_user)):
    cursor = panels_collection.find({"owner_email": current_user["email"]}).sort("panel_id", 1)
    panels = [_serialize_panel(doc) async for doc in cursor]
    latest = await _latest_by_panel([p["panel_id"] for p in panels])
    return [_with_latest(p, latest.get(p["panel_id"])) for p in panels]


@router.get("/{panel_id}", response_model=PanelOut)
async def get_panel(panel_id: str, current_user: dict = Depends(get_current_user)):
    panel = _serialize_panel(await _owned_panel(panel_id, current_user))
    latest = await _latest_by_panel([panel_id])
    return _with_latest(panel, latest.get(panel_id))


@router.delete("/{panel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_panel(panel_id: str, current_user: dict = Depends(get_current_user)):
    await _owned_panel(panel_id, current_user)
    await inspections_collection.delete_many({"panel_id": panel_id})
    await panels_collection.delete_one({"panel_id": panel_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{panel_id}/history")
async def get_panel_history(panel_id: str, current_user: dict = Depends(get_current_user)):
    await _owned_panel(panel_id, current_user)
    cursor = inspections_collection.find({"panel_id": panel_id, **ANALYZED}).sort("created_at", 1)
    return [{
        "id": str(doc["_id"]),
        "date": doc["created_at"],
        "health_score": doc["health_score"],
        "status": doc["status"],
        "detected_defect": doc["detected_defect"],
        "confidence": doc["confidence"],
        "power_output": doc.get("power_output"),
        "power_loss_pct": doc.get("power_loss_pct"),
        "temperature": doc.get("temperature"),
    } async for doc in cursor]


@router.get("/{panel_id}/prediction")
async def get_panel_prediction(panel_id: str, current_user: dict = Depends(get_current_user)):
    await _owned_panel(panel_id, current_user)
    latest = await inspections_collection.find_one(
        {"panel_id": panel_id, **ANALYZED}, sort=[("created_at", -1)]
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No inspections yet for this panel")
    return {
        "current_health": latest["health_score"],
        "status": latest["status"],
        "degradation_forecast": latest["degradation_forecast"],
        "recommendation": latest["recommendation"],
        "analysis_mode": latest.get("analysis_mode"),
    }
