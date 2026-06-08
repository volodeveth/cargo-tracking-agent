import asyncio
from tracking_agent.llm.assistant import LLMAssistant
from tracking_agent.models.enums import NormalizedStatus, NumberType


def test_disabled_returns_none():
    a = LLMAssistant(enabled=False, base_url="", api_key="", model="")
    assert asyncio.run(a.normalize_unknown("weird status", "air_awb")) is None


# --- #5: explanation of incomplete data ---

def test_explain_incomplete_disabled_returns_none():
    a = LLMAssistant(enabled=False, base_url="", api_key="", model="")
    out = asyncio.run(a.explain_incomplete(["eta", "actual_arrival"], "in_transit", "fixtures"))
    assert out is None


def test_explain_incomplete_returns_text(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return "Джерело не надало дату прибуття, тому ETA відсутня."

    monkeypatch.setattr(a, "_call", fake_call)
    out = asyncio.run(a.explain_incomplete(["eta", "actual_arrival"], "in_transit", "fixtures"))
    assert out == "Джерело не надало дату прибуття, тому ETA відсутня."


def test_explain_incomplete_swallows_errors(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def boom(prompt):
        raise RuntimeError("network")

    monkeypatch.setattr(a, "_call", boom)
    assert asyncio.run(a.explain_incomplete(["eta"], "in_transit", "fixtures")) is None


# --- #3: extracting events from semi-structured text ---

def test_extract_events_disabled_returns_empty():
    a = LLMAssistant(enabled=False, base_url="", api_key="", model="")
    assert asyncio.run(a.extract_events("some text", NumberType.AIR_AWB)) == []


def test_extract_events_parses_json_and_normalizes_status(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return (
            '[{"event_name": "Departed from origin", "location": "HKG", '
            '"datetime": "2026-06-05 18:45:00+0800", "raw_text": "DEP HKG"}]'
        )

    monkeypatch.setattr(a, "_call", fake_call)
    events = asyncio.run(a.extract_events("freeform page text", NumberType.AIR_AWB))
    assert len(events) == 1
    ev = events[0]
    assert ev.event_name == "Departed from origin"
    assert ev.location == "HKG"
    # status is derived deterministically from rules, not invented by the LLM
    assert ev.normalized_status == NormalizedStatus.DEPARTED
    assert ev.datetime is not None


def test_extract_events_handles_code_fences(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return '```json\n[{"event_name": "Arrived at destination", "location": "MAN"}]\n```'

    monkeypatch.setattr(a, "_call", fake_call)
    events = asyncio.run(a.extract_events("text", NumberType.AIR_AWB))
    assert len(events) == 1
    assert events[0].normalized_status == NormalizedStatus.ARRIVED


def test_extract_events_drops_invalid_datetime(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return '[{"event_name": "Customs clearance", "datetime": "yesterday afternoon"}]'

    monkeypatch.setattr(a, "_call", fake_call)
    events = asyncio.run(a.extract_events("text", NumberType.AIR_AWB))
    assert len(events) == 1
    # unparseable date is discarded, never guessed
    assert events[0].datetime is None
    assert events[0].normalized_status == NormalizedStatus.CUSTOMS


def test_extract_events_invalid_json_returns_empty(monkeypatch):
    a = LLMAssistant(enabled=True, base_url="http://x", api_key="k", model="m")

    async def fake_call(prompt):
        return "I could not find any tracking events on this page."

    monkeypatch.setattr(a, "_call", fake_call)
    assert asyncio.run(a.extract_events("text", NumberType.AIR_AWB)) == []


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
