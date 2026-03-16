"""Rentcast API integration for rent estimates and comparables."""

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.cache import cache_get, cache_set, TTL_RENT

logger = logging.getLogger(__name__)

RENTCAST_BASE = "https://api.rentcast.io/v1"


async def get_rent_estimate(
    address: str,
    beds: Optional[int] = None,
    baths: Optional[float] = None,
    sqft: Optional[int] = None,
    property_type: str = "Single Family",
) -> Optional[dict[str, Any]]:
    """
    Fetch rent estimate from Rentcast API.

    Returns dict with keys: rent, rentRangeLow, rentRangeHigh, comparables.
    Returns None if API key is missing or call fails.
    """
    if not settings.RENTCAST_API_KEY:
        logger.warning("RENTCAST_API_KEY not configured, skipping rent estimate")
        return None

    # Check cache
    cache_key = f"rent:{address}:{beds}:{baths}:{sqft}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Rent estimate cache hit for %s", address)
        return cached

    params: dict[str, Any] = {"address": address}
    if beds:
        params["bedrooms"] = beds
    if baths:
        params["bathrooms"] = baths
    if sqft:
        params["squareFootage"] = sqft
    params["propertyType"] = property_type

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{RENTCAST_BASE}/avm/rent/long-term",
                params=params,
                headers={"X-Api-Key": settings.RENTCAST_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

            await cache_set(cache_key, data, TTL_RENT)
            logger.info("Rent estimate fetched for %s: $%s", address, data.get("rent"))
            return data

    except httpx.HTTPStatusError as e:
        logger.error("Rentcast API error %d: %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.error("Rentcast API call failed: %s", e)

    return None


async def get_rent_comps(
    address: str,
    beds: Optional[int] = None,
    baths: Optional[float] = None,
    radius: float = 2.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Fetch rental comparables near the given address."""
    if not settings.RENTCAST_API_KEY:
        return []

    cache_key = f"rent_comps:{address}:{beds}:{baths}:{radius}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    params: dict[str, Any] = {
        "address": address,
        "radius": radius,
        "limit": limit,
    }
    if beds:
        params["bedrooms"] = beds
    if baths:
        params["bathrooms"] = baths

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{RENTCAST_BASE}/listings/rental/long-term",
                params=params,
                headers={"X-Api-Key": settings.RENTCAST_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            comps = data if isinstance(data, list) else data.get("listings", [])

            await cache_set(cache_key, comps, TTL_RENT)
            return comps

    except Exception as e:
        logger.error("Rentcast comps failed: %s", e)
        return []
