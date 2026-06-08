from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from .queue import run_batch
from .orchestrator import process_shipment
from ..config import get_settings
from ..models.schemas import (
    ShipmentInput, ShipmentResult, TrackingResponse, Summary, ShortResult,
    TrackingError,
)
from ..models.enums import ErrorCode, NormalizedStatus

_NON_BLOCKING = {ErrorCode.PARTIAL_DATA}


def _is_success(r: ShipmentResult) -> bool:
    if r.tracking is None or r.tracking.current_status in (None, NormalizedStatus.NOT_FOUND):
        return False
    return not any(e.code not in _NON_BLOCKING for e in r.errors)


async def _safe_process(inp: ShipmentInput) -> ShipmentResult:
    # Guarantee ТЗ §13 independence: a failure (or hang) on one number must never
    # cancel the batch — it degrades to a structured error result. A per-number
    # timeout (ТЗ §11) bounds how long any single shipment can take.
    timeout = get_settings().number_timeout
    try:
        return await asyncio.wait_for(process_shipment(inp), timeout=timeout)
    except asyncio.TimeoutError:
        return ShipmentResult(input=inp, errors=[TrackingError(
            code=ErrorCode.TIMEOUT,
            message=f"Processing exceeded the per-number timeout of {timeout}s")])
    except Exception as exc:
        return ShipmentResult(input=inp, errors=[TrackingError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unexpected error: {type(exc).__name__}: {exc}")])


async def build_response(inputs: list[ShipmentInput], request_id: str) -> TrackingResponse:
    results: list[ShipmentResult] = await run_batch(inputs, _safe_process)
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
