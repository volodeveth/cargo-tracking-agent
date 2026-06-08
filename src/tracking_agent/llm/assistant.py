from __future__ import annotations
import json
import httpx
from ..models.enums import NormalizedStatus, NumberType
from ..models.schemas import TrackingEvent
from ..normalization.normalizer import normalize_status
from ..parsers.dates import parse_datetime

_ALLOWED = {s.value for s in NormalizedStatus}


def _extract_json_array(text: str):
    """Best-effort pull of a JSON array out of an LLM reply (handles code fences)."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None


class LLMAssistant:
    def __init__(self, enabled: bool, base_url: str, api_key: str, model: str):
        self.enabled = enabled and bool(api_key)
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    async def _call(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def normalize_unknown(self, raw_status: str, number_type: str):
        if not self.enabled:
            return None
        prompt = (
            f"Map this {number_type} tracking status to exactly one of "
            f"{sorted(_ALLOWED)}. Reply with only the value.\nStatus: {raw_status}"
        )
        try:
            answer = await self._call(prompt)
        except Exception:
            return None
        answer = answer.strip().strip('".').lower()
        if answer in _ALLOWED:
            return NormalizedStatus(answer)
        return None

    async def extract_events(self, text: str, number_type: NumberType) -> list[TrackingEvent]:
        """#3: pull tracking events out of semi-structured text when the
        deterministic parser found nothing. Statuses are normalized by the
        deterministic rules and dates are validated by the project parser, so
        the LLM never invents a status value or a date."""
        if not self.enabled:
            return []
        prompt = (
            "Extract tracking events from the text below as a JSON array. "
            "Each item: {\"event_name\": str, \"location\": str|null, "
            "\"datetime\": str|null, \"raw_text\": str}. "
            "Use ONLY information present in the text. Do not invent events, "
            "statuses or dates. If a field is absent, use null. "
            "If there are no events, reply with [].\n\nText:\n" + text
        )
        try:
            raw = await self._call(prompt)
        except Exception:
            return []
        data = _extract_json_array(raw)
        if not isinstance(data, list):
            return []
        events: list[TrackingEvent] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("event_name") or item.get("status")
            raw_dt = item.get("datetime")
            di = parse_datetime(raw_dt) if isinstance(raw_dt, str) else None
            events.append(TrackingEvent(
                event_name=name,
                normalized_status=normalize_status(name, number_type),
                location=item.get("location"),
                datetime=di.datetime if di else None,
                raw_text=item.get("raw_text") or name,
            ))
        return events

    async def explain_incomplete(self, missing_fields: list[str], status: str,
                                 source: str | None = None) -> str | None:
        """#5: short, user-facing explanation (Ukrainian) of why the data is
        incomplete. Grounded strictly in the list of missing fields — the model
        is told not to invent dates, statuses or facts."""
        if not self.enabled:
            return None
        prompt = (
            "Поясни українською, у 1-2 реченнях, чому дані трекінгу неповні. "
            "Спирайся ЛИШЕ на перелік відсутніх полів — не вигадуй дат, статусів "
            "чи фактів, яких немає. "
            f"Поточний статус: {status}. "
            f"Відсутні поля: {', '.join(missing_fields) or 'немає'}. "
            f"Джерело даних: {source or 'невідоме'}."
        )
        try:
            return await self._call(prompt)
        except Exception:
            return None
