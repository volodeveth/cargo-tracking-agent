import asyncio
import respx
import httpx
from tracking_agent.webhook.notifier import notify_status_change


@respx.mock
def test_webhook_posts_signed_payload():
    route = respx.post("https://hook.example/x").mock(return_value=httpx.Response(200))
    ok = asyncio.run(notify_status_change(
        "https://hook.example/x", "secret", {"number": "n", "old": "a", "new": "b"}))
    assert ok is True
    assert route.called
    sent = route.calls[0].request
    assert "X-Signature" in sent.headers


def test_webhook_noop_without_url():
    ok = asyncio.run(notify_status_change("", "", {"x": 1}))
    assert ok is False
