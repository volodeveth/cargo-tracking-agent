from tracking_agent.normalization.normalizer import normalize_status
from tracking_agent.normalization.translate_uk import to_ukrainian
from tracking_agent.models.enums import NumberType, NormalizedStatus


def test_air_departed():
    assert normalize_status("Departed from origin airport", NumberType.AIR_AWB) == NormalizedStatus.DEPARTED


def test_container_picked_up():
    assert normalize_status("Gate out empty", NumberType.SEA_CONTAINER) == NormalizedStatus.CONTAINER_PICKED_UP


def test_unmatched_returns_unknown():
    assert normalize_status("zzz", NumberType.AIR_AWB) == NormalizedStatus.UNKNOWN


def test_ua_translation_full_coverage():
    for s in NormalizedStatus:
        assert to_ukrainian(s)  # non-empty for every enum member
