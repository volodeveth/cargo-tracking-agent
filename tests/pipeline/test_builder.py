import asyncio
from tracking_agent.pipeline.builder import build_response, to_short
from tracking_agent.models.schemas import ShipmentInput


def test_build_response_summary():
    inputs = [ShipmentInput(id="a", number="080-38652331"),
              ShipmentInput(id="b", number="hello")]
    resp = asyncio.run(build_response(inputs, request_id="r1"))
    assert resp.summary.total == 2
    assert resp.summary.success + resp.summary.failed == 2
    short = to_short(resp.results[0])
    assert short.number == "080-38652331"


def test_successfully_tracked_with_partial_data_counts_as_success():
    """A shipment tracked successfully (even with PARTIAL_DATA) must count as
    success=1, failed=0 — PARTIAL_DATA is non-blocking."""
    inputs = [ShipmentInput(id="a", number="080-38652331")]
    resp = asyncio.run(build_response(inputs, request_id="r"))
    assert resp.summary.success == 1, (
        f"Expected success=1 but got {resp.summary.success}; "
        f"errors={[e.code.value for e in resp.results[0].errors]}"
    )
    assert resp.summary.failed == 0


def test_invalid_format_counts_as_failed():
    """An invalid-format number that never gets tracking data must count as failed."""
    inputs = [ShipmentInput(id="b", number="hello")]
    resp = asyncio.run(build_response(inputs, request_id="r"))
    assert resp.summary.success == 0
    assert resp.summary.failed == 1


def test_not_found_counts_as_failed():
    """A not-found number must count as failed in the summary."""
    inputs = [ShipmentInput(id="n", number="501-20285134")]
    resp = asyncio.run(build_response(inputs, request_id="r"))
    assert resp.summary.success == 0
    assert resp.summary.failed == 1
