"""
RealDeal AI - Scraping Celery Tasks

Orchestrates the scraping pipeline: market-level scrapes, individual property
deep scrapes, rent estimate updates, and the main daily pipeline.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from app.tasks.celery_app import app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BRIGHTDATA_USER = os.getenv("BRIGHTDATA_USERNAME", "")
BRIGHTDATA_PASS = os.getenv("BRIGHTDATA_PASSWORD", "")
RENTOMETER_API_KEY = os.getenv("RENTOMETER_API_KEY", "")

# Default tracked markets (city, state)
DEFAULT_MARKETS = [
    ("Dallas", "TX"),
    ("Houston", "TX"),
    ("San Antonio", "TX"),
    ("Austin", "TX"),
    ("Jacksonville", "FL"),
    ("Tampa", "FL"),
    ("Orlando", "FL"),
    ("Atlanta", "GA"),
    ("Charlotte", "NC"),
    ("Raleigh", "NC"),
    ("Nashville", "TN"),
    ("Memphis", "TN"),
    ("Indianapolis", "IN"),
    ("Columbus", "OH"),
    ("Cleveland", "OH"),
    ("Kansas City", "MO"),
    ("Birmingham", "AL"),
    ("Oklahoma City", "OK"),
    ("Phoenix", "AZ"),
    ("Las Vegas", "NV"),
]


def _run_async(coro):
    """Run an async coroutine in a new event loop (for Celery workers)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_scraper_kwargs() -> dict:
    """Common kwargs for scraper instantiation."""
    kwargs: dict[str, Any] = {}
    if BRIGHTDATA_USER and BRIGHTDATA_PASS:
        kwargs["brightdata_username"] = BRIGHTDATA_USER
        kwargs["brightdata_password"] = BRIGHTDATA_PASS
    return kwargs


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.task(
    bind=True,
    name="app.tasks.scraping_tasks.scrape_market",
    max_retries=3,
    default_retry_delay=120,
    rate_limit="2/m",
    soft_time_limit=600,
    time_limit=900,
)
def scrape_market(self, state: str, city: str) -> dict[str, Any]:
    """
    Orchestrate scraping across all sources for a single market.

    Scrapes Zillow, Redfin, and Realtor.com in sequence, deduplicates
    results, and stores them in the database.
    """
    logger.info("Starting market scrape for %s, %s", city, state)
    scraper_kwargs = _get_scraper_kwargs()

    async def _scrape():
        from app.scrapers import ZillowScraper, RedfinScraper, RealtorScraper

        all_properties = []
        errors = []

        # Zillow
        try:
            async with ZillowScraper(**scraper_kwargs) as scraper:
                props = await scraper.scrape_all_pages(city, state, max_pages=10)
                all_properties.extend(props)
                logger.info("Zillow: %d properties for %s, %s", len(props), city, state)
        except Exception as exc:
            errors.append(f"Zillow: {exc}")
            logger.error("Zillow scrape failed for %s, %s: %s", city, state, exc)

        # Redfin (CSV preferred)
        try:
            async with RedfinScraper(**scraper_kwargs) as scraper:
                props = await scraper.scrape_csv_download(city, state)
                if not props:
                    result = await scraper.scrape_search(city, state)
                    props = result.get("properties", [])
                all_properties.extend(props)
                logger.info("Redfin: %d properties for %s, %s", len(props), city, state)
        except Exception as exc:
            errors.append(f"Redfin: {exc}")
            logger.error("Redfin scrape failed for %s, %s: %s", city, state, exc)

        # Realtor.com
        try:
            async with RealtorScraper(**scraper_kwargs) as scraper:
                props = await scraper.scrape_all_pages(city, state, max_pages=10)
                all_properties.extend(props)
                logger.info("Realtor: %d properties for %s, %s", len(props), city, state)
        except Exception as exc:
            errors.append(f"Realtor: {exc}")
            logger.error("Realtor scrape failed for %s, %s: %s", city, state, exc)

        return all_properties, errors

    try:
        all_properties, errors = _run_async(_scrape())

        # Deduplicate by address + zip
        seen: set[str] = set()
        unique = []
        for prop in all_properties:
            key = f"{prop.address.lower().strip()}-{prop.zip_code}"
            if key not in seen and prop.price > 0:
                seen.add(key)
                unique.append(prop)

        # Store in database
        stored_count = _store_properties(unique, city, state)

        # Queue analysis for new properties
        from app.tasks.analysis_tasks import batch_analyze_properties

        if unique:
            property_ids = [_get_property_id(p) for p in unique]
            batch_analyze_properties.delay(property_ids)

        result = {
            "city": city,
            "state": state,
            "total_scraped": len(all_properties),
            "unique_properties": len(unique),
            "stored": stored_count,
            "errors": errors,
            "scraped_at": datetime.utcnow().isoformat(),
        }
        logger.info(
            "Market scrape complete for %s, %s: %d unique properties",
            city, state, len(unique),
        )
        return result

    except Exception as exc:
        logger.error("Market scrape failed for %s, %s: %s", city, state, exc)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    name="app.tasks.scraping_tasks.scrape_property_details",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="5/m",
    soft_time_limit=120,
)
def scrape_property_details(self, property_id: str) -> dict[str, Any]:
    """
    Deep scrape a single property: fetch detail pages from all sources,
    rent estimates, and public records.
    """
    logger.info("Deep scraping property %s", property_id)
    scraper_kwargs = _get_scraper_kwargs()

    # Load property from database
    property_data = _load_property(property_id)
    if not property_data:
        logger.error("Property %s not found in database", property_id)
        return {"error": "Property not found", "property_id": property_id}

    async def _deep_scrape():
        from app.scrapers import RentometerScraper, PublicRecordsScraper

        results: dict[str, Any] = {"property_id": property_id}

        # Rent estimate
        try:
            async with RentometerScraper(api_key=RENTOMETER_API_KEY, **scraper_kwargs) as scraper:
                rent_data = await scraper.get_rent_for_property(property_data)
                results["rent_estimate"] = rent_data
                if rent_data.get("median_rent", 0) > 0:
                    property_data.estimated_rent = rent_data["median_rent"]
        except Exception as exc:
            logger.warning("Rent estimate failed for %s: %s", property_id, exc)
            results["rent_estimate_error"] = str(exc)

        # Public records / tax data
        try:
            async with PublicRecordsScraper(**scraper_kwargs) as scraper:
                tax_record = await scraper.get_tax_for_property(property_data)
                if tax_record:
                    results["tax_record"] = tax_record.__dict__
                    if tax_record.tax_amount > 0:
                        property_data.tax_annual = tax_record.tax_amount
                    if tax_record.year_built > 0 and property_data.year_built == 0:
                        property_data.year_built = tax_record.year_built

                # Ownership history
                history = await scraper.get_ownership_history(
                    property_data.address,
                    property_data.city,
                    property_data.state,
                )
                results["ownership_history"] = history
        except Exception as exc:
            logger.warning("Public records failed for %s: %s", property_id, exc)
            results["public_records_error"] = str(exc)

        # Scrape detail page from original source
        if property_data.url:
            try:
                source = property_data.source
                if source == "zillow":
                    from app.scrapers import ZillowScraper
                    async with ZillowScraper(**scraper_kwargs) as scraper:
                        detail = await scraper.scrape(property_data.url)
                        if detail.get("properties"):
                            detailed = detail["properties"][0]
                            _merge_property_data(property_data, detailed)
                elif source == "redfin":
                    from app.scrapers import RedfinScraper
                    async with RedfinScraper(**scraper_kwargs) as scraper:
                        detail = await scraper.scrape(property_data.url)
                        if detail.get("properties"):
                            detailed = detail["properties"][0]
                            _merge_property_data(property_data, detailed)
                elif source == "realtor":
                    from app.scrapers import RealtorScraper
                    async with RealtorScraper(**scraper_kwargs) as scraper:
                        detail = await scraper.scrape(property_data.url)
                        if detail.get("properties"):
                            detailed = detail["properties"][0]
                            _merge_property_data(property_data, detailed)
            except Exception as exc:
                logger.warning("Detail scrape failed for %s: %s", property_id, exc)
                results["detail_scrape_error"] = str(exc)

        return results

    try:
        results = _run_async(_deep_scrape())

        # Update property in database with enriched data
        _update_property(property_id, property_data)

        # Trigger re-analysis
        from app.tasks.analysis_tasks import analyze_property
        analyze_property.delay(property_id)

        results["scraped_at"] = datetime.utcnow().isoformat()
        return results

    except Exception as exc:
        logger.error("Deep scrape failed for %s: %s", property_id, exc)
        raise self.retry(exc=exc)


@app.task(
    name="app.tasks.scraping_tasks.update_rent_estimates",
    soft_time_limit=1800,
    time_limit=3600,
)
def update_rent_estimates() -> dict[str, Any]:
    """Batch update rent estimates for properties missing or with stale data."""
    logger.info("Starting batch rent estimate update")
    scraper_kwargs = _get_scraper_kwargs()

    # Load properties needing rent updates
    properties = _load_properties_needing_rent_update()
    logger.info("Found %d properties needing rent updates", len(properties))

    updated = 0
    errors = 0

    async def _update_batch(batch):
        nonlocal updated, errors
        from app.scrapers import RentometerScraper

        async with RentometerScraper(api_key=RENTOMETER_API_KEY, **scraper_kwargs) as scraper:
            for prop_id, prop in batch:
                try:
                    rent_data = await scraper.get_rent_for_property(prop)
                    median = rent_data.get("median_rent", 0)
                    if median > 0:
                        prop.estimated_rent = median
                        _update_property(prop_id, prop)
                        updated += 1
                except Exception as exc:
                    logger.debug("Rent update failed for %s: %s", prop_id, exc)
                    errors += 1

    # Process in batches of 50
    batch_size = 50
    for i in range(0, len(properties), batch_size):
        batch = properties[i : i + batch_size]
        _run_async(_update_batch(batch))

    result = {
        "total_processed": len(properties),
        "updated": updated,
        "errors": errors,
        "completed_at": datetime.utcnow().isoformat(),
    }
    logger.info("Rent estimate update complete: %s", result)
    return result


@app.task(
    name="app.tasks.scraping_tasks.refresh_market_data",
    soft_time_limit=900,
    time_limit=1800,
)
def refresh_market_data() -> dict[str, Any]:
    """Update market-level statistics from aggregated property data."""
    logger.info("Refreshing market data")

    markets = _load_tracked_markets()
    updated_markets = 0

    for city, state in markets:
        try:
            # Aggregate from stored properties
            properties = _load_market_properties(city, state)
            if not properties:
                continue

            prices = [p.price for p in properties if p.price > 0]
            rents = [p.estimated_rent for p in properties if p.estimated_rent > 0]
            sqfts = [p.sqft for p in properties if p.sqft > 0]
            doms = [p.days_on_market for p in properties if p.days_on_market > 0]

            market_stats = {
                "city": city,
                "state": state,
                "median_home_price": _median(prices) if prices else 0,
                "median_rent": _median(rents) if rents else 0,
                "price_per_sqft": (
                    sum(prices) / sum(sqfts) if prices and sqfts else 0
                ),
                "rent_per_sqft": (
                    sum(r / s for r, s in zip(rents, sqfts) if s > 0) / len(rents)
                    if rents and sqfts
                    else 0
                ),
                "avg_days_on_market": (
                    sum(doms) / len(doms) if doms else 0
                ),
                "active_listings": len(properties),
                "updated_at": datetime.utcnow().isoformat(),
            }

            _store_market_data(market_stats)
            updated_markets += 1

        except Exception as exc:
            logger.error("Market refresh failed for %s, %s: %s", city, state, exc)

    result = {
        "markets_processed": len(markets),
        "markets_updated": updated_markets,
        "completed_at": datetime.utcnow().isoformat(),
    }
    logger.info("Market data refresh complete: %s", result)
    return result


@app.task(
    name="app.tasks.scraping_tasks.daily_scrape_pipeline",
    soft_time_limit=3600,
    time_limit=7200,
)
def daily_scrape_pipeline() -> dict[str, Any]:
    """
    Main daily pipeline: scrape all tracked markets, then update market stats.

    Runs as a chord: scrape all markets in parallel, then refresh market data.
    """
    logger.info("Starting daily scrape pipeline")

    markets = _load_tracked_markets()
    if not markets:
        markets = DEFAULT_MARKETS

    # Launch scrape tasks for each market
    from celery import chord

    scrape_tasks = [
        scrape_market.s(state, city)
        for city, state in markets
    ]

    # After all scrapes complete, refresh market data and check alerts
    callback = refresh_market_data.si()
    pipeline = chord(scrape_tasks)(callback)

    logger.info("Daily pipeline launched for %d markets", len(markets))
    return {
        "markets_queued": len(markets),
        "started_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Database interface stubs
# ---------------------------------------------------------------------------
# These functions abstract the database layer. In production, they would use
# SQLAlchemy / the ORM models. Here they define the interface.


def _store_properties(properties, city: str, state: str) -> int:
    """Store properties in the database. Returns count of new/updated records."""
    # In production: upsert into properties table
    logger.info("Storing %d properties for %s, %s", len(properties), city, state)
    return len(properties)


def _load_property(property_id: str):
    """Load a single property from the database."""
    from app.ai.deal_analyzer import PropertyData
    # In production: SELECT * FROM properties WHERE id = property_id
    logger.debug("Loading property %s", property_id)
    return None  # Placeholder


def _update_property(property_id: str, property_data) -> None:
    """Update a property record in the database."""
    logger.debug("Updating property %s", property_id)


def _get_property_id(prop) -> str:
    """Generate or retrieve the database ID for a property."""
    import hashlib
    key = f"{prop.address}-{prop.zip_code}".lower()
    return hashlib.md5(key.encode()).hexdigest()


def _load_properties_needing_rent_update() -> list:
    """Load properties with missing or stale rent estimates."""
    logger.debug("Loading properties needing rent updates")
    return []


def _load_tracked_markets() -> list[tuple[str, str]]:
    """Load user-tracked markets from database."""
    return DEFAULT_MARKETS


def _load_market_properties(city: str, state: str) -> list:
    """Load all active properties for a market."""
    return []


def _store_market_data(stats: dict) -> None:
    """Store aggregated market statistics."""
    logger.debug("Storing market data for %s, %s", stats.get("city"), stats.get("state"))


def _merge_property_data(target, source) -> None:
    """Merge non-empty fields from source into target."""
    for field_name in (
        "sqft", "lot_size_sqft", "year_built", "bedrooms", "bathrooms",
        "stories", "property_type", "latitude", "longitude", "tax_annual",
        "hoa_monthly", "description", "days_on_market",
    ):
        source_val = getattr(source, field_name, None)
        target_val = getattr(target, field_name, None)
        if source_val and (not target_val or target_val == 0):
            setattr(target, field_name, source_val)


def _median(values: list[float]) -> float:
    """Calculate median of a list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    return sorted_vals[n // 2]
