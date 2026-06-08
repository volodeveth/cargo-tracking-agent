from __future__ import annotations
from datetime import datetime
from ..models.schemas import DateInfo
from ..models.enums import TimezoneConfidence

_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%d %b %Y %H:%M",
    "%d %b %Y",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


def parse_datetime(raw: str | None) -> DateInfo:
    if not raw:
        return DateInfo()
    raw = raw.strip()
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if dt.tzinfo is not None:
            return DateInfo(
                datetime=dt, raw_datetime=raw,
                timezone=dt.strftime("%z")[:3] + ":" + dt.strftime("%z")[3:],
                timezone_confidence=TimezoneConfidence.SOURCE_PROVIDED,
            )
        return DateInfo(
            datetime=None, raw_datetime=raw, timezone=None,
            timezone_confidence=TimezoneConfidence.UNKNOWN,
        )
    return DateInfo(raw_datetime=raw, timezone_confidence=TimezoneConfidence.UNKNOWN)
