import asyncio
from tracking_agent.scheduler.recheck import recheck_numbers


def test_recheck_returns_changed(monkeypatch, tmp_path):
    async def fake_process(s):
        from tracking_agent.models.schemas import ShipmentResult, TrackingData
        from tracking_agent.models.enums import NormalizedStatus
        r = ShipmentResult(input=s)
        r.tracking = TrackingData(current_status=NormalizedStatus.ARRIVED)
        return r
    monkeypatch.setattr("tracking_agent.scheduler.recheck.process_shipment", fake_process)
    changed = asyncio.run(recheck_numbers(
        [("internal-001", "080-38652331")], db_path=str(tmp_path / "r.db")))
    assert changed and changed[0]["new"] == "arrived"
