from tracking_agent.models.schemas import (
    ShipmentInput, TrackingResponse, ShipmentResult, DateInfo,
)

def test_shipment_input_minimal():
    s = ShipmentInput(id="internal-001", number="123-12345678")
    assert s.number == "123-12345678"
    assert s.type is None

def test_dateinfo_defaults():
    d = DateInfo()
    assert d.datetime is None and d.timezone_confidence.value == "unknown"

def test_response_is_schema_stable_when_empty():
    r = TrackingResponse(request_id="x", checked_at="2026-06-08T00:00:00Z",
                         summary={"total": 0, "success": 0, "failed": 0}, results=[])
    dumped = r.model_dump()
    assert dumped["summary"]["total"] == 0
    assert dumped["results"] == []
