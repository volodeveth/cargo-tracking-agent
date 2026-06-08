from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from ..models.schemas import TrackingEvent, Dates, Route


@dataclass
class ParsedTracking:
    raw_status: Optional[str] = None
    events: list[TrackingEvent] = field(default_factory=list)
    dates: Dates = field(default_factory=Dates)
    route: Route = field(default_factory=Route)
