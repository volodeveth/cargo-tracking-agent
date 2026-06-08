# AWB prefix (first 3 digits) -> (airline name, IATA code).
# Representative subset; extend freely — not exhaustive by design.
AWB_PREFIXES: dict[str, tuple[str, str]] = {
    "020": ("Lufthansa Cargo", "LH"),
    "074": ("KLM", "KL"),
    "080": ("LOT Polish Airlines", "LO"),
    "125": ("British Airways", "BA"),
    "157": ("Qatar Airways", "QR"),
    "176": ("Emirates SkyCargo", "EK"),
    "235": ("Turkish Airlines", "TK"),
    "501": ("United Airlines", "UA"),
}


def lookup_awb_carrier(normalized_number: str):
    prefix = normalized_number.replace("-", "")[:3]
    if prefix in AWB_PREFIXES:
        name, code = AWB_PREFIXES[prefix]
        return {"name": name, "code": code, "source": "awb_prefix"}
    return None
