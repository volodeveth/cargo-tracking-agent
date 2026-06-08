import asyncio
from types import SimpleNamespace

import tracking_agent.pipeline.orchestrator as orch
import tracking_agent.llm.assistant as assistant_mod
from tracking_agent.models.schemas import ShipmentInput, TrackingEvent
from tracking_agent.models.enums import NormalizedStatus


def _settings(**over):
    base = dict(
        use_fixtures=True,
        llm_enabled=True,
        llm_base_url="http://x",
        llm_api_key="k",
        llm_model="m",
        source_retries=0,
        debug_artifacts=False,
        debug_dir="",
        number_timeout=60,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _install_fake_llm(monkeypatch, *, extract=None, explanation=None, normalize=None):
    class FakeAssistant:
        def __init__(self, *a, **k):
            pass

        async def extract_events(self, text, number_type):
            return list(extract or [])

        async def explain_incomplete(self, missing_fields, status, source=None):
            return explanation

        async def normalize_unknown(self, raw_status, number_type):
            return normalize

    monkeypatch.setattr(assistant_mod, "LLMAssistant", FakeAssistant)


def test_explanation_attached_when_data_incomplete(monkeypatch):
    monkeypatch.setattr(orch, "get_settings", lambda: _settings())
    _install_fake_llm(monkeypatch, explanation="Перевізник не опублікував ETA, тому дата прибуття відсутня.")

    res = asyncio.run(orch.process_shipment(ShipmentInput(id="a", number="080-38652331")))

    assert res.quality.missing_fields  # the air fixture lacks actual_* dates
    assert res.quality.explanation == "Перевізник не опублікував ETA, тому дата прибуття відсутня."


def test_no_explanation_when_llm_disabled(monkeypatch):
    monkeypatch.setattr(orch, "get_settings", lambda: _settings(llm_enabled=False))
    _install_fake_llm(monkeypatch, explanation="should not be used")

    res = asyncio.run(orch.process_shipment(ShipmentInput(id="a", number="080-38652331")))

    assert res.quality.missing_fields
    assert res.quality.explanation is None


def test_events_extracted_from_semi_structured_page(monkeypatch):
    monkeypatch.setattr(orch, "get_settings", lambda: _settings())
    recovered = [
        TrackingEvent(event_name="Departed from origin airport (DEP)",
                      normalized_status=NormalizedStatus.DEPARTED, location="HKG"),
    ]
    _install_fake_llm(monkeypatch, extract=recovered)

    res = asyncio.run(orch.process_shipment(ShipmentInput(id="s", number="999-88887777")))

    assert res.tracking is not None
    assert len(res.tracking.events) == 1
    assert res.tracking.current_status == NormalizedStatus.DEPARTED
    assert "events_extracted_by_llm" in res.quality.warnings


def test_no_extraction_when_deterministic_parser_succeeds(monkeypatch):
    monkeypatch.setattr(orch, "get_settings", lambda: _settings())
    # extractor would return junk, but it must never be consulted when the
    # deterministic parser already produced events
    junk = [TrackingEvent(event_name="WRONG", location="ZZZ")]
    _install_fake_llm(monkeypatch, extract=junk)

    res = asyncio.run(orch.process_shipment(ShipmentInput(id="a", number="080-38652331")))

    assert res.tracking is not None
    assert "events_extracted_by_llm" not in res.quality.warnings
    assert all(e.event_name != "WRONG" for e in res.tracking.events)
