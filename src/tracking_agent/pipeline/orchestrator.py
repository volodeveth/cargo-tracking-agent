from __future__ import annotations
from datetime import datetime, timezone
from ..config import get_settings
from ..models.schemas import (
    ShipmentInput, ShipmentResult, DetectedInfo, Carrier, TrackingData,
    LastEvent, SourceInfo, TrackingError, DebugStep,
)
from ..models.enums import NumberType, NormalizedStatus, ErrorCode
from ..detection.detector import detect_type, normalize_number
from ..detection.awb_prefixes import lookup_awb_carrier
from ..connectors.base import ConnectorStatus
from ..parsers.track_trace_parser import parse_track_trace
from ..normalization.normalizer import normalize_status
from ..normalization.translate_uk import to_ukrainian
from ..quality.scorer import score_quality
from ..quality.risk import assess_risk
from ..pipeline.router import build_chain


async def process_shipment(shipment: ShipmentInput) -> ShipmentResult:
    settings = get_settings()
    result = ShipmentResult(input=shipment)
    number_type = detect_type(shipment.number)
    normalized = normalize_number(shipment.number)
    result.detected = DetectedInfo(type=number_type, normalized_number=normalized)
    result.debug.append(DebugStep(step="detect_type", status="success", result=number_type.value))

    if number_type == NumberType.UNKNOWN:
        result.errors.append(TrackingError(
            code=ErrorCode.INVALID_FORMAT,
            message="Number does not match AWB or container format"))
        return result

    if number_type == NumberType.AIR_AWB:
        carrier = lookup_awb_carrier(normalized)
        if carrier:
            result.detected.carrier = Carrier(**carrier)

    chain = build_chain(number_type, use_fixtures=settings.use_fixtures)
    primary = chain[0].name if chain else None
    conn_result = None
    transient_errors: list[TrackingError] = []
    for connector in chain:
        cr = await connector.fetch(normalized, number_type)
        result.debug.append(DebugStep(step=f"query:{connector.name}", status=cr.status.value,
                                      url=cr.url))
        if cr.status == ConnectorStatus.OK and cr.raw_html:
            conn_result = cr
            break
        if cr.status == ConnectorStatus.NOT_FOUND:
            conn_result = cr
            break
        if cr.error_code:
            transient_errors.append(TrackingError(code=cr.error_code,
                                                  message=cr.error_message or "",
                                                  source=cr.source))

    result.source = SourceInfo(primary_source=primary,
                               final_source=conn_result.source if conn_result else None,
                               url=conn_result.url if conn_result else None,
                               retrieved_at=datetime.now(timezone.utc))

    if conn_result is None:
        result.errors.extend(transient_errors)

    if conn_result is None or conn_result.status == ConnectorStatus.NOT_FOUND:
        result.errors.append(TrackingError(code=ErrorCode.NOT_FOUND,
                                            message="No tracking data found",
                                            source=conn_result.source if conn_result else None))
        result.tracking = TrackingData(current_status=NormalizedStatus.NOT_FOUND)
        return result

    parsed = parse_track_trace(conn_result.raw_html, number_type)
    result.debug.append(DebugStep(step="parse_events", status="success",
                                  events_count=len(parsed.events)))
    current = normalize_status(parsed.raw_status, number_type)

    if current == NormalizedStatus.UNKNOWN and settings.llm_enabled:
        from ..llm.assistant import LLMAssistant
        assistant = LLMAssistant(True, settings.llm_base_url,
                                 settings.llm_api_key, settings.llm_model)
        guess = await assistant.normalize_unknown(parsed.raw_status or "", number_type.value)
        if guess is not None:
            current = guess
            result.quality.warnings.append("status_normalized_by_llm")

    last = parsed.events[-1] if parsed.events else None
    td = TrackingData(
        current_status=current,
        raw_status=parsed.raw_status,
        status_uk=to_ukrainian(current),
        last_event=LastEvent(event_name=last.event_name, location=last.location,
                             datetime=last.datetime, is_actual=True) if last else None,
        dates=parsed.dates,
        route=parsed.route,
        events=parsed.events,
    )
    result.tracking = td
    result.quality = score_quality(td)
    result.risk = assess_risk(td)
    if result.quality.missing_fields:
        result.errors.append(TrackingError(code=ErrorCode.PARTIAL_DATA,
                                            message="Some key fields are missing",
                                            source=conn_result.source))
    return result
