from __future__ import annotations
import json
from pathlib import Path
from ..models.enums import NumberType
from .base import ConnectorResult, ConnectorStatus

_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures"


class FixtureConnector:
    name = "fixtures"
    supports = (NumberType.AIR_AWB, NumberType.SEA_CONTAINER)

    def __init__(self, fixture_dir: Path = _FIXTURE_DIR):
        self._dir = fixture_dir
        self._index = json.loads((fixture_dir / "index.json").read_text(encoding="utf-8"))

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        entry = self._index.get(normalized_number)
        if entry is None:
            return ConnectorResult(status=ConnectorStatus.NOT_FOUND, source=self.name)
        if entry == "not_found":
            return ConnectorResult(status=ConnectorStatus.NOT_FOUND, source=self.name)
        html = (self._dir / entry).read_text(encoding="utf-8")
        return ConnectorResult(
            status=ConnectorStatus.OK, source=self.name,
            url=f"fixture://{entry}", raw_html=html,
        )
