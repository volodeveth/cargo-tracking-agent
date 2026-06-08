from __future__ import annotations
import argparse
import asyncio
import csv
import json
import uuid
from .models.schemas import ShipmentInput
from .pipeline.builder import build_response


def _load(path: str) -> list[ShipmentInput]:
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            return [ShipmentInput(id=r.get("id"), number=r["number"])
                    for r in csv.DictReader(f)]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [ShipmentInput(**s) for s in data["shipments"]]


async def _run(inp: str, outp: str) -> None:
    shipments = _load(inp)
    resp = await build_response(shipments, request_id=f"cli-{uuid.uuid4().hex[:8]}")
    payload = resp.model_dump(mode="json")
    if outp:
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Cargo tracking agent")
    parser.add_argument("--input", required=True, help="Input file (.json or .csv)")
    parser.add_argument("--output", default="", help="Output file path (default: stdout)")
    args = parser.parse_args()
    asyncio.run(_run(args.input, args.output))


if __name__ == "__main__":
    main()
