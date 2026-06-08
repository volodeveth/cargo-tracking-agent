from __future__ import annotations
from ..models.enums import NumberType
from .track_trace_air import TrackTraceAirConnector


class TrackTraceContainerConnector(TrackTraceAirConnector):
    name = "track-trace.com/container"
    supports = (NumberType.SEA_CONTAINER,)
    url_template = "https://www.track-trace.com/container"
