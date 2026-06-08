from __future__ import annotations
import argparse
import asyncio
import csv
import json
import sys
import uuid
from .models.schemas import ShipmentInput
from .pipeline.builder import build_response
from .config import get_settings
from .export.excel import export_results
from .export.sheets import export_to_sheets


def _load(path: str) -> list[ShipmentInput]:
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            return [ShipmentInput(id=r.get("id"), number=r["number"])
                    for r in csv.DictReader(f)]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [ShipmentInput(**s) for s in data["shipments"]]


async def _run(inp: str, outp: str, fmt: str) -> None:
    shipments = _load(inp)
    resp = await build_response(shipments, request_id=f"cli-{uuid.uuid4().hex[:8]}")

    if fmt == "sheets":
        settings = get_settings()
        ok = export_to_sheets(resp.results, settings.sheets_spreadsheet_id,
                              settings.sheets_credentials_path)
        if ok:
            print("Exported to Google Sheets", file=sys.stderr)
            return
        print("Google Sheets export unavailable (no credentials/libraries); "
              "falling back to JSON", file=sys.stderr)
        fmt = "json"

    if fmt == "xlsx":
        target = outp or "output.xlsx"
        export_results(resp.results, target)
        print(f"Wrote {target}", file=sys.stderr)
        return

    payload = resp.model_dump(mode="json")
    if outp:
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Cargo tracking agent")
    parser.add_argument("--input", required=True, help="Input file (.json or .csv)")
    parser.add_argument("--output", default="", help="Output file path (default: stdout for json)")
    parser.add_argument("--format", choices=["json", "xlsx", "sheets"], default="json",
                        help="Output format (default: json)")
    args = parser.parse_args()
    asyncio.run(_run(args.input, args.output, args.format))


if __name__ == "__main__":
    main()
