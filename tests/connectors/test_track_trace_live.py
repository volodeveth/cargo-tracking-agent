import asyncio
from tracking_agent.connectors.track_trace_air import TrackTraceAirConnector
from tracking_agent.connectors.base import ConnectorStatus


def test_air_connector_maps_captcha(monkeypatch):
    c = TrackTraceAirConnector()

    async def fake_get(url, number):
        return ("<html>Please verify you are human captcha</html>", url)

    monkeypatch.setattr(c, "_get_page_html", fake_get)
    r = asyncio.run(c.fetch("080-38652331", c.supports[0]))
    assert r.status == ConnectorStatus.ERROR
    assert r.error_code.value == "CAPTCHA_REQUIRED"


def test_air_connector_maps_cf_challenge(monkeypatch):
    c = TrackTraceAirConnector()

    async def fake_get(url, number):
        return ("<html><div class='cf-challenge'>checking your browser</div></html>", url)

    monkeypatch.setattr(c, "_get_page_html", fake_get)
    r = asyncio.run(c.fetch("080-38652331", c.supports[0]))
    assert r.status == ConnectorStatus.ERROR
    assert r.error_code.value == "CAPTCHA_REQUIRED"


def test_air_connector_returns_ok_for_clean_html(monkeypatch):
    c = TrackTraceAirConnector()

    async def fake_get(url, number):
        return ("<html><body><table id='results'></table></body></html>", url)

    monkeypatch.setattr(c, "_get_page_html", fake_get)
    r = asyncio.run(c.fetch("080-38652331", c.supports[0]))
    assert r.status == ConnectorStatus.OK
    assert r.raw_html is not None


def test_air_connector_maps_timeout(monkeypatch):
    c = TrackTraceAirConnector()

    class FakeTimeoutError(Exception):
        pass

    FakeTimeoutError.__name__ = "TimeoutError"

    async def fake_get(url, number):
        raise FakeTimeoutError("timed out")

    monkeypatch.setattr(c, "_get_page_html", fake_get)
    r = asyncio.run(c.fetch("080-38652331", c.supports[0]))
    assert r.status == ConnectorStatus.ERROR
    assert r.error_code.value == "TIMEOUT"


def test_air_connector_maps_generic_error(monkeypatch):
    c = TrackTraceAirConnector()

    async def fake_get(url, number):
        raise ConnectionError("network down")

    monkeypatch.setattr(c, "_get_page_html", fake_get)
    r = asyncio.run(c.fetch("080-38652331", c.supports[0]))
    assert r.status == ConnectorStatus.ERROR
    assert r.error_code.value == "SOURCE_UNAVAILABLE"
