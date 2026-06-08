import asyncio
from types import SimpleNamespace

import tracking_agent.pipeline.orchestrator as orch
from tracking_agent.models.schemas import ShipmentInput
from tracking_agent.models.enums import NumberType


def _settings(**over):
    base = dict(use_fixtures=True, llm_enabled=False,
                llm_base_url="", llm_api_key="", llm_model="")
    base.update(over)
    return SimpleNamespace(**base)


def _run(monkeypatch, shipment):
    monkeypatch.setattr(orch, "get_settings", lambda: _settings())
    return asyncio.run(orch.process_shipment(shipment))


def test_type_hint_is_validated_not_trusted(monkeypatch):
    # number is clearly an AWB; a conflicting user type must NOT override detection
    res = _run(monkeypatch, ShipmentInput(id="a", number="080-38652331", type="container"))
    assert res.detected.type == NumberType.AIR_AWB
    assert "type_hint_ignored" in res.quality.warnings


def test_matching_type_hint_produces_no_warning(monkeypatch):
    res = _run(monkeypatch, ShipmentInput(id="a", number="080-38652331", type="air"))
    assert res.detected.type == NumberType.AIR_AWB
    assert "type_hint_ignored" not in res.quality.warnings


def test_carrier_hint_used_when_none_derived(monkeypatch):
    # containers have no carrier lookup -> user hint fills it, marked unverified
    res = _run(monkeypatch, ShipmentInput(id="c", number="TLLU4912250", carrier="Maersk"))
    assert res.detected.carrier is not None
    assert res.detected.carrier.name == "Maersk"
    assert res.detected.carrier.source == "user_provided"


def test_carrier_hint_ignored_when_conflicts_with_derived(monkeypatch):
    # AWB 080 resolves to LOT via prefix; a conflicting hint is flagged, not trusted
    res = _run(monkeypatch, ShipmentInput(id="a", number="080-38652331", carrier="Ryanair"))
    assert res.detected.carrier.name == "LOT Polish Airlines"
    assert res.detected.carrier.source == "awb_prefix"
    assert "carrier_hint_ignored" in res.quality.warnings


def test_comment_is_echoed(monkeypatch):
    res = _run(monkeypatch, ShipmentInput(id="a", number="080-38652331", comment="rush order"))
    assert res.input.comment == "rush order"
