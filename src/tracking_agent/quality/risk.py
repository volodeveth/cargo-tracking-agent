from __future__ import annotations
from datetime import datetime, timezone
from ..models.schemas import TrackingData, Risk
from ..models.enums import NormalizedStatus, RiskLevel

_DONE = {
    NormalizedStatus.DELIVERED,
    NormalizedStatus.ARRIVED,
    NormalizedStatus.READY_FOR_PICKUP,
    NormalizedStatus.CONTAINER_RETURNED,
}


def assess_risk(td: TrackingData) -> Risk:
    reasons: list[str] = []
    delay = False
    eta = td.dates.eta.datetime if td.dates.eta else None
    if eta and td.current_status not in _DONE:
        now = datetime.now(timezone.utc)
        if eta.tzinfo is None:
            eta = eta.replace(tzinfo=timezone.utc)
        if now > eta:
            delay = True
            reasons.append("past_eta")
    if td.current_status == NormalizedStatus.EXCEPTION:
        reasons.append("exception_status")
    level = RiskLevel.LOW
    if "exception_status" in reasons:
        level = RiskLevel.HIGH
    elif delay:
        level = RiskLevel.MEDIUM
    return Risk(risk_level=level, delay_detected=delay, reasons=reasons)
