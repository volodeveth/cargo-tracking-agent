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


def test_parse_empty_html_does_not_crash():
    parsed = parse_track_trace("", NumberType.AIR_AWB)
    assert parsed.events == []
    assert parsed.raw_status is None


def test_parse_garbage_html_does_not_crash():
    parsed = parse_track_trace("<html><body><p>not a tracking page</p></body></html>",
                               NumberType.SEA_CONTAINER)
    assert parsed.events == []


def test_parse_skips_rows_with_too_few_cells():
    html = """<table id="results">
      <tr><th>date</th><th>status</th><th>loc</th></tr>
      <tr><td>2026-06-05T18:45:00+02:00</td><td>incomplete</td></tr>
      <tr><td>2026-06-05T19:00:00+02:00</td><td>Departed (DEP)</td><td>HKG</td></tr>
    </table>"""
    parsed = parse_track_trace(html, NumberType.AIR_AWB)
    assert len(parsed.events) == 1  # the 2-cell row is skipped
    assert parsed.events[0].location == "HKG"


def test_parse_missing_meta_leaves_dates_and_route_empty():
    html = """<table id="results">
      <tr><th>date</th><th>status</th><th>loc</th></tr>
      <tr><td>2026-06-05T18:45:00+02:00</td><td>Departed (DEP)</td><td>HKG</td></tr>
    </table>"""
    parsed = parse_track_trace(html, NumberType.AIR_AWB)
    assert parsed.dates.eta is None and parsed.dates.etd is None
    assert parsed.route.origin is None and parsed.route.destination is None
