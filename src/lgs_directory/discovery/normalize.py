"""Address and name normalization utilities for store deduplication."""

from __future__ import annotations

import re

# Street type abbreviation → canonical expansion
_STREET_ABBREVS: dict[str, str] = {
    "ST": "STREET",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "BLVD": "BOULEVARD",
    "DR": "DRIVE",
    "RD": "ROAD",
    "LN": "LANE",
    "CT": "COURT",
    "PL": "PLACE",
    "CIR": "CIRCLE",
    "TRL": "TRAIL",
    "PKWY": "PARKWAY",
    "HWY": "HIGHWAY",
    "WAY": "WAY",
    "SQ": "SQUARE",
    "LOOP": "LOOP",
    "TER": "TERRACE",
    "TERR": "TERRACE",
    "PT": "POINT",
    "ALY": "ALLEY",
    "PLZ": "PLAZA",
    "STE": "SUITE",
    "FLR": "FLOOR",
    "N": "NORTH",
    "S": "SOUTH",
    "E": "EAST",
    "W": "WEST",
    "NE": "NORTHEAST",
    "NW": "NORTHWEST",
    "SE": "SOUTHEAST",
    "SW": "SOUTHWEST",
}

# Pattern to detect suite/unit/apt numbers (stripped for matching)
_SUITE_PATTERN = re.compile(
    r"\b(?:STE|SUITE|UNIT|APT|APARTMENT|#|BLDG|BUILDING|FLOOR|FLR|RM|ROOM)\b\.?\s*\S*",
    re.IGNORECASE,
)

# US state name → 2-letter code
_STATE_NAMES: dict[str, str] = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX",
    "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC",
}

# Common store name suffixes to strip for matching (preserved in original)
_NAME_SUFFIXES = re.compile(
    r"\b(?:LLC|INC|INCORPORATED|CORP|CORPORATION|LTD|CO|COMPANY"
    r"|GAMES|GAMING|COMICS|CARDS|HOBBIES|HOBBY|TOYS|COLLECTIBLES)\b",
)


def _strip_punctuation(text: str) -> str:
    """Remove non-alphanumeric characters except spaces."""
    assert isinstance(text, str), "Input must be a string"
    result = re.sub(r"[^\w\s]", " ", text)
    assert isinstance(result, str)
    return result


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters to a single space and strip."""
    assert isinstance(text, str), "Input must be a string"
    result = re.sub(r"\s+", " ", text).strip()
    assert isinstance(result, str)
    return result


def _expand_abbreviations(street: str) -> str:
    """Expand street type abbreviations to canonical forms."""
    assert isinstance(street, str), "Input must be a string"
    words = street.split()
    expanded = []
    for word in words:
        canonical = _STREET_ABBREVS.get(word, word)
        expanded.append(canonical)
    result = " ".join(expanded)
    assert len(result) >= 0
    return result


def _strip_suite(street: str) -> tuple[str, str | None]:
    """Strip suite/unit/apt from street, returning (street, suite_part)."""
    assert isinstance(street, str), "Input must be a string"
    match = _SUITE_PATTERN.search(street)
    suite_part = match.group(0).strip() if match else None
    cleaned = _SUITE_PATTERN.sub("", street)
    cleaned = _collapse_whitespace(cleaned)
    assert isinstance(cleaned, str)
    return cleaned, suite_part


def _normalize_state(state: str) -> str:
    """Normalize state to 2-letter code."""
    assert isinstance(state, str), "Input must be a string"
    upper = state.upper().strip()
    # Already a 2-letter code
    if len(upper) == 2 and upper.isalpha():
        return upper
    # Full state name
    code = _STATE_NAMES.get(upper)
    assert code is not None or len(upper) == 2, f"Unknown state: {state}"
    return code if code is not None else upper


def _normalize_zip(zip_code: str) -> str:
    """Normalize ZIP to 5-digit form."""
    assert isinstance(zip_code, str), "Input must be a string"
    cleaned = zip_code.strip()
    # Take first 5 digits from ZIP+4
    if "-" in cleaned:
        cleaned = cleaned.split("-")[0]
    assert len(cleaned) == 5, f"Invalid ZIP after normalization: {cleaned}"
    return cleaned


def normalize_address(
    street: str, city: str, state: str, zip_code: str
) -> dict[str, str]:
    """Normalize an address to canonical form for matching.

    Returns a dict with keys: street, city, state, zip_code, and optionally suite.
    """
    assert isinstance(street, str) and len(street) > 0, "Street must be non-empty"
    assert isinstance(city, str) and len(city) > 0, "City must be non-empty"

    # Uppercase everything
    norm_street = street.upper()
    norm_city = city.upper()

    # Strip punctuation
    norm_street = _strip_punctuation(norm_street)
    norm_city = _strip_punctuation(norm_city)

    # Strip suite/unit before abbreviation expansion
    norm_street, suite = _strip_suite(norm_street)

    # Expand abbreviations
    norm_street = _expand_abbreviations(norm_street)

    # Collapse whitespace
    norm_street = _collapse_whitespace(norm_street)
    norm_city = _collapse_whitespace(norm_city)

    # Normalize state and ZIP
    norm_state = _normalize_state(state)
    norm_zip = _normalize_zip(zip_code)

    result: dict[str, str] = {
        "street": norm_street,
        "city": norm_city,
        "state": norm_state,
        "zip_code": norm_zip,
    }
    if suite is not None:
        result["suite"] = suite

    assert "street" in result and "city" in result
    return result


def normalize_name(name: str) -> str:
    """Normalize a store name to canonical form for matching.

    Strips common suffixes, punctuation, and whitespace. Returns uppercase.
    The original name should be preserved separately.
    """
    assert isinstance(name, str) and len(name) > 0, "Name must be non-empty"

    upper = name.upper()
    stripped = _strip_punctuation(upper)
    stripped = _NAME_SUFFIXES.sub("", stripped)
    result = _collapse_whitespace(stripped)

    assert isinstance(result, str) and len(result) >= 0
    return result
