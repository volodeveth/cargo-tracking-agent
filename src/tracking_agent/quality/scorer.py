from __future__ import annotations
from ..models.schemas import TrackingData, Quality

_KEY_FIELDS = ["eta", "etd", "actual_departure", "actual_arrival"]


def score_quality(td: TrackingData) -> Quality:
    missing = []
    for f in _KEY_FIELDS:
        di = getattr(td.dates, f)
        if di is None or di.datetime is None:
            missing.append(f)
    has_events = bool(td.events)
    present = len(_KEY_FIELDS) - len(missing)
    confidence = round(0.4 * bool(has_events) + 0.6 * (present / len(_KEY_FIELDS)), 2)
    return Quality(
        confidence=confidence,
        data_complete=not missing and has_events,
        missing_fields=missing,
        warnings=[],
    )
