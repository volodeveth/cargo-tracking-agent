from __future__ import annotations
import hashlib
import hmac
import json
import httpx


async def notify_status_change(url: str, secret: str, payload: dict,
                               retries: int = 2) -> bool:
    if not url:
        return False
    body = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest() if secret else ""
    headers = {"Content-Type": "application/json", "X-Signature": sig}
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(retries + 1):
            try:
                resp = await client.post(url, content=body, headers=headers)
                if resp.status_code < 400:
                    return True
            except httpx.HTTPError:
                pass
    return False
