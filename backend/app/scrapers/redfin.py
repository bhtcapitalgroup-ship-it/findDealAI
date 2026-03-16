"""
RealDeal AI - Redfin Scraper

Extracts property listings from Redfin search results, detail pages,
and the CSV download endpoint.
"""

import csv
import io
import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup

from app.ai.deal_analyzer import PropertyData
from app.scrapers.base import BaseScraper, ScrapingError, rate_limit

logger = logging.getLogger(__name__)


class RedfinScraper(BaseScraper):
    """Scrape Redfin search results, detail pages, and CSV downloads."""

    SOURCE_NAME = "redfin"
    BASE_URL = "https://www.redfin.com"
    STINGRAY_URL = "https://www.redfin.com/stingray"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @rate_limit(calls_per_second=0.5)
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a Redfin URL (search or detail)."""
        html = await self._fetch(url)

        if "/home/" in url or re.search(r"/\d+$", url):
            prop = self._parse_detail_page(html, url)
            return {
                "properties": [prop] if prop else [],
                "total_results": 1 if prop else 0,
                "current_page": 1,
                "total_pages": 1,
            }
        else:
            return self._parse_search_page(html)

    async def scrape_search(
        self,
        city: str,
        state: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        beds_min: Optional[int] = None,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search Redfin using their internal gis-csv and stingray endpoints."""
        # First resolve the region ID via auto-complete
        region_info = await self._resolve_region(city, state)
        if not region_info:
            logger.warning("Could not resolve Redfin region for %s, %s", city, state)
            return {"properties": [], "total_results": 0, "current_page": 1, "total_pages": 1}

        region_id = region_info.get("id", "")
        region_type = region_info.get("type", 6)  # 6 = city

        # Build the gis endpoint URL
        params: dict[str, Any] = {
            "al": 1,
            "include_nearby_homes": True,
            "market": state.lower(),
            "num_homes": 350,
            "ord": "redfin-recommended-asc",
            "page_number": page,
            "region_id": region_id,
            "region_type": region_type,
            "sf": "1,2,3,5,6,7",  # property types
            "status": 9,  # active
            "uipt": "1,2,3,4,5,6",  # all property types
            "v": 8,
        }
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price
        if beds_min:
            params["min_beds"] = beds_min

        url = f"{self.STINGRAY_URL}/api/gis?{urlencode(params)}"
        try:
            raw = await self._fetch(url)
            # Redfin wraps JSON in "{}&&" prefix
            cleaned = raw.strip()
            if cleaned.startswith("{}&&"):
                cleaned = cleaned[4:]
            data = json.loads(cleaned)
            return self._parse_gis_response(data)
        except (ScrapingError, json.JSONDecodeError) as exc:
            logger.warning("Redfin API scrape failed, falling back to HTML: %s", exc)
            slug = f"/city/{region_id}/{state}/{city.replace(' ', '-')}"
            fallback_url = f"{self.BASE_URL}{slug}"
            html = await self._fetch(fallback_url)
            return self._parse_search_page(html)

    async def scrape_csv_download(
        self,
        city: str,
        state: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> list[PropertyData]:
        """
        Use Redfin's CSV download endpoint for bulk data extraction.
        This returns up to 350 properties per request.
        """
        region_info = await self._resolve_region(city, state)
        if not region_info:
            return []

        region_id = region_info.get("id", "")
        region_type = region_info.get("type", 6)

        params: dict[str, Any] = {
            "al": 1,
            "market": state.lower(),
            "num_homes": 350,
            "ord": "redfin-recommended-asc",
            "page_number": 1,
            "region_id": region_id,
            "region_type": region_type,
            "sf": "1,2,3,5,6,7",
            "status": 9,
            "uipt": "1,2,3,4,5,6",
            "v": 8,
        }
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price

        url = f"{self.STINGRAY_URL}/api/gis-csv?{urlencode(params)}"

        try:
            csv_text = await self._fetch(url)
            return self._parse_csv(csv_text)
        except ScrapingError as exc:
            logger.error("CSV download failed for %s, %s: %s", city, state, exc)
            return []

    def parse(self, raw_html: str) -> list[PropertyData]:
        """Parse raw HTML from a Redfin search page."""
        result = self._parse_search_page(raw_html)
        return result.get("properties", [])

    # ------------------------------------------------------------------
    # Region resolution
    # ------------------------------------------------------------------

    async def _resolve_region(self, city: str, state: str) -> Optional[dict]:
        """Use Redfin's autocomplete to resolve a city to a region ID."""
        query = f"{city} {state}"
        url = f"{self.STINGRAY_URL}/do/location-autocomplete?location={quote(query)}&v=2"

        try:
            raw = await self._fetch(url)
            cleaned = raw.strip()
            if cleaned.startswith("{}&&"):
                cleaned = cleaned[4:]
            data = json.loads(cleaned)

            sections = data.get("payload", {}).get("sections", [])
            for section in sections:
                for row in section.get("rows", []):
                    if row.get("type") == "city" or row.get("subType") == "city":
                        return {
                            "id": row.get("id", ""),
                            "type": row.get("type_code", 6),
                            "name": row.get("name", ""),
                            "url": row.get("url", ""),
                        }
            # Fallback: return first result
            for section in sections:
                rows = section.get("rows", [])
                if rows:
                    return {
                        "id": rows[0].get("id", ""),
                        "type": rows[0].get("type_code", 6),
                        "name": rows[0].get("name", ""),
                        "url": rows[0].get("url", ""),
                    }
        except Exception as exc:
            logger.error("Region resolution failed for %s, %s: %s", city, state, exc)

        return None

    # ------------------------------------------------------------------
    # Parsing: GIS API
    # ------------------------------------------------------------------

    def _parse_gis_response(self, data: dict) -> dict[str, Any]:
        properties: list[PropertyData] = []
        payload = data.get("payload", {})
        homes = payload.get("homes", [])

        for home in homes:
            try:
                prop = self._map_gis_home(home)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Error parsing Redfin GIS home: %s", exc)

        total = payload.get("totalResultCount", len(properties))
        return {
            "properties": properties,
            "total_results": total,
            "current_page": 1,
            "total_pages": max(1, (total + 350 - 1) // 350),
        }

    def _map_gis_home(self, home: dict) -> Optional[PropertyData]:
        hd = home.get("homeData", home)
        price_info = hd.get("priceInfo", {})
        addr_info = hd.get("addressInfo", {})

        price = float(price_info.get("amount", hd.get("price", {}).get("value", 0)))
        if price <= 0:
            price = float(hd.get("listingPrice", 0))

        return PropertyData(
            address=addr_info.get("formattedStreetLine", hd.get("streetLine", {}).get("value", "")),
            city=addr_info.get("city", ""),
            state=addr_info.get("state", ""),
            zip_code=str(addr_info.get("zip", "")),
            price=price,
            bedrooms=int(hd.get("beds", 0)),
            bathrooms=float(hd.get("baths", 0)),
            sqft=int(hd.get("sqFt", {}).get("value", 0)) if isinstance(hd.get("sqFt"), dict) else int(hd.get("sqFt", 0)),
            lot_size_sqft=int(hd.get("lotSize", {}).get("value", 0)) if isinstance(hd.get("lotSize"), dict) else 0,
            year_built=int(hd.get("yearBuilt", {}).get("value", 0)) if isinstance(hd.get("yearBuilt"), dict) else int(hd.get("yearBuilt", 0)),
            property_type=self._map_property_type(hd.get("propertyType", 0)),
            latitude=float(addr_info.get("centroid", {}).get("centroid", {}).get("latitude", hd.get("latitude", 0))),
            longitude=float(addr_info.get("centroid", {}).get("centroid", {}).get("longitude", hd.get("longitude", 0))),
            days_on_market=int(hd.get("dom", {}).get("value", 0)) if isinstance(hd.get("dom"), dict) else int(hd.get("timeOnRedfin", {}).get("value", 0) / 86400000) if isinstance(hd.get("timeOnRedfin"), dict) else 0,
            hoa_monthly=float(hd.get("hoa", {}).get("value", 0)) if isinstance(hd.get("hoa"), dict) else 0,
            url=f"{self.BASE_URL}{hd.get('url', '')}",
            mls_id=str(hd.get("mlsId", {}).get("value", "")) if isinstance(hd.get("mlsId"), dict) else str(hd.get("listingId", "")),
            source="redfin",
        )

    # ------------------------------------------------------------------
    # Parsing: Search HTML
    # ------------------------------------------------------------------

    def _parse_search_page(self, html: str) -> dict[str, Any]:
        properties: list[PropertyData] = []
        soup = BeautifulSoup(html, "html.parser")

        # Try embedded React state
        for script in soup.find_all("script"):
            text = script.string or ""
            if "window.__reactServerState" in text or "reactServerAgent" in text:
                match = re.search(r"=\s*(\{.*\});\s*$", text, re.DOTALL)
                if match:
                    try:
                        state = json.loads(match.group(1))
                        homes = (
                            state.get("cat1", {})
                            .get("searchResults", {})
                            .get("homes", [])
                        )
                        for home in homes:
                            prop = self._map_gis_home(home)
                            if prop:
                                properties.append(prop)
                    except (json.JSONDecodeError, AttributeError):
                        pass

        # CSS-based parsing fallback
        cards = soup.select(
            'div[class*="HomeCardContainer"], '
            'div[data-rf-test-name="mapHomeCard"], '
            'div.HomeViews div[class*="homecard"]'
        )

        for card in cards:
            try:
                prop = self._parse_html_card(card)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Redfin card parse error: %s", exc)

        total_el = soup.select_one('span[class*="homes-count"], div[class*="resultsCount"]')
        total = self._clean_int(total_el.get_text()) if total_el else len(properties)

        return {
            "properties": properties,
            "total_results": total,
            "current_page": 1,
            "total_pages": max(1, (total + 350 - 1) // 350),
        }

    def _parse_html_card(self, card) -> Optional[PropertyData]:
        price_el = card.select_one(
            'span[class*="homecardV2Price"], '
            'span[data-rf-test-name="homecard-price"]'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        addr_el = card.select_one(
            'div[class*="homeAddress"], '
            'span[data-rf-test-name="homecard-streetAddress"]'
        )
        address = addr_el.get_text(strip=True) if addr_el else ""

        loc_el = card.select_one(
            'div[class*="homeAddressSecond"], '
            'span[data-rf-test-name="homecard-cityState"]'
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Parse city, state, zip from location
        city, state, zip_code = "", "", ""
        loc_parts = [p.strip() for p in location.split(",")]
        if len(loc_parts) >= 2:
            city = loc_parts[0]
            sz = loc_parts[1].strip().split()
            state = sz[0] if len(sz) >= 1 else ""
            zip_code = sz[1] if len(sz) >= 2 else ""

        # Stats
        stats = card.select(
            'div[class*="HomeStatsV2"] div[class*="stat"], '
            'span[class*="HomeCardContainer__HomeCardStat"]'
        )
        beds, baths, sqft = 0, 0.0, 0
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if "bed" in text or "bd" in text:
                beds = self._clean_int(text)
            elif "bath" in text or "ba" in text:
                baths = self._clean_float(text)
            elif "sq" in text:
                sqft = self._clean_int(text.replace(",", ""))

        link = card.select_one("a[href]")
        url = ""
        if link:
            href = link.get("href", "")
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        return PropertyData(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            price=price,
            bedrooms=beds,
            bathrooms=baths,
            sqft=sqft,
            url=url,
            source="redfin",
        )

    # ------------------------------------------------------------------
    # Parsing: Detail page
    # ------------------------------------------------------------------

    def _parse_detail_page(self, html: str, url: str = "") -> Optional[PropertyData]:
        soup = BeautifulSoup(html, "html.parser")

        # Price
        price_el = soup.select_one(
            'div[class*="statsValue"] span, '
            'span[data-rf-test-id="abp-price"], '
            'div[class*="price-section"] span'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        # Address
        street_el = soup.select_one(
            'h1[class*="street-address"], '
            'span[data-rf-test-id="abp-streetLine"]'
        )
        address = street_el.get_text(strip=True) if street_el else ""

        loc_el = soup.select_one(
            'h1[class*="cityStateZip"], '
            'span[data-rf-test-id="abp-cityStateZip"]'
        )
        location = loc_el.get_text(strip=True) if loc_el else ""
        city, state, zip_code = "", "", ""
        loc_parts = [p.strip() for p in location.split(",")]
        if len(loc_parts) >= 2:
            city = loc_parts[0]
            sz = loc_parts[-1].strip().split()
            state = sz[0] if len(sz) >= 1 else ""
            zip_code = sz[1] if len(sz) >= 2 else ""

        # Key details
        beds, baths, sqft, year_built = 0, 0.0, 0, 0
        detail_items = soup.select(
            'div[class*="keyDetail"] span, '
            'div[data-rf-test-name="abp-beds"] span, '
            'div[data-rf-test-name="abp-baths"] span, '
            'div[data-rf-test-name="abp-sqFt"] span'
        )
        for item in detail_items:
            text = item.get_text(strip=True).lower()
            parent_text = (item.parent.get_text(strip=True) if item.parent else "").lower()
            combined = f"{parent_text} {text}"
            if "bed" in combined:
                beds = self._clean_int(text)
            elif "bath" in combined:
                baths = self._clean_float(text)
            elif "sq" in combined and "lot" not in combined:
                sqft = self._clean_int(text.replace(",", ""))

        # Year built from property details section
        for row in soup.select('div[class*="amenity-group"] span'):
            text = row.get_text(strip=True)
            if "Built in" in text:
                match = re.search(r"(\d{4})", text)
                if match:
                    year_built = int(match.group(1))
                break

        # HOA
        hoa = 0.0
        hoa_el = soup.select_one('span[class*="hoa-value"], div[class*="hoa"] span')
        if hoa_el:
            hoa = self._clean_float(hoa_el.get_text())

        # Description
        desc_el = soup.select_one(
            'div[class*="remarks"] p, '
            'div[id="marketing-remarks-scroll"] span'
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        return PropertyData(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            price=price,
            bedrooms=beds,
            bathrooms=baths,
            sqft=sqft,
            year_built=year_built,
            hoa_monthly=hoa,
            description=description,
            url=url,
            source="redfin",
        )

    # ------------------------------------------------------------------
    # Parsing: CSV
    # ------------------------------------------------------------------

    def _parse_csv(self, csv_text: str) -> list[PropertyData]:
        """Parse Redfin's CSV download format."""
        properties: list[PropertyData] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        column_map = {
            "ADDRESS": "address",
            "CITY": "city",
            "STATE OR PROVINCE": "state",
            "STATE": "state",
            "ZIP OR POSTAL CODE": "zip_code",
            "ZIP": "zip_code",
            "PRICE": "price",
            "BEDS": "bedrooms",
            "BATHS": "bathrooms",
            "SQUARE FEET": "sqft",
            "LOT SIZE": "lot_size_sqft",
            "YEAR BUILT": "year_built",
            "DAYS ON MARKET": "days_on_market",
            "HOA/MONTH": "hoa_monthly",
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": "url",
            "URL": "url",
            "MLS#": "mls_id",
            "PROPERTY TYPE": "property_type",
            "LATITUDE": "latitude",
            "LONGITUDE": "longitude",
        }

        for row in reader:
            try:
                # Normalize column names
                normalized: dict[str, Any] = {}
                for csv_col, field_name in column_map.items():
                    if csv_col in row:
                        normalized[field_name] = row[csv_col]

                prop = PropertyData(
                    address=str(normalized.get("address", "")),
                    city=str(normalized.get("city", "")),
                    state=str(normalized.get("state", "")),
                    zip_code=str(normalized.get("zip_code", "")),
                    price=self._clean_price(str(normalized.get("price", "0"))),
                    bedrooms=self._clean_int(str(normalized.get("bedrooms", "0"))),
                    bathrooms=self._clean_float(str(normalized.get("bathrooms", "0"))),
                    sqft=self._clean_int(str(normalized.get("sqft", "0"))),
                    lot_size_sqft=self._clean_int(str(normalized.get("lot_size_sqft", "0"))),
                    year_built=self._clean_int(str(normalized.get("year_built", "0"))),
                    days_on_market=self._clean_int(str(normalized.get("days_on_market", "0"))),
                    hoa_monthly=self._clean_float(str(normalized.get("hoa_monthly", "0"))),
                    property_type=self._map_property_type_str(str(normalized.get("property_type", ""))),
                    latitude=self._clean_float(str(normalized.get("latitude", "0"))),
                    longitude=self._clean_float(str(normalized.get("longitude", "0"))),
                    url=str(normalized.get("url", "")),
                    mls_id=str(normalized.get("mls_id", "")),
                    source="redfin",
                )

                if prop.price > 0:
                    properties.append(prop)

            except Exception as exc:
                logger.debug("Error parsing CSV row: %s", exc)

        logger.info("Parsed %d properties from Redfin CSV", len(properties))
        return properties

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_property_type(type_code: int) -> str:
        mapping = {
            1: "single_family",
            2: "condo",
            3: "townhouse",
            4: "multi_family",
            5: "land",
            6: "single_family",  # other
            13: "single_family",  # manufactured
        }
        return mapping.get(type_code, "single_family")

    @staticmethod
    def _map_property_type_str(raw: str) -> str:
        raw_lower = raw.lower()
        if "single" in raw_lower or "house" in raw_lower:
            return "single_family"
        elif "condo" in raw_lower:
            return "condo"
        elif "town" in raw_lower:
            return "townhouse"
        elif "multi" in raw_lower or "duplex" in raw_lower or "triplex" in raw_lower:
            return "multi_family"
        elif "land" in raw_lower or "lot" in raw_lower:
            return "land"
        return "single_family"
