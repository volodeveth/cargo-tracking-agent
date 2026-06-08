import re
from ..models.enums import NumberType

_AWB_RE = re.compile(r"^\d{3}-?\d{8}$")
_CONTAINER_RE = re.compile(r"^[A-Z]{4}\d{7}$")


def normalize_number(number: str) -> str:
    return re.sub(r"\s+", "", number.strip().upper())


def detect_type(number: str) -> NumberType:
    n = normalize_number(number)
    if _AWB_RE.match(n):
        return NumberType.AIR_AWB
    if _CONTAINER_RE.match(n):
        return NumberType.SEA_CONTAINER
    return NumberType.UNKNOWN


def iso6346_valid(number: str) -> bool:
    n = normalize_number(number)
    if not _CONTAINER_RE.match(n):
        return False
    letter_val = {}
    v = 10
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if v % 11 == 0:
            v += 1
        letter_val[c] = v
        v += 1
    total = 0
    for i, ch in enumerate(n[:10]):
        val = letter_val[ch] if ch.isalpha() else int(ch)
        total += val * (2 ** i)
    check = total % 11
    if check == 10:
        check = 0
    return check == int(n[10])
