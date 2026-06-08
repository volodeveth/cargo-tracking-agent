from typing import Optional
import datetime as _dt
from pydantic import BaseModel, Field
from .enums import (
    NumberType, NormalizedStatus, ErrorCode, RiskLevel, TimezoneConfidence,
)


class ShipmentInput(BaseModel):
    id: Optional[str] = None
    number: str
    type: Optional[str] = None
    carrier: Optional[str] = None
    comment: Optional[str] = None


class Carrier(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    source: Optional[str] = None


class DetectedInfo(BaseModel):
    type: NumberType = NumberType.UNKNOWN
    normalized_number: Optional[str] = None
    carrier: Optional[Carrier] = None


class DateInfo(BaseModel):
    datetime: Optional[_dt.datetime] = None
    raw_datetime: Optional[str] = None
    timezone: Optional[str] = None
    timezone_confidence: TimezoneConfidence = TimezoneConfidence.UNKNOWN


class TrackingEvent(BaseModel):
    event_code: Optional[str] = None
    event_name: Optional[str] = None
    normalized_status: Optional[NormalizedStatus] = None
    location: Optional[str] = None
    datetime: Optional[_dt.datetime] = None
    raw_text: Optional[str] = None


class LastEvent(BaseModel):
    event_code: Optional[str] = None
    event_name: Optional[str] = None
    location: Optional[str] = None
    datetime: Optional[_dt.datetime] = None
    is_actual: Optional[bool] = None


class Dates(BaseModel):
    etd: Optional[DateInfo] = None
    eta: Optional[DateInfo] = None
    actual_departure: Optional[DateInfo] = None
    actual_arrival: Optional[DateInfo] = None


class Route(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    transit_points: list[str] = Field(default_factory=list)


class TrackingData(BaseModel):
    current_status: Optional[NormalizedStatus] = None
    raw_status: Optional[str] = None
    status_uk: Optional[str] = None
    last_event: Optional[LastEvent] = None
    dates: Dates = Field(default_factory=Dates)
    route: Route = Field(default_factory=Route)
    events: list[TrackingEvent] = Field(default_factory=list)


class SourceInfo(BaseModel):
    primary_source: Optional[str] = None
    final_source: Optional[str] = None
    url: Optional[str] = None
    retrieved_at: Optional[_dt.datetime] = None


class Quality(BaseModel):
    confidence: float = 0.0
    data_complete: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class Risk(BaseModel):
    risk_level: RiskLevel = RiskLevel.LOW
    delay_detected: bool = False
    reasons: list[str] = Field(default_factory=list)


class TrackingError(BaseModel):
    code: ErrorCode
    message: str
    source: Optional[str] = None


class DebugStep(BaseModel):
    step: str
    status: str
    result: Optional[str] = None
    url: Optional[str] = None
    events_count: Optional[int] = None


class ShipmentResult(BaseModel):
    input: ShipmentInput
    detected: DetectedInfo = Field(default_factory=DetectedInfo)
    tracking: Optional[TrackingData] = None
    source: SourceInfo = Field(default_factory=SourceInfo)
    quality: Quality = Field(default_factory=Quality)
    risk: Risk = Field(default_factory=Risk)
    errors: list[TrackingError] = Field(default_factory=list)
    debug: list[DebugStep] = Field(default_factory=list)


class Summary(BaseModel):
    total: int = 0
    success: int = 0
    failed: int = 0


class TrackingResponse(BaseModel):
    request_id: str
    checked_at: _dt.datetime
    summary: Summary
    results: list[ShipmentResult] = Field(default_factory=list)


class ShortResult(BaseModel):
    id: Optional[str] = None
    number: str
    type: NumberType
    current_status: Optional[NormalizedStatus] = None
    eta: Optional[_dt.datetime] = None
    etd: Optional[_dt.datetime] = None
    last_event_at: Optional[_dt.datetime] = None
    source: Optional[str] = None
    errors: list[TrackingError] = Field(default_factory=list)
