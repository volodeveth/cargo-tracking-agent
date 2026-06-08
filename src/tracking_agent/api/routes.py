from __future__ import annotations
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from ..models.schemas import ShipmentInput
from ..pipeline.builder import build_response

router = APIRouter()


class TrackRequest(BaseModel):
    shipments: list[ShipmentInput]


@router.post("/track")
async def track(req: TrackRequest):
    request_id = f"tracking-check-{uuid.uuid4().hex[:8]}"
    resp = await build_response(req.shipments, request_id=request_id)
    return resp.model_dump(mode="json")
