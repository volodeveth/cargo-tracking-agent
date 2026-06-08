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

# User-supplied `type` is treated as a hint only: detection from the number is
# authoritative, so these synonyms exist solely to compare against it.
_TYPE_SYNONYMS = {
    "air": NumberType.AIR_AWB, "air_awb": NumberType.AIR_AWB,
    "awb": NumberType.AIR_AWB, "aircargo": NumberType.AIR_AWB,
    "sea": NumberType.SEA_CONTAINER, "sea_container": NumberType.SEA_CONTAINER,
    "container": NumberType.SEA_CONTAINER, "ocean": NumberType.SEA_CONTAINER,
}


def _coerce_type_hint(value: str) -> NumberType | None:
    return _TYPE_SYNONYMS.get(value.strip().lower())


async def process_shipment(shipment: ShipmentInput) -> ShipmentResult:
    settings = get_settings()
    result = ShipmentResult(input=shipment)
    number_type = detect_type(shipment.number)
    normalized = normalize_number(shipment.number)
    result.detected = DetectedInfo(type=number_type, normalized_number=normalized)
    result.debug.append(DebugStep(step="detect_type", status="success", result=number_type.value))

    # Optional user hints are validated against detection, never trusted blindly.
    hint_warnings: list[str] = []
    if shipment.type:
        coerced = _coerce_type_hint(shipment.type)
        if number_type != NumberType.UNKNOWN and coerced != number_type:
            hint_warnings.append("type_hint_ignored")

    if number_type == NumberType.UNKNOWN:
        result.errors.append(TrackingError(
            code=ErrorCode.INVALID_FORMAT,
            message="Number does not match AWB or container format"))
        result.quality.warnings.extend(hint_warnings)
        return result

    if number_type == NumberType.AIR_AWB:
        carrier = lookup_awb_carrier(normalized)
        if carrier:
            result.detected.carrier = Carrier(**carrier)

    if shipment.carrier:
        provided = shipment.carrier.strip()
        if result.detected.carrier is None:
            # nothing derived from the number -> use the hint, flagged unverified
            result.detected.carrier = Carrier(name=provided, source="user_provided")
        else:
            derived = (result.detected.carrier.name or "").strip().lower()
            p = provided.lower()
            # tolerant match: "LOT" vs "LOT Polish Airlines" is consistent, not a conflict
            if p and derived and p not in derived and derived not in p:
                hint_warnings.append("carrier_hint_ignored")

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
        result.tracking = TrackingData(current_status=NormalizedStatus.NOT_FOUND,
                                        status_uk=to_ukrainian(NormalizedStatus.NOT_FOUND))
        result.quality.warnings.extend(hint_warnings)
        return result

    parsed = parse_track_trace(conn_result.raw_html, number_type)
    result.debug.append(DebugStep(step="parse_events", status="success",
                                  events_count=len(parsed.events)))

    assistant = None
    if settings.llm_enabled:
        from ..llm.assistant import LLMAssistant
        assistant = LLMAssistant(True, settings.llm_base_url,
                                 settings.llm_api_key, settings.llm_model)

    # #3: when the deterministic parser found nothing on a non-standard page,
    # let the LLM recover events from the semi-structured text.
    events_extracted_by_llm = False
    if not parsed.events and assistant is not None:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(conn_result.raw_html, "html.parser").get_text(" ", strip=True)
        extracted = await assistant.extract_events(text, number_type)
        if extracted:
            parsed.events = extracted
            parsed.raw_status = extracted[-1].raw_text or extracted[-1].event_name
            events_extracted_by_llm = True
            result.debug.append(DebugStep(step="llm_extract_events", status="success",
                                          events_count=len(extracted)))

    current = normalize_status(parsed.raw_status, number_type)

    # #4: map a status the deterministic rules could not resolve.
    status_normalized_by_llm = False
    if current == NormalizedStatus.UNKNOWN and assistant is not None:
        guess = await assistant.normalize_unknown(parsed.raw_status or "", number_type.value)
        if guess is not None:
            current = guess
            status_normalized_by_llm = True

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
    if events_extracted_by_llm:
        result.quality.warnings.append("events_extracted_by_llm")
    if status_normalized_by_llm:
        result.quality.warnings.append("status_normalized_by_llm")
    result.quality.warnings.extend(hint_warnings)
    result.risk = assess_risk(td)
    if result.quality.missing_fields:
        result.errors.append(TrackingError(code=ErrorCode.PARTIAL_DATA,
                                            message="Some key fields are missing",
                                            source=conn_result.source))
        # #5: explain to the user why the data is incomplete.
        if assistant is not None:
            explanation = await assistant.explain_incomplete(
                result.quality.missing_fields, current.value, conn_result.source)
            if explanation:
                result.quality.explanation = explanation
    return result
