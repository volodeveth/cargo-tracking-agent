import asyncio
from types import SimpleNamespace

import tracking_agent.pipeline.orchestrator as orch
import tracking_agent.pipeline.builder as builder
from tracking_agent.connectors.base import ConnectorResult, ConnectorStatus
from tracking_agent.models.enums import NumberType
from tracking_agent.models.schemas import ShipmentInput, ShipmentResult


# --- §11 retry of transient network errors ---

def test_fetch_with_retry_recovers_after_transient_errors():
    class Flaky:
        name = "flaky"

        def __init__(self):
            self.calls = 0

        async def fetch(self, number, number_type):
            self.calls += 1
            if self.calls < 3:
                return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                                       error_code="SOURCE_UNAVAILABLE")
            return ConnectorResult(status=ConnectorStatus.OK, source=self.name, raw_html="<html/>")

    c = Flaky()
    cr = asyncio.run(orch._fetch_with_retry(c, "X", NumberType.AIR_AWB, retries=2))
    assert cr.status == ConnectorStatus.OK
    assert c.calls == 3  # initial attempt + 2 retries


def test_fetch_with_retry_does_not_retry_non_transient():
    class Captcha:
        name = "c"

        def __init__(self):
            self.calls = 0

        async def fetch(self, number, number_type):
            self.calls += 1
            return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                                   error_code="CAPTCHA_REQUIRED")

    c = Captcha()
    asyncio.run(orch._fetch_with_retry(c, "X", NumberType.AIR_AWB, retries=2))
    assert c.calls == 1  # CAPTCHA is permanent -> no retry


# --- §11 per-number timeout ---

def test_build_response_times_out_per_number(monkeypatch):
    async def slow(inp):
        await asyncio.sleep(5)
        return ShipmentResult(input=inp)

    monkeypatch.setattr(builder, "process_shipment", slow)
    monkeypatch.setattr(builder, "get_settings", lambda: SimpleNamespace(number_timeout=0.05))
    resp = asyncio.run(builder.build_response(
        [ShipmentInput(id="a", number="080-38652331")], request_id="t"))
    assert any(e.code.value == "TIMEOUT" for e in resp.results[0].errors)


# --- §11 debug artifacts & §9 PARSING_FAILED ---

def _full_settings(**over):
    base = dict(use_fixtures=True, llm_enabled=False, llm_base_url="", llm_api_key="",
                llm_model="", source_retries=0, debug_artifacts=False, debug_dir="",
                number_timeout=60)
    base.update(over)
    return SimpleNamespace(**base)


def test_debug_artifacts_saved_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_settings",
                        lambda: _full_settings(debug_artifacts=True, debug_dir=str(tmp_path)))
    asyncio.run(orch.process_shipment(ShipmentInput(id="a", number="080-38652331")))
    assert list(tmp_path.glob("*.html")), "expected a debug HTML artifact to be written"


def test_no_debug_artifacts_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_settings",
                        lambda: _full_settings(debug_artifacts=False, debug_dir=str(tmp_path)))
    asyncio.run(orch.process_shipment(ShipmentInput(id="a", number="080-38652331")))
    assert not list(tmp_path.glob("*.html"))


def test_parsing_failed_when_page_fetched_but_unparseable(monkeypatch):
    # 999 fixture is a non-standard page: deterministic parser yields nothing and
    # the LLM is off, so the page was fetched but could not be parsed.
    monkeypatch.setattr(orch, "get_settings", lambda: _full_settings())
    res = asyncio.run(orch.process_shipment(ShipmentInput(id="s", number="999-88887777")))
    assert any(e.code.value == "PARSING_FAILED" for e in res.errors)
