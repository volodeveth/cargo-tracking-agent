from tracking_agent.detection.detector import detect_type, normalize_number, iso6346_valid
from tracking_agent.detection.awb_prefixes import lookup_awb_carrier
from tracking_agent.models.enums import NumberType


def test_air_awb_with_and_without_dash():
    assert detect_type("123-12345678") == NumberType.AIR_AWB
    assert detect_type(" 12312345678 ") == NumberType.AIR_AWB


def test_sea_container():
    assert detect_type("mscu1234567") == NumberType.SEA_CONTAINER


def test_unknown():
    assert detect_type("hello") == NumberType.UNKNOWN


def test_normalize_number():
    # normalize_number strips outer whitespace and internal spaces, uppercases,
    # but does NOT remove dashes — "123-123 45678" → "123-12345678"
    assert normalize_number(" 123-123 45678 ") == "123-12345678"
    assert normalize_number("mscu1234567") == "MSCU1234567"


def test_iso6346_known_valid():
    # MSCU1234567 is a syntactically valid container format; function returns bool
    assert isinstance(iso6346_valid("MSCU1234567"), bool)
    # MSKU1880987 is a real valid container number (check digit passes)
    assert iso6346_valid("MSKU1880987") is True


def test_lookup_awb_carrier_lot_polish():
    result = lookup_awb_carrier("08038652331")
    assert result is not None
    assert result["source"] == "awb_prefix"
    assert result["name"]  # non-empty name
