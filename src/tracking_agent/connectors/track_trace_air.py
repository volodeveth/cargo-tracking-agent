from __future__ import annotations
from ..config import get_settings
from ..models.enums import NumberType, ErrorCode
from .base import ConnectorResult, ConnectorStatus

_BLOCK_MARKERS = ("captcha", "are you human", "cf-challenge", "access denied")


class TrackTraceAirConnector:
    name = "track-trace.com/aircargo"
    supports = (NumberType.AIR_AWB,)
    url_template = "https://www.track-trace.com/aircargo"

    async def _get_page_html(self, url: str, number: str) -> tuple[str, str]:
        from playwright.async_api import async_playwright
        settings = get_settings()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=settings.track_trace_timeout * 1000)
                html = await page.content()
                final_url = page.url
            finally:
                await browser.close()
            return html, final_url

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        try:
            html, final_url = await self._get_page_html(self.url_template, normalized_number)
        except Exception as exc:
            name = type(exc).__name__
            code = ErrorCode.TIMEOUT if "Timeout" in name else ErrorCode.SOURCE_UNAVAILABLE
            return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                                   error_code=code, error_message=str(exc))
        low = html.lower()
        if any(m in low for m in _BLOCK_MARKERS):
            return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                                   url=final_url, error_code=ErrorCode.CAPTCHA_REQUIRED,
                                   error_message="Site requires CAPTCHA / blocks automation")
        return ConnectorResult(status=ConnectorStatus.OK, source=self.name,
                               url=final_url, raw_html=html)
