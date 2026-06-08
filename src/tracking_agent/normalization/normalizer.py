from ..models.enums import NumberType, NormalizedStatus
from .rules_air import AIR_RULES
from .rules_container import CONTAINER_RULES


def normalize_status(raw: str | None, number_type: NumberType) -> NormalizedStatus:
    if not raw:
        return NormalizedStatus.UNKNOWN
    rules = AIR_RULES if number_type == NumberType.AIR_AWB else CONTAINER_RULES
    for pattern, status in rules:
        if pattern.search(raw):
            return status
    return NormalizedStatus.UNKNOWN
