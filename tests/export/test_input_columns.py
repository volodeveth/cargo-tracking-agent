import io

import openpyxl

from tracking_agent.api.web import _parse_csv, _parse_xlsx
from tracking_agent.cli import _load


def test_parse_csv_reads_optional_columns():
    data = b"id,number,type,carrier,comment\nx1,080-38652331,air,LOT,urgent\n"
    s = _parse_csv(data)
    assert s[0].type == "air"
    assert s[0].carrier == "LOT"
    assert s[0].comment == "urgent"


def test_parse_xlsx_reads_optional_columns():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["id", "number", "type", "carrier", "comment"])
    ws.append(["x1", "080-38652331", "air", "LOT", "urgent"])
    buf = io.BytesIO()
    wb.save(buf)
    s = _parse_xlsx(buf.getvalue())
    assert s[0].type == "air"
    assert s[0].carrier == "LOT"
    assert s[0].comment == "urgent"


def test_cli_load_csv_reads_optional_columns(tmp_path):
    p = tmp_path / "in.csv"
    p.write_text("id,number,type,carrier,comment\nx,080-38652331,air,LOT,note\n",
                 encoding="utf-8")
    s = _load(str(p))
    assert s[0].type == "air"
    assert s[0].carrier == "LOT"
    assert s[0].comment == "note"
