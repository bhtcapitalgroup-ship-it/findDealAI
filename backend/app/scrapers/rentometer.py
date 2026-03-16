"""
RealDeal AI - Rentometer Scraper

Fetches rental estimates for a given address from Rentometer and
similar rent-estimation sources.
"""

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup

from app.ai.deal_analyzer import PropertyData
from app.scrapers.base import BaseScraper, ScrapingError, rate_limit

logger = logging.getLogger(__name__)


class RentometerScraper(BaseScraper):
    """Fetch rent estimates from Rentometer."""

    SOURCE_NAME = "rentometer"
    BASE_URL = "https://www.rentometer.com"
    API_URL = "https://www.rentometer.com/api/v1"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @rate_limit(calls_per_second=0.3)
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a Rentometer results page."""
        html = await self._fetch(url)
        return self._parse_results_page(html)

    async def get_rent_estimate(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        bedrooms: int = 2,
        bathrooms: float = 1.0,
        sqft: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Get rent estimate for a specific address.

        Returns {
            "median_rent": float,
            "percentile_25": float,
            "percentile_75": float,
            "sample_size": int,
            "min_rent": float,
            "max_rent": float,
            "radius_miles": float,
            "address": str,
        }
        """
        # Try API first if key is available
        if self._api_key:
            try:
                return await self._fetch_via_api(
                    address, city, state, zip_code, bedrooms
                )
            except ScrapingError:
                logger.warning("Rentometer API failed, falling back to scraping")

        # Fallback to web scraping
        return await self._fetch_via_web(
            address, city, state, zip_code, bedrooms, bathrooms, sqft
        )

    async def get_rent_for_property(self, property: PropertyData) -> dict[str, Any]:
        """Convenience method: get rent estimate for a PropertyData object."""
        return await self.get_rent_estimate(
            address=property.address,
            city=property.city,
            state=property.state,
            zip_code=property.zip_code,
            bedrooms=property.bedrooms,
            bathrooms=property.bathrooms,
            sqft=property.sqft,
        )

    def parse(self, raw_html: str) -> list[PropertyData]:
        """Parse is not typical for Rentometer; returns empty list."""
        return []

    # ------------------------------------------------------------------
    # API-based fetch
    # ------------------------------------------------------------------

    async def _fetch_via_api(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        bedrooms: int,
    ) -> dict[str, Any]:
        """Use the Rentometer API (requires API key)."""
        full_address = f"{address}, {city}, {state} {zip_code}"
        params = {
            "api_key": self._api_key,
            "address": full_address,
            "bedrooms": bedrooms,
        }

        url = f"{self.API_URL}/summary?{urlencode(params)}"
        data = await self._fetch_json(url)

        if "error" in data:
            raise ScrapingError(f"Rentometer API error: {data['error']}")

        return {
            "median_rent": float(data.get("median", 0)),
            "percentile_25": float(data.get("percentile_25", 0)),
            "percentile_75": float(data.get("percentile_75", 0)),
            "mean_rent": float(data.get("mean", 0)),
            "sample_size": int(data.get("sample_size", 0)),
            "min_rent": float(data.get("min", 0)),
            "max_rent": float(data.get("max", 0)),
            "radius_miles": float(data.get("radius_miles", 1.0)),
            "address": full_address,
            "source": "rentometer_api",
        }

    # ------------------------------------------------------------------
    # Web-based fetch
    # ------------------------------------------------------------------

    async def _fetch_via_web(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        bedrooms: int,
        bathrooms: float = 1.0,
        sqft: Optional[int] = None,
    ) -> dict[str, Any]:
        """Scrape the Rentometer website directly."""
        full_address = f"{address}, {city}, {state} {zip_code}"

        # Step 1: Get a search results page
        search_params = {
            "address": full_address,
            "bedrooms": bedrooms,
        }
        if sqft:
            search_params["sqft"] = sqft

        search_url = f"{self.BASE_URL}/results?{urlencode(search_params)}"

        try:
            html = await self._fetch(search_url)
            result = self._parse_results_page(html)
            result["address"] = full_address
            return result

        except ScrapingError:
            # Try the analysis endpoint
            analysis_url = f"{self.BASE_URL}/analysis?{urlencode(search_params)}"
            try:
                html = await self._fetch(analysis_url)
                result = self._parse_results_page(html)
                result["address"] = full_address
                return result
            except ScrapingError as exc:
                logger.error("Rentometer scraping failed for %s: %s", full_address, exc)
                return self._empty_result(full_address)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_results_page(self, html: str) -> dict[str, Any]:
        """Parse a Rentometer results page for rent statistics."""
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "median_rent": 0.0,
            "percentile_25": 0.0,
            "percentile_75": 0.0,
            "mean_rent": 0.0,
            "sample_size": 0,
            "min_rent": 0.0,
            "max_rent": 0.0,
            "radius_miles": 1.0,
            "source": "rentometer_web",
        }

        # Try extracting from embedded JavaScript data
        for script in soup.find_all("script"):
            text = script.string or ""
            if "analysisData" in text or "rentData" in text or "median" in text:
                # Extract JSON-like data from script
                json_match = re.search(r"(?:analysisData|rentData|results)\s*[:=]\s*(\{[^;]+\})", text)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        result["median_rent"] = float(data.get("median", data.get("median_rent", 0)))
                        result["percentile_25"] = float(data.get("percentile_25", data.get("q1", 0)))
                        result["percentile_75"] = float(data.get("percentile_75", data.get("q3", 0)))
                        result["mean_rent"] = float(data.get("mean", data.get("average", 0)))
                        result["sample_size"] = int(data.get("sample_size", data.get("count", 0)))
                        result["min_rent"] = float(data.get("min", 0))
                        result["max_rent"] = float(data.get("max", 0))
                        if result["median_rent"] > 0:
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass

        # Parse from HTML elements
        # Median rent
        median_el = soup.select_one(
            'div[class*="median"] span[class*="amount"], '
            'span[class*="median-rent"], '
            'div[class*="result-median"] .value, '
            'h2[class*="median"]'
        )
        if median_el:
            result["median_rent"] = self._clean_price(median_el.get_text())

        # Sample size
        sample_el = soup.select_one(
            'span[class*="sample-size"], '
            'div[class*="sample"] span, '
            'span[class*="listing-count"]'
        )
        if sample_el:
            result["sample_size"] = self._clean_int(sample_el.get_text())

        # Percentiles / range
        range_els = soup.select(
            'div[class*="range"] span[class*="value"], '
            'div[class*="quartile"] span'
        )
        if len(range_els) >= 2:
            values = sorted([self._clean_price(el.get_text()) for el in range_els])
            values = [v for v in values if v > 0]
            if len(values) >= 2:
                result["percentile_25"] = values[0]
                result["percentile_75"] = values[-1]

        # Min/Max
        min_el = soup.select_one('span[class*="min-rent"], div[class*="min"] .value')
        max_el = soup.select_one('span[class*="max-rent"], div[class*="max"] .value')
        if min_el:
            result["min_rent"] = self._clean_price(min_el.get_text())
        if max_el:
            result["max_rent"] = self._clean_price(max_el.get_text())

        # If we still don't have percentiles, estimate from median
        if result["median_rent"] > 0:
            if result["percentile_25"] == 0:
                result["percentile_25"] = result["median_rent"] * 0.85
            if result["percentile_75"] == 0:
                result["percentile_75"] = result["median_rent"] * 1.15

        return result

    @staticmethod
    def _empty_result(address: str) -> dict[str, Any]:
        return {
            "median_rent": 0.0,
            "percentile_25": 0.0,
            "percentile_75": 0.0,
            "mean_rent": 0.0,
            "sample_size": 0,
            "min_rent": 0.0,
            "max_rent": 0.0,
            "radius_miles": 0.0,
            "address": address,
            "source": "rentometer_web",
            "error": "No data available",
        }
