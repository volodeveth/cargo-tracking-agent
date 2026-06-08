from enum import Enum


class NumberType(str, Enum):
    AIR_AWB = "air_awb"
    SEA_CONTAINER = "sea_container"
    UNKNOWN = "unknown"


class NormalizedStatus(str, Enum):
    NOT_FOUND = "not_found"
    CREATED = "created"
    BOOKED = "booked"
    RECEIVED = "received"
    IN_ORIGIN_TERMINAL = "in_origin_terminal"
    DEPARTED = "departed"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    CUSTOMS = "customs"
    READY_FOR_PICKUP = "ready_for_pickup"
    DELIVERED = "delivered"
    CONTAINER_PICKED_UP = "container_picked_up"
    CONTAINER_RETURNED = "container_returned"
    EXCEPTION = "exception"
    UNKNOWN = "unknown"


class ErrorCode(str, Enum):
    INVALID_FORMAT = "INVALID_FORMAT"
    NOT_FOUND = "NOT_FOUND"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    PARSING_FAILED = "PARSING_FAILED"
    PARTIAL_DATA = "PARTIAL_DATA"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimezoneConfidence(str, Enum):
    SOURCE_PROVIDED = "source_provided"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
