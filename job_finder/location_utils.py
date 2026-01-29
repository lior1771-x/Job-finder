"""Location normalization utilities."""

import ast
import re
from typing import Optional


# Standard location mappings - use word boundaries to avoid partial matches
CITY_ALIASES = {
    # US Cities (only abbreviations/alternate names, not substrings)
    "sf": "San Francisco",
    "san fran": "San Francisco",
    "nyc": "New York",
    "la": "Los Angeles",
    "dc": "Washington DC",
    "washington, d.c.": "Washington DC",
    "washington d.c.": "Washington DC",
    # International
    "london, uk": "London, UK",
    "london, united kingdom": "London, UK",
    "bangalore": "Bengaluru",
    "bombay": "Mumbai",
}

COUNTRY_ALIASES = {
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    "united kingdom": "UK",
    "great britain": "UK",
    "deutschland": "Germany",
    "brasil": "Brazil",
}

STATE_ABBREV = {
    "california": "CA",
    "new york": "NY",
    "texas": "TX",
    "washington": "WA",
    "colorado": "CO",
    "oregon": "OR",
    "massachusetts": "MA",
    "illinois": "IL",
    "georgia": "GA",
    "florida": "FL",
    "pennsylvania": "PA",
    "british columbia": "BC",
    "ontario": "ON",
}


def normalize_location(raw_location: str) -> str:
    """
    Normalize a location string to a standard format.

    Returns format like: "City, State/Country" or "Remote" or "City (Remote)"
    """
    if not raw_location or raw_location == "Unknown":
        return "Unknown"

    location = raw_location.strip()

    # Check if it's a dict-like string and parse it
    if location.startswith("{") and location.endswith("}"):
        location = _parse_dict_location(location)

    # Extract remote indicator
    is_remote = _is_remote(location)

    # Clean up the location string
    location = _clean_location(location)

    # Normalize city names
    location = _normalize_city(location)

    # Normalize country/state
    location = _normalize_region(location)

    # Add remote indicator back if needed
    if is_remote and "remote" not in location.lower():
        if location and location != "Unknown":
            location = f"{location} (Remote)"
        else:
            location = "Remote"

    return location if location else "Unknown"


def _parse_dict_location(location: str) -> str:
    """Parse a dict-like location string."""
    try:
        # Try to parse as Python dict
        loc_dict = ast.literal_eval(location)
        if isinstance(loc_dict, dict):
            city = loc_dict.get("city", "")
            region = loc_dict.get("region", "")
            country = loc_dict.get("countryName", loc_dict.get("country", ""))

            parts = []
            if city:
                parts.append(city)
            if region and region != city:
                # Abbreviate US states
                region_lower = region.lower()
                if region_lower in STATE_ABBREV:
                    region = STATE_ABBREV[region_lower]
                parts.append(region)
            if country and country not in ["United States", "USA"] and len(parts) < 2:
                parts.append(country)

            return ", ".join(parts) if parts else "Unknown"
    except (ValueError, SyntaxError):
        pass
    return location


def _is_remote(location: str) -> bool:
    """Check if location indicates remote work."""
    location_lower = location.lower()
    remote_indicators = ["remote", "work from home", "wfh", "distributed"]
    return any(ind in location_lower for ind in remote_indicators)


def _clean_location(location: str) -> str:
    """Clean up location string."""
    # Remove (Remote) suffix temporarily
    location = re.sub(r'\s*\(remote\)\s*', ' ', location, flags=re.IGNORECASE)

    # Remove "Locations" suffix
    location = re.sub(r'\s+locations?\s*$', '', location, flags=re.IGNORECASE)

    # Handle "XX-Remote-Location" pattern (e.g., "CA-Remote-British Columbia")
    match = re.match(r'^[A-Z]{2}-Remote-(.+)$', location)
    if match:
        location = match.group(1)

    # Remove country prefixes like "US-", "IE-"
    location = re.sub(r'^[A-Z]{2}-', '', location)

    # Handle "Remote-State (National)" patterns
    location = re.sub(r'Remote-([A-Z]{2})\s*\(National\)', r'\1', location)

    # Remove (National) markers
    location = re.sub(r'\s*\(National\)\s*', ' ', location, flags=re.IGNORECASE)

    # Clean up multiple locations - take first one
    if ", US-" in location or ", IE-" in location:
        location = location.split(",")[0].strip()

    # Remove (HQ) markers
    location = re.sub(r'\s*\(HQ\)\s*', ' ', location, flags=re.IGNORECASE)

    # Clean extra whitespace
    location = " ".join(location.split())

    return location.strip()


def _normalize_city(location: str) -> str:
    """Normalize city names using word boundaries."""
    for alias, standard in CITY_ALIASES.items():
        # Use word boundaries to avoid partial matches (e.g., "sf" shouldn't match "San Francisco")
        pattern = r'\b' + re.escape(alias) + r'\b'
        location = re.sub(pattern, standard, location, flags=re.IGNORECASE)

    return location


def _normalize_region(location: str) -> str:
    """Normalize country and state names."""
    # Normalize countries
    for alias, standard in COUNTRY_ALIASES.items():
        pattern = r'\b' + re.escape(alias) + r'\b'
        location = re.sub(pattern, standard, location, flags=re.IGNORECASE)

    return location


def extract_search_terms(location: str) -> list[str]:
    """
    Extract searchable terms from a normalized location.
    Used for filtering - returns terms that should match.
    """
    terms = []
    location_lower = location.lower()

    # Add the full location
    terms.append(location_lower)

    # Add individual parts
    parts = re.split(r'[,\(\)]', location)
    for part in parts:
        part = part.strip().lower()
        if part and part not in ["remote"]:
            terms.append(part)

    # Add "remote" if applicable
    if "remote" in location_lower:
        terms.append("remote")

    return list(set(terms))
