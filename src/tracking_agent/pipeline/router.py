from __future__ import annotations
from ..models.enums import NumberType
from ..connectors.registry import all_connectors


def build_chain(number_type: NumberType, use_fixtures: bool):
    reg = all_connectors()
    chain = []
    if number_type == NumberType.AIR_AWB:
        chain = [reg["track-trace.com/aircargo"], reg["carrier_website"], reg["cargoai"]]
    elif number_type == NumberType.SEA_CONTAINER:
        chain = [reg["track-trace.com/container"], reg["carrier_website"]]
    if use_fixtures:
        chain.append(reg["fixtures"])
    return chain
