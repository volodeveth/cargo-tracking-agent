from __future__ import annotations
from ..models.enums import NumberType, ErrorCode
from .base import ConnectorResult, ConnectorStatus


class CarrierWebsiteConnector:
    name = "carrier_website"
    supports = (NumberType.AIR_AWB, NumberType.SEA_CONTAINER)

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        # Extension point: per-carrier subclasses implement real scraping.
        return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                               error_code=ErrorCode.SOURCE_UNAVAILABLE,
                               error_message="No carrier-specific connector configured")
