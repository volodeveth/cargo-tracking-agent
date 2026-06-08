from __future__ import annotations
import io
from openpyxl import Workbook
from ..models.schemas import ShipmentResult

_HEADERS = ["id", "number", "type", "current_status", "status_uk",
            "eta", "etd", "risk_level", "delay_detected", "source", "errors"]


def _build_workbook(results: list[ShipmentResult]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "results"
    ws.append(_HEADERS)
    for r in results:
        td = r.tracking
        ws.append([
            r.input.id, r.input.number, r.detected.type.value,
            td.current_status.value if td and td.current_status else None,
            td.status_uk if td else None,
            td.dates.eta.datetime.isoformat() if td and td.dates.eta and td.dates.eta.datetime else None,
            td.dates.etd.datetime.isoformat() if td and td.dates.etd and td.dates.etd.datetime else None,
            r.risk.risk_level.value, r.risk.delay_detected,
            r.source.final_source,
            "; ".join(e.code.value for e in r.errors),
        ])
    return wb


def export_results(results: list[ShipmentResult], path: str) -> str:
    _build_workbook(results).save(path)
    return path


def export_results_bytes(results: list[ShipmentResult]) -> bytes:
    buf = io.BytesIO()
    _build_workbook(results).save(buf)
    return buf.getvalue()
