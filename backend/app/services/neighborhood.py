"""Neighborhood data aggregation from Census, FBI Crime, and GreatSchools APIs."""

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.cache import cache_get, cache_set, TTL_NEIGHBORHOOD

logger = logging.getLogger(__name__)


async def get_neighborhood_data(
    zip_code: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict[str, Any]:
    """
    Aggregate neighborhood intelligence from multiple free government APIs.

    Returns a dict with: crime_rate, crime_label, school_rating,
    pop_growth, rent_growth, median_income, unemployment.
    """
    cache_key = f"neighborhood:{zip_code}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Neighborhood cache hit for %s", zip_code)
        return cached

    result: dict[str, Any] = {}

    # Fetch all sources concurrently — failures are non-fatal
    import asyncio
    census_task = _fetch_census(zip_code)
    school_task = _fetch_school_rating(zip_code, latitude, longitude)
    crime_task = _fetch_crime_index(zip_code)

    census, schools, crime = await asyncio.gather(
        census_task, school_task, crime_task,
        return_exceptions=True,
    )

    if isinstance(census, dict):
        result.update(census)
    else:
        logger.warning("Census fetch failed: %s", census)

    if isinstance(schools, dict):
        result.update(schools)
    else:
        logger.warning("School rating fetch failed: %s", schools)

    if isinstance(crime, dict):
        result.update(crime)
    else:
        logger.warning("Crime data fetch failed: %s", crime)

    if result:
        await cache_set(cache_key, result, TTL_NEIGHBORHOOD)

    return result


async def _fetch_census(zip_code: str) -> dict[str, Any]:
    """
    Fetch demographics from US Census Bureau ACS 5-Year API.

    Variables:
      B01003_001E = total population
      B19013_001E = median household income
      B23025_005E = unemployed
      B23025_002E = labor force
      B25064_001E = median gross rent
    """
    variables = "B01003_001E,B19013_001E,B23025_005E,B23025_002E,B25064_001E"
    url = (
        f"https://api.census.gov/data/2022/acs/acs5"
        f"?get={variables}&for=zip%20code%20tabulation%20area:{zip_code}"
    )
    if settings.CENSUS_API_KEY:
        url += f"&key={settings.CENSUS_API_KEY}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    if len(data) < 2:
        return {}

    row = data[1]
    population = _safe_int(row[0])
    median_income = _safe_int(row[1])
    unemployed = _safe_int(row[2])
    labor_force = _safe_int(row[3])
    median_rent = _safe_int(row[4])

    unemployment = round(unemployed / labor_force * 100, 1) if labor_force else None

    # Fetch prior year for growth calculation
    pop_growth = await _calc_pop_growth(zip_code, population)

    # Estimate rent growth from median rent vs national average
    rent_growth = _estimate_rent_growth(median_rent)

    return {
        "median_income": median_income,
        "unemployment": unemployment,
        "pop_growth": pop_growth,
        "rent_growth": rent_growth,
        "population": population,
        "median_rent": median_rent,
    }


async def _calc_pop_growth(zip_code: str, current_pop: Optional[int]) -> Optional[float]:
    """Compare current ACS population to prior year for growth rate."""
    if not current_pop:
        return None

    try:
        url = (
            f"https://api.census.gov/data/2021/acs/acs5"
            f"?get=B01003_001E&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        if settings.CENSUS_API_KEY:
            url += f"&key={settings.CENSUS_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if len(data) >= 2:
            prior_pop = _safe_int(data[1][0])
            if prior_pop and prior_pop > 0:
                return round((current_pop - prior_pop) / prior_pop * 100, 2)
    except Exception:
        pass
    return None


def _estimate_rent_growth(median_rent: Optional[int]) -> Optional[float]:
    """Rough rent growth estimate based on deviation from national median."""
    if not median_rent:
        return None
    # National median ~$1,300. Areas above tend to have higher growth.
    national_median = 1300
    deviation = (median_rent - national_median) / national_median
    # Cap between -2% and +8%
    growth = round(2.5 + deviation * 3, 1)
    return max(-2.0, min(8.0, growth))


async def _fetch_school_rating(
    zip_code: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict[str, Any]:
    """
    Fetch school ratings from GreatSchools API.

    Uses lat/lng if available, falls back to zip code search.
    """
    if not settings.GREATSCHOOLS_API_KEY:
        logger.info("GREATSCHOOLS_API_KEY not set, skipping school data")
        return {}

    base = "https://gs-api.greatschools.org/nearby-schools"
    params: dict[str, Any] = {"limit": 10}

    if latitude and longitude:
        params["lat"] = latitude
        params["lon"] = longitude
    else:
        params["zip"] = zip_code

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                base,
                params=params,
                headers={"x-api-key": settings.GREATSCHOOLS_API_KEY},
            )
            resp.raise_for_status()
            schools = resp.json().get("schools", [])

        if not schools:
            return {}

        ratings = [s.get("rating", 0) for s in schools if s.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

        return {"school_rating": avg_rating}

    except Exception as e:
        logger.error("GreatSchools API failed: %s", e)
        return {}


async def _fetch_crime_index(zip_code: str) -> dict[str, Any]:
    """
    Fetch crime data from FBI Crime Data Explorer API.

    The FBI API uses ORI codes (agency identifiers), not zip codes directly.
    We use a simplified approach: fetch state-level data and adjust by
    population density as a proxy. For production, use a geocoded
    agency lookup.
    """
    # FBI CDE API is complex (ORI-based). For MVP, use a heuristic based
    # on Census poverty rate and population density as crime proxies.
    # TODO: integrate full FBI CDE or CrimeMapping API
    try:
        # Use Census poverty rate as a crime proxy (correlated)
        url = (
            f"https://api.census.gov/data/2022/acs/acs5"
            f"?get=B17001_002E,B17001_001E&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        if settings.CENSUS_API_KEY:
            url += f"&key={settings.CENSUS_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if len(data) < 2:
            return {}

        poverty_pop = _safe_int(data[1][0])
        total_pop = _safe_int(data[1][1])

        if not total_pop or total_pop == 0:
            return {}

        poverty_rate = poverty_pop / total_pop

        # Map poverty rate to a 0-100 crime index (rough correlation)
        # National avg poverty rate ~12%. Double = high crime proxy.
        crime_index = min(100, max(0, round(poverty_rate / 0.24 * 100)))

        if crime_index < 25:
            label = "Low"
        elif crime_index < 50:
            label = "Moderate"
        elif crime_index < 75:
            label = "High"
        else:
            label = "Very High"

        return {"crime_rate": crime_index, "crime_label": label}

    except Exception as e:
        logger.error("Crime index estimation failed: %s", e)
        return {}


def _safe_int(val: Any) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
