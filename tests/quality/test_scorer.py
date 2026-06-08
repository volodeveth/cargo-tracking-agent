from tracking_agent.quality.scorer import score_quality
from tracking_agent.models.schemas import TrackingData, Dates, DateInfo


def test_missing_actual_arrival_listed():
    td = TrackingData(events=[], dates=Dates(eta=DateInfo(datetime=None)))
    q = score_quality(td)
    assert "actual_arrival" in q.missing_fields
    assert 0.0 <= q.confidence <= 1.0


def test_all_dates_present_and_events_gives_full_score():
    from datetime import datetime, timezone
    dt = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    from tracking_agent.models.schemas import TrackingEvent
    dates = Dates(
        eta=DateInfo(datetime=dt),
        etd=DateInfo(datetime=dt),
        actual_departure=DateInfo(datetime=dt),
        actual_arrival=DateInfo(datetime=dt),
    )
    events = [TrackingEvent(event_name="Delivered")]
    td = TrackingData(events=events, dates=dates)
    q = score_quality(td)
    assert q.missing_fields == []
    assert q.data_complete is True
    assert q.confidence == 1.0


def test_no_events_reduces_confidence():
    from datetime import datetime, timezone
    dt = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    dates = Dates(
        eta=DateInfo(datetime=dt),
        etd=DateInfo(datetime=dt),
        actual_departure=DateInfo(datetime=dt),
        actual_arrival=DateInfo(datetime=dt),
    )
    td = TrackingData(events=[], dates=dates)
    q = score_quality(td)
    assert q.data_complete is False
    assert q.confidence == round(0.0 * 0.4 + 0.6 * 1.0, 2)


def test_empty_tracking_data_all_missing():
    td = TrackingData()
    q = score_quality(td)
    assert set(q.missing_fields) == {"eta", "etd", "actual_departure", "actual_arrival"}
    assert q.data_complete is False
    assert q.confidence == 0.0
