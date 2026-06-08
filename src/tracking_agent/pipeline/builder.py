from __future__ import annotations
from datetime import datetime, timezone
from .queue import run_batch
from .orchestrator import process_shipment
from ..models.schemas import (
    ShipmentInput, ShipmentResult, TrackingResponse, Summary, ShortResult,
)


async def build_response(inputs: list[ShipmentInput], request_id: str) -> TrackingResponse:
    results: list[ShipmentResult] = await run_batch(inputs, process_shipment)
    success = sum(1 for r in results if not r.errors)
    failed = len(results) - success
    return TrackingResponse(
        request_id=request_id,
        checked_at=datetime.now(timezone.utc),
        summary=Summary(total=len(results), success=success, failed=failed),
        results=results,
    )


def to_short(r: ShipmentResult) -> ShortResult:
    td = r.tracking
    return ShortResult(
        id=r.input.id, number=r.input.number, type=r.detected.type,
        current_status=td.current_status if td else None,
        eta=td.dates.eta.datetime if td and td.dates.eta else None,
        etd=td.dates.etd.datetime if td and td.dates.etd else None,
        last_event_at=td.last_event.datetime if td and td.last_event else None,
        source=r.source.final_source, errors=r.errors,
    )
