from tracking_agent.parsers.dates import parse_datetime


def test_parse_with_timezone():
    d = parse_datetime("2026-06-05T18:45:00+08:00")
    assert d.timezone_confidence.value == "source_provided"
    assert d.datetime is not None


def test_parse_unknown_tz_keeps_raw_no_invention():
    d = parse_datetime("07 Jun 2026 12:30")
    assert d.raw_datetime == "07 Jun 2026 12:30"
    assert d.timezone is None
    assert d.timezone_confidence.value == "unknown"


def test_unparseable_returns_raw_only():
    d = parse_datetime("garbage")
    assert d.datetime is None and d.raw_datetime == "garbage"
