import asyncio
from tracking_agent.pipeline.orchestrator import process_shipment
from tracking_agent.models.schemas import ShipmentInput
from tracking_agent.models.enums import NumberType, NormalizedStatus


def test_invalid_format_returns_error():
    res = asyncio.run(process_shipment(ShipmentInput(id="x", number="hello")))
    assert res.detected.type == NumberType.UNKNOWN
    assert res.errors[0].code.value == "INVALID_FORMAT"


def test_air_found_via_fixture():
    res = asyncio.run(process_shipment(ShipmentInput(id="a", number="080-38652331")))
    assert res.detected.type == NumberType.AIR_AWB
    assert res.tracking is not None
    assert res.tracking.current_status is not None
    assert res.tracking.status_uk


def test_not_found_number():
    res = asyncio.run(process_shipment(ShipmentInput(id="n", number="501-20285134")))
    assert res.tracking is None or res.tracking.current_status == NormalizedStatus.NOT_FOUND
    assert any(e.code.value == "NOT_FOUND" for e in res.errors)


def test_successful_tracking_has_no_transient_connector_errors():
    """Transient connector failures (SOURCE_UNAVAILABLE, LOGIN_REQUIRED) must not
    appear in result.errors when tracking ultimately succeeds via a later connector."""
    res = asyncio.run(process_shipment(ShipmentInput(id="a", number="080-38652331")))
    assert res.tracking is not None
    assert res.tracking.current_status is not None
    assert res.tracking.current_status != NormalizedStatus.NOT_FOUND
    transient_codes = {"SOURCE_UNAVAILABLE", "LOGIN_REQUIRED"}
    error_codes = {e.code.value for e in res.errors}
    assert error_codes.isdisjoint(transient_codes), (
        f"Transient connector errors leaked into result.errors: "
        f"{error_codes & transient_codes}"
    )
