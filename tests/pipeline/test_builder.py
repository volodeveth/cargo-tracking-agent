import asyncio
import tracking_agent.pipeline.builder as builder
from tracking_agent.pipeline.builder import build_response, to_short
from tracking_agent.models.schemas import ShipmentInput, ShipmentResult


def test_build_response_isolates_per_item_exceptions(monkeypatch):
    """One shipment raising must not sink the batch (ТЗ §13: independent processing)."""
    async def flaky(inp):
        if inp.number == "BOOM":
            raise RuntimeError("unexpected downstream failure")
        return ShipmentResult(input=inp)

    monkeypatch.setattr(builder, "process_shipment", flaky)
    inputs = [ShipmentInput(id="ok1", number="080-38652331"),
              ShipmentInput(id="bad", number="BOOM"),
              ShipmentInput(id="ok2", number="TLLU4912250")]
    resp = asyncio.run(builder.build_response(inputs, request_id="t"))

    assert resp.summary.total == 3
    assert [r.input.id for r in resp.results] == ["ok1", "bad", "ok2"]  # order kept
    bad = resp.results[1]
    assert bad.input.number == "BOOM"
    assert any(e.code.value == "INTERNAL_ERROR" for e in bad.errors)
    assert resp.results[0].errors == [] and resp.results[2].errors == []


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
