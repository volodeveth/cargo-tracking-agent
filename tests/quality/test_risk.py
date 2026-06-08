from datetime import datetime, timezone, timedelta
from tracking_agent.quality.risk import assess_risk
from tracking_agent.models.schemas import TrackingData, Dates, DateInfo
from tracking_agent.models.enums import NormalizedStatus, RiskLevel


def test_delay_detected_when_past_eta_and_not_arrived():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    td = TrackingData(current_status=NormalizedStatus.IN_TRANSIT,
                      dates=Dates(eta=DateInfo(datetime=past)))
    risk = assess_risk(td)
    assert risk.delay_detected is True
    assert risk.risk_level.value in ("medium", "high")


def test_no_delay_when_eta_in_future():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    td = TrackingData(current_status=NormalizedStatus.IN_TRANSIT,
                      dates=Dates(eta=DateInfo(datetime=future)))
    risk = assess_risk(td)
    assert risk.delay_detected is False
    assert risk.risk_level == RiskLevel.LOW


def test_no_delay_when_already_delivered():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    td = TrackingData(current_status=NormalizedStatus.DELIVERED,
                      dates=Dates(eta=DateInfo(datetime=past)))
    risk = assess_risk(td)
    assert risk.delay_detected is False
    assert risk.risk_level == RiskLevel.LOW


def test_exception_status_gives_high_risk():
    td = TrackingData(current_status=NormalizedStatus.EXCEPTION)
    risk = assess_risk(td)
    assert risk.risk_level == RiskLevel.HIGH
    assert "exception_status" in risk.reasons


def test_exception_with_past_eta_is_high_risk():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    td = TrackingData(current_status=NormalizedStatus.EXCEPTION,
                      dates=Dates(eta=DateInfo(datetime=past)))
    risk = assess_risk(td)
    assert risk.risk_level == RiskLevel.HIGH
    assert "exception_status" in risk.reasons
    assert "past_eta" in risk.reasons


def test_tz_naive_eta_treated_as_utc():
    past_naive = datetime.now() - timedelta(days=1)
    assert past_naive.tzinfo is None
    td = TrackingData(current_status=NormalizedStatus.IN_TRANSIT,
                      dates=Dates(eta=DateInfo(datetime=past_naive)))
    risk = assess_risk(td)
    assert risk.delay_detected is True


def test_no_eta_returns_low_risk():
    td = TrackingData(current_status=NormalizedStatus.IN_TRANSIT)
    risk = assess_risk(td)
    assert risk.delay_detected is False
    assert risk.risk_level == RiskLevel.LOW
    assert risk.reasons == []
