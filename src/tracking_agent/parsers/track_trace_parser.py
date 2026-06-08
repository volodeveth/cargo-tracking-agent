from __future__ import annotations
from bs4 import BeautifulSoup
from ..models.enums import NumberType
from ..models.schemas import TrackingEvent, Dates, Route
from ..normalization.normalizer import normalize_status
from .dates import parse_datetime
from .base import ParsedTracking


def parse_track_trace(html: str, number_type: NumberType) -> ParsedTracking:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="results")
    events: list[TrackingEvent] = []
    if table:
        for row in table.find_all("tr")[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) < 3:
                continue
            raw_dt, status_text, location = cells[0], cells[1], cells[2]
            events.append(TrackingEvent(
                event_name=status_text,
                normalized_status=normalize_status(status_text, number_type),
                location=location,
                datetime=parse_datetime(raw_dt).datetime,
                raw_text=status_text,
            ))
    meta = soup.find("div", class_="meta")
    dates = Dates()
    route = Route()
    if meta:
        dates.eta = parse_datetime(meta.get("data-eta"))
        dates.etd = parse_datetime(meta.get("data-etd"))
        route.origin = meta.get("data-origin")
        route.destination = meta.get("data-destination")
    raw_status = events[-1].raw_text if events else None
    return ParsedTracking(raw_status=raw_status, events=events, dates=dates, route=route)
