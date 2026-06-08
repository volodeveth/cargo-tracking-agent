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
