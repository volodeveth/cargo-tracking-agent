from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol
from ..models.enums import NumberType, ErrorCode


class ConnectorStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ConnectorResult:
    status: ConnectorStatus
    source: str
    url: Optional[str] = None
    raw_html: Optional[str] = None
    raw_json: Optional[dict] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None


class Connector(Protocol):
    name: str
    supports: tuple[NumberType, ...]

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        ...
