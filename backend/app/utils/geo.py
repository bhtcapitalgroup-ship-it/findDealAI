"""
RealDeal AI - Geocoding Utilities

Provides geocoding, reverse geocoding, distance calculations,
zip code lookups, and geographic bounding box operations.
"""

import logging
import math
import os
from functools import lru_cache
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GEOCODING_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Earth radius in miles
EARTH_RADIUS_MILES = 3958.8
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    unit: str = "miles",
) -> float:
    """
    Calculate the great-circle distance between two points
    on Earth using the Haversine formula.

    Args:
        lat1, lon1: Coordinates of point 1 (degrees)
        lat2, lon2: Coordinates of point 2 (degrees)
        unit: "miles" or "km"

    Returns:
        Distance in the specified unit.
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    radius = EARTH_RADIUS_MILES if unit == "miles" else EARTH_RADIUS_KM
    return round(radius * c, 4)


def bounding_box(
    lat: float,
    lon: float,
    radius_miles: float,
) -> dict[str, float]:
    """
    Calculate a bounding box around a point at a given radius.

    Returns {"min_lat", "max_lat", "min_lon", "max_lon"}.
    """
    lat_r = math.radians(lat)

    # Latitude: 1 degree ~ 69 miles
    delta_lat = radius_miles / 69.0

    # Longitude: depends on latitude
    delta_lon = radius_miles / (69.0 * math.cos(lat_r))

    return {
        "min_lat": round(lat - delta_lat, 6),
        "max_lat": round(lat + delta_lat, 6),
        "min_lon": round(lon - delta_lon, 6),
        "max_lon": round(lon + delta_lon, 6),
    }


def is_within_radius(
    lat1: float, lon1: float, lat2: float, lon2: float, radius_miles: float
) -> bool:
    """Check if two points are within a given radius."""
    return haversine_distance(lat1, lon1, lat2, lon2) <= radius_miles


# ---------------------------------------------------------------------------
# Zip code utilities (embedded lookup for common codes)
# ---------------------------------------------------------------------------

# Partial mapping of major city zip code ranges for fast lookup
MAJOR_CITY_ZIPS: dict[str, dict[str, Any]] = {
    "75201": {"city": "Dallas", "state": "TX", "lat": 32.789, "lon": -96.798, "county": "Dallas"},
    "75202": {"city": "Dallas", "state": "TX", "lat": 32.782, "lon": -96.800, "county": "Dallas"},
    "77001": {"city": "Houston", "state": "TX", "lat": 29.752, "lon": -95.358, "county": "Harris"},
    "78201": {"city": "San Antonio", "state": "TX", "lat": 29.468, "lon": -98.525, "county": "Bexar"},
    "73301": {"city": "Austin", "state": "TX", "lat": 30.326, "lon": -97.771, "county": "Travis"},
    "32099": {"city": "Jacksonville", "state": "FL", "lat": 30.332, "lon": -81.656, "county": "Duval"},
    "33601": {"city": "Tampa", "state": "FL", "lat": 27.950, "lon": -82.457, "county": "Hillsborough"},
    "32801": {"city": "Orlando", "state": "FL", "lat": 28.538, "lon": -81.379, "county": "Orange"},
    "30301": {"city": "Atlanta", "state": "GA", "lat": 33.749, "lon": -84.388, "county": "Fulton"},
    "28201": {"city": "Charlotte", "state": "NC", "lat": 35.227, "lon": -80.843, "county": "Mecklenburg"},
    "27601": {"city": "Raleigh", "state": "NC", "lat": 35.780, "lon": -78.638, "county": "Wake"},
    "37201": {"city": "Nashville", "state": "TN", "lat": 36.163, "lon": -86.782, "county": "Davidson"},
    "38101": {"city": "Memphis", "state": "TN", "lat": 35.149, "lon": -90.049, "county": "Shelby"},
    "46201": {"city": "Indianapolis", "state": "IN", "lat": 39.768, "lon": -86.158, "county": "Marion"},
    "43201": {"city": "Columbus", "state": "OH", "lat": 39.961, "lon": -82.999, "county": "Franklin"},
    "44101": {"city": "Cleveland", "state": "OH", "lat": 41.499, "lon": -81.694, "county": "Cuyahoga"},
    "85001": {"city": "Phoenix", "state": "AZ", "lat": 33.448, "lon": -112.074, "county": "Maricopa"},
    "89101": {"city": "Las Vegas", "state": "NV", "lat": 36.171, "lon": -115.144, "county": "Clark"},
    "90001": {"city": "Los Angeles", "state": "CA", "lat": 33.941, "lon": -118.249, "county": "Los Angeles"},
    "10001": {"city": "New York", "state": "NY", "lat": 40.750, "lon": -73.997, "county": "New York"},
}


def lookup_zip(zip_code: str) -> Optional[dict[str, Any]]:
    """
    Look up city, state, lat/lon, and county for a zip code.
    Uses embedded data for common codes, falls back to API.
    """
    zip_code = zip_code.strip()[:5]

    # Check embedded lookup
    if zip_code in MAJOR_CITY_ZIPS:
        return MAJOR_CITY_ZIPS[zip_code]

    # In production, this would query a zip code database or API
    logger.debug("Zip code %s not in embedded lookup", zip_code)
    return None


def zip_to_coords(zip_code: str) -> Optional[tuple[float, float]]:
    """Return (latitude, longitude) for a zip code."""
    data = lookup_zip(zip_code)
    if data:
        return (data["lat"], data["lon"])
    return None


def city_state_to_coords(city: str, state: str) -> Optional[tuple[float, float]]:
    """Look up approximate coordinates for a city/state."""
    # Search embedded data
    target = (city.lower(), state.upper())
    for zip_data in MAJOR_CITY_ZIPS.values():
        if (zip_data["city"].lower(), zip_data["state"]) == target:
            return (zip_data["lat"], zip_data["lon"])
    return None


# ---------------------------------------------------------------------------
# Google Maps Geocoding API
# ---------------------------------------------------------------------------


async def geocode_address(
    address: str,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    api_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Geocode an address using Google Maps API.

    Returns {
        "latitude": float,
        "longitude": float,
        "formatted_address": str,
        "place_id": str,
        "components": dict,
    }
    """
    key = api_key or GOOGLE_MAPS_API_KEY
    if not key:
        logger.warning("Google Maps API key not configured")
        return None

    full_address = address
    if city:
        full_address += f", {city}"
    if state:
        full_address += f", {state}"
    if zip_code:
        full_address += f" {zip_code}"

    params = {"address": full_address, "key": key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GEOCODING_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error("Geocoding API returned %d", resp.status)
                    return None

                data = await resp.json()

                if data.get("status") != "OK" or not data.get("results"):
                    logger.warning(
                        "Geocoding returned status %s for: %s",
                        data.get("status"),
                        full_address,
                    )
                    return None

                result = data["results"][0]
                location = result["geometry"]["location"]

                # Parse address components
                components: dict[str, str] = {}
                for comp in result.get("address_components", []):
                    for comp_type in comp.get("types", []):
                        components[comp_type] = comp.get("long_name", "")
                        components[f"{comp_type}_short"] = comp.get("short_name", "")

                return {
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "formatted_address": result.get("formatted_address", ""),
                    "place_id": result.get("place_id", ""),
                    "components": components,
                }

    except Exception as exc:
        logger.error("Geocoding failed for '%s': %s", full_address, exc)
        return None


async def reverse_geocode(
    latitude: float,
    longitude: float,
    api_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Reverse geocode coordinates to an address.

    Returns {
        "formatted_address": str,
        "street": str,
        "city": str,
        "state": str,
        "zip_code": str,
        "county": str,
    }
    """
    key = api_key or GOOGLE_MAPS_API_KEY
    if not key:
        return None

    params = {"latlng": f"{latitude},{longitude}", "key": key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GEOCODING_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                if data.get("status") != "OK" or not data.get("results"):
                    return None

                result = data["results"][0]
                components: dict[str, str] = {}
                for comp in result.get("address_components", []):
                    for comp_type in comp.get("types", []):
                        components[comp_type] = comp.get("long_name", "")
                        components[f"{comp_type}_short"] = comp.get("short_name", "")

                return {
                    "formatted_address": result.get("formatted_address", ""),
                    "street": f"{components.get('street_number', '')} {components.get('route', '')}".strip(),
                    "city": components.get("locality", components.get("sublocality", "")),
                    "state": components.get("administrative_area_level_1_short", ""),
                    "zip_code": components.get("postal_code", ""),
                    "county": components.get("administrative_area_level_2", ""),
                }

    except Exception as exc:
        logger.error("Reverse geocoding failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Geographic calculations
# ---------------------------------------------------------------------------


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial bearing from point 1 to point 2 (degrees)."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)

    bearing_rad = math.atan2(x, y)
    return (math.degrees(bearing_rad) + 360) % 360


def midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Calculate the geographic midpoint between two coordinates."""
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    dlon = lon2_r - lon1_r

    bx = math.cos(lat2_r) * math.cos(dlon)
    by = math.cos(lat2_r) * math.sin(dlon)

    lat_mid = math.atan2(
        math.sin(lat1_r) + math.sin(lat2_r),
        math.sqrt((math.cos(lat1_r) + bx) ** 2 + by ** 2),
    )
    lon_mid = lon1_r + math.atan2(by, math.cos(lat1_r) + bx)

    return (round(math.degrees(lat_mid), 6), round(math.degrees(lon_mid), 6))


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_miles: float
) -> tuple[float, float]:
    """
    Calculate destination point given start point, bearing, and distance.
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    brng = math.radians(bearing_deg)
    d = distance_miles / EARTH_RADIUS_MILES

    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d)
        + math.cos(lat_r) * math.sin(d) * math.cos(brng)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat_r),
        math.cos(d) - math.sin(lat_r) * math.sin(lat2),
    )

    return (round(math.degrees(lat2), 6), round(math.degrees(lon2), 6))


def sort_by_distance(
    origin_lat: float,
    origin_lon: float,
    locations: list[dict[str, Any]],
    lat_key: str = "latitude",
    lon_key: str = "longitude",
) -> list[dict[str, Any]]:
    """Sort a list of locations by distance from an origin point."""
    for loc in locations:
        loc["_distance_miles"] = haversine_distance(
            origin_lat, origin_lon, loc[lat_key], loc[lon_key]
        )

    sorted_locs = sorted(locations, key=lambda x: x["_distance_miles"])
    return sorted_locs


def filter_by_radius(
    origin_lat: float,
    origin_lon: float,
    locations: list[dict[str, Any]],
    radius_miles: float,
    lat_key: str = "latitude",
    lon_key: str = "longitude",
) -> list[dict[str, Any]]:
    """Filter locations to those within a radius of an origin point."""
    # Fast pre-filter with bounding box
    bbox = bounding_box(origin_lat, origin_lon, radius_miles)
    pre_filtered = [
        loc
        for loc in locations
        if bbox["min_lat"] <= loc[lat_key] <= bbox["max_lat"]
        and bbox["min_lon"] <= loc[lon_key] <= bbox["max_lon"]
    ]

    # Precise filter with haversine
    result = [
        loc
        for loc in pre_filtered
        if haversine_distance(origin_lat, origin_lon, loc[lat_key], loc[lon_key])
        <= radius_miles
    ]

    return result
