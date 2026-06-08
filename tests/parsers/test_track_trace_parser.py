from pathlib import Path
from tracking_agent.parsers.track_trace_parser import parse_track_trace
from tracking_agent.models.enums import NumberType

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_parse_air_events_and_dates():
    html = (FIX / "air_080-38652331.html").read_text(encoding="utf-8")
    parsed = parse_track_trace(html, NumberType.AIR_AWB)
    assert len(parsed.events) == 3
    assert parsed.route.origin == "HKG"
    assert parsed.dates.eta is not None
    assert parsed.raw_status == "In transit / transfer (MAN)"
