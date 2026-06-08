from __future__ import annotations
from .track_trace_air import TrackTraceAirConnector
from .track_trace_container import TrackTraceContainerConnector
from .carrier_website import CarrierWebsiteConnector
from .cargoai import CargoAiConnector
from .fixture import FixtureConnector


def all_connectors():
    return {
        "track-trace.com/aircargo": TrackTraceAirConnector(),
        "track-trace.com/container": TrackTraceContainerConnector(),
        "carrier_website": CarrierWebsiteConnector(),
        "cargoai": CargoAiConnector(),
        "fixtures": FixtureConnector(),
    }
