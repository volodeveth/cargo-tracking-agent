from __future__ import annotations
from datetime import datetime, timezone
from .queue import run_batch
from .orchestrator import process_shipment
from ..models.schemas import (
    ShipmentInput, ShipmentResult, TrackingResponse, Summary, ShortResult,
)
from ..models.enums import ErrorCode, NormalizedStatus

_NON_BLOCKING = {ErrorCode.PARTIAL_DATA}


def _is_success(r: ShipmentResult) -> bool:
    if r.tracking is None or r.tracking.current_status in (None, NormalizedStatus.NOT_FOUND):
        return False
    return not any(e.code not in _NON_BLOCKING for e in r.errors)


async def build_response(inputs: list[ShipmentInput], request_id: str) -> TrackingResponse:
    results: list[ShipmentResult] = await run_batch(inputs, process_shipment)
    success = sum(1 for r in results if _is_success(r))
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
