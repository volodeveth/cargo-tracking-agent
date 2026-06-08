import asyncio
from tracking_agent.llm.assistant import LLMAssistant
from tracking_agent.models.enums import NormalizedStatus


def test_disabled_returns_none():
    a = LLMAssistant(enabled=False, base_url="", api_key="", model="")
    assert asyncio.run(a.normalize_unknown("weird status", "air_awb")) is None


def test_validates_against_enum(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return "departed"

    monkeypatch.setattr(a, "_call", fake_call)
    assert asyncio.run(a.normalize_unknown("left the airport", "air_awb")) == NormalizedStatus.DEPARTED


def test_rejects_invalid_enum(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return "teleported"

    monkeypatch.setattr(a, "_call", fake_call)
    assert asyncio.run(a.normalize_unknown("x", "air_awb")) is None
