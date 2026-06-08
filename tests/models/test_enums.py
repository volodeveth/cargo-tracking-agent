from tracking_agent.models.enums import NumberType, NormalizedStatus, ErrorCode, RiskLevel

def test_enums_have_required_members():
    assert NumberType.AIR_AWB.value == "air_awb"
    assert NumberType.SEA_CONTAINER.value == "sea_container"
    assert NumberType.UNKNOWN.value == "unknown"
    assert NormalizedStatus.DELIVERED.value == "delivered"
    assert NormalizedStatus.CONTAINER_PICKED_UP.value == "container_picked_up"
    assert ErrorCode.CAPTCHA_REQUIRED.value == "CAPTCHA_REQUIRED"
    assert RiskLevel.HIGH.value == "high"
