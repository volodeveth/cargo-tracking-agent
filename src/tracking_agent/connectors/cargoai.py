from __future__ import annotations
from ..config import get_settings
from ..models.enums import NumberType, ErrorCode
from .base import ConnectorResult, ConnectorStatus


class CargoAiConnector:
    name = "cargoai"
    supports = (NumberType.AIR_AWB,)

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        settings = get_settings()
        if not settings.cargoai_api_key:
            return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                                   error_code=ErrorCode.LOGIN_REQUIRED,
                                   error_message="CargoAI API key not configured")
        # Real httpx call would go here when credentials exist.
        return ConnectorResult(status=ConnectorStatus.ERROR, source=self.name,
                               error_code=ErrorCode.SOURCE_UNAVAILABLE)
