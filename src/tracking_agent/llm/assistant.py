from __future__ import annotations
import httpx
from ..models.enums import NormalizedStatus

_ALLOWED = {s.value for s in NormalizedStatus}


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
            return resp.json()["choices"][0]["message"]["content"].strip().lower()

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
        answer = answer.strip().strip('".')
        if answer in _ALLOWED:
            return NormalizedStatus(answer)
        return None
