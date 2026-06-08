from __future__ import annotations
import uuid
from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from ..models.schemas import ShipmentInput
from ..pipeline.builder import build_response
from ..export.excel import export_results_bytes

router = APIRouter()

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class TrackRequest(BaseModel):
    shipments: list[ShipmentInput]


@router.post("/track")
async def track(req: TrackRequest, format: str = Query("json", pattern="^(json|xlsx)$")):
    request_id = f"tracking-check-{uuid.uuid4().hex[:8]}"
    resp = await build_response(req.shipments, request_id=request_id)
    if format == "xlsx":
        return Response(
            content=export_results_bytes(resp.results),
            media_type=XLSX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{request_id}.xlsx"'},
        )
    return resp.model_dump(mode="json")
