"""
RealDeal AI - Zillow Scraper

Extracts property listings from Zillow search results and detail pages.
Parses both server-rendered HTML and embedded JSON-LD / __NEXT_DATA__ payloads.
"""

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote_plus, urlencode

from bs4 import BeautifulSoup

from app.ai.deal_analyzer import PropertyData
from app.scrapers.base import BaseScraper, ScrapingError, rate_limit

logger = logging.getLogger(__name__)


class ZillowScraper(BaseScraper):
    """Scrape Zillow search results and property detail pages."""

    SOURCE_NAME = "zillow"
    BASE_URL = "https://www.zillow.com"
    SEARCH_URL = "https://www.zillow.com/search/GetSearchPageState.htm"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @rate_limit(calls_per_second=0.5)
    async def scrape(self, url: str) -> dict[str, Any]:
        """
        Scrape a Zillow URL (search page or detail page).

        Returns {
            "properties": [PropertyData, ...],
            "total_results": int,
            "current_page": int,
            "total_pages": int,
        }
        """
        html = await self._fetch(url)

        if "/homedetails/" in url:
            prop = self._parse_detail_page(html)
            return {
                "properties": [prop] if prop else [],
                "total_results": 1 if prop else 0,
                "current_page": 1,
                "total_pages": 1,
            }
        else:
            return self._parse_search_results(html)

    async def scrape_search(
        self,
        city: str,
        state: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        beds_min: Optional[int] = None,
        status: str = "forSale",
        page: int = 1,
    ) -> dict[str, Any]:
        """Scrape Zillow search using their internal API endpoint."""
        search_query_state = {
            "pagination": {"currentPage": page},
            "usersSearchTerm": f"{city}, {state}",
            "filterState": {
                "isForSaleByAgent": {"value": True},
                "isForSaleByOwner": {"value": True},
                "isNewConstruction": {"value": False},
                "isForSaleForeclosure": {"value": True},
                "isComingSoon": {"value": False},
                "isAuction": {"value": True},
                "isPreMarketForeclosure": {"value": True},
                "isPreMarketPreForeclosure": {"value": True},
            },
            "isListVisible": True,
        }

        if min_price:
            search_query_state["filterState"]["price"] = {"min": min_price}
        if max_price:
            search_query_state["filterState"]["price"] = search_query_state["filterState"].get("price", {})
            search_query_state["filterState"]["price"]["max"] = max_price
        if beds_min:
            search_query_state["filterState"]["beds"] = {"min": beds_min}

        params = {
            "searchQueryState": json.dumps(search_query_state),
            "wants": json.dumps({"cat1": ["listResults", "mapResults"], "cat2": ["total"]}),
            "requestId": page,
        }

        url = f"{self.SEARCH_URL}?{urlencode(params)}"

        try:
            data = await self._fetch_json(url)
            return self._parse_api_response(data)
        except ScrapingError:
            # Fallback to HTML scraping
            slug = f"{city.lower().replace(' ', '-')}-{state.lower()}"
            fallback_url = f"{self.BASE_URL}/{slug}/"
            if page > 1:
                fallback_url += f"{page}_p/"
            html = await self._fetch(fallback_url)
            return self._parse_search_results(html)

    async def scrape_all_pages(
        self,
        city: str,
        state: str,
        max_pages: int = 20,
        **kwargs,
    ) -> list[PropertyData]:
        """Scrape all pages for a search, respecting rate limits."""
        all_properties: list[PropertyData] = []
        seen_fingerprints: set[str] = set()

        for page in range(1, max_pages + 1):
            try:
                result = await self.scrape_search(city, state, page=page, **kwargs)
                properties = result.get("properties", [])

                if not properties:
                    logger.info("No more results at page %d", page)
                    break

                for prop in properties:
                    fp = self._fingerprint(
                        {"address": prop.address, "zip_code": prop.zip_code, "price": prop.price}
                    )
                    if fp not in seen_fingerprints:
                        seen_fingerprints.add(fp)
                        all_properties.append(prop)

                total_pages = result.get("total_pages", 1)
                if page >= total_pages:
                    break

                logger.info(
                    "Zillow page %d/%d: %d properties (total so far: %d)",
                    page,
                    total_pages,
                    len(properties),
                    len(all_properties),
                )

            except ScrapingError as exc:
                logger.error("Failed on page %d: %s", page, exc)
                break

        return all_properties

    def parse(self, raw_html: str) -> list[PropertyData]:
        """Parse raw HTML from a Zillow search results page."""
        result = self._parse_search_results(raw_html)
        return result.get("properties", [])

    # ------------------------------------------------------------------
    # Parsing: API JSON response
    # ------------------------------------------------------------------

    def _parse_api_response(self, data: dict) -> dict[str, Any]:
        properties: list[PropertyData] = []
        cat1 = data.get("cat1", {})
        search_results = cat1.get("searchResults", {}).get("listResults", [])
        total_results = cat1.get("searchResults", {}).get("totalResultCount", 0)
        total_pages = max(1, (total_results + 40 - 1) // 40)  # 40 results per page

        for item in search_results:
            try:
                prop = self._map_api_listing(item)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Error parsing API listing: %s", exc)

        return {
            "properties": properties,
            "total_results": total_results,
            "current_page": data.get("categoryTotals", {}).get("cat1", {}).get("totalPages", 1),
            "total_pages": total_pages,
        }

    def _map_api_listing(self, item: dict) -> Optional[PropertyData]:
        hd = item.get("hdpData", {}).get("homeInfo", {})
        if not hd:
            return None

        return PropertyData(
            address=hd.get("streetAddress", item.get("addressStreet", "")),
            city=hd.get("city", item.get("addressCity", "")),
            state=hd.get("state", item.get("addressState", "")),
            zip_code=str(hd.get("zipcode", item.get("addressZipcode", ""))),
            price=float(hd.get("price", item.get("unformattedPrice", 0))),
            bedrooms=int(hd.get("bedrooms", item.get("beds", 0))),
            bathrooms=float(hd.get("bathrooms", item.get("baths", 0))),
            sqft=int(hd.get("livingArea", item.get("area", 0))),
            lot_size_sqft=int(hd.get("lotSize", 0)),
            year_built=int(hd.get("yearBuilt", 0)),
            property_type=self._map_property_type(hd.get("homeType", "")),
            latitude=float(hd.get("latitude", item.get("latLong", {}).get("latitude", 0))),
            longitude=float(hd.get("longitude", item.get("latLong", {}).get("longitude", 0))),
            tax_annual=float(hd.get("taxAssessedValue", 0)) * 0.012,  # ~1.2 % tax rate estimate
            days_on_market=int(hd.get("daysOnZillow", 0)),
            url=f"{self.BASE_URL}{item.get('detailUrl', '')}",
            mls_id=str(hd.get("zpid", "")),
            source="zillow",
        )

    # ------------------------------------------------------------------
    # Parsing: Search results HTML
    # ------------------------------------------------------------------

    def _parse_search_results(self, html: str) -> dict[str, Any]:
        properties: list[PropertyData] = []

        # Try extracting __NEXT_DATA__ JSON blob
        next_data = self._extract_next_data(html)
        if next_data:
            try:
                search_results = (
                    next_data.get("props", {})
                    .get("pageProps", {})
                    .get("searchPageState", {})
                    .get("cat1", {})
                    .get("searchResults", {})
                    .get("listResults", [])
                )
                for item in search_results:
                    prop = self._map_api_listing(item)
                    if prop and prop.price > 0:
                        properties.append(prop)

                if properties:
                    total = (
                        next_data.get("props", {})
                        .get("pageProps", {})
                        .get("searchPageState", {})
                        .get("cat1", {})
                        .get("searchResults", {})
                        .get("totalResultCount", len(properties))
                    )
                    return {
                        "properties": properties,
                        "total_results": total,
                        "current_page": 1,
                        "total_pages": max(1, (total + 40 - 1) // 40),
                    }
            except Exception as exc:
                logger.debug("__NEXT_DATA__ parsing failed: %s", exc)

        # Fallback: parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Parse JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, list):
                    for item in ld:
                        prop = self._parse_json_ld(item)
                        if prop:
                            properties.append(prop)
                elif isinstance(ld, dict):
                    prop = self._parse_json_ld(ld)
                    if prop:
                        properties.append(prop)
            except (json.JSONDecodeError, TypeError):
                continue

        # Parse listing cards via CSS selectors
        listing_cards = soup.select(
            'article[data-test="property-card"], '
            'li[class*="ListItem"] article, '
            'div[id="grid-search-results"] ul > li article'
        )

        for card in listing_cards:
            try:
                prop = self._parse_listing_card(card)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Error parsing listing card: %s", exc)

        # Dedup
        seen: set[str] = set()
        unique: list[PropertyData] = []
        for p in properties:
            fp = self._fingerprint({"address": p.address, "zip_code": p.zip_code, "price": p.price})
            if fp not in seen:
                seen.add(fp)
                unique.append(p)

        total_text = soup.select_one('span[class*="result-count"], div[class*="total-text"]')
        total = self._clean_int(total_text.get_text()) if total_text else len(unique)

        return {
            "properties": unique,
            "total_results": total,
            "current_page": 1,
            "total_pages": max(1, (total + 40 - 1) // 40),
        }

    def _parse_listing_card(self, card) -> Optional[PropertyData]:
        """Parse a single listing card from search results HTML."""
        # Price
        price_el = card.select_one(
            'span[data-test="property-card-price"], '
            'div[class*="price"], '
            'span[class*="PropertyCardWrapper__StyledPriceLine"]'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        # Address
        addr_el = card.select_one(
            'address[data-test="property-card-addr"], '
            'a[data-test="property-card-link"] address, '
            'address'
        )
        full_address = addr_el.get_text(strip=True) if addr_el else ""

        # Parse address components
        address, city, state, zip_code = self._split_address(full_address)

        # Beds / Baths / Sqft
        beds = 0
        baths = 0.0
        sqft = 0

        detail_els = card.select(
            'ul[class*="StyledPropertyCardHomeDetailsList"] li, '
            'div[class*="property-card-data"] span'
        )
        for el in detail_els:
            text = el.get_text(strip=True).lower()
            if "bd" in text or "bed" in text:
                beds = self._clean_int(text)
            elif "ba" in text or "bath" in text:
                baths = self._clean_float(text)
            elif "sqft" in text or "sq ft" in text:
                sqft = self._clean_int(text.replace(",", ""))

        # URL
        link_el = card.select_one("a[href*='/homedetails/']")
        detail_url = ""
        if link_el:
            href = link_el.get("href", "")
            detail_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        if not address and not price:
            return None

        return PropertyData(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            price=price,
            bedrooms=beds,
            bathrooms=baths,
            sqft=sqft,
            url=detail_url,
            source="zillow",
        )

    # ------------------------------------------------------------------
    # Parsing: Detail page
    # ------------------------------------------------------------------

    def _parse_detail_page(self, html: str) -> Optional[PropertyData]:
        """Parse a Zillow property detail page."""
        # Try __NEXT_DATA__ first
        next_data = self._extract_next_data(html)
        if next_data:
            try:
                gdp = (
                    next_data.get("props", {})
                    .get("pageProps", {})
                    .get("componentProps", {})
                    .get("gdpClientCache", {})
                )
                # gdpClientCache is keyed by zpid
                for key, val in gdp.items():
                    if isinstance(val, str):
                        val = json.loads(val)
                    prop_data = val.get("property", {})
                    if prop_data:
                        return self._map_detail_data(prop_data)
            except Exception as exc:
                logger.debug("Detail __NEXT_DATA__ parsing failed: %s", exc)

        soup = BeautifulSoup(html, "html.parser")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, dict) and ld.get("@type") in (
                    "SingleFamilyResidence",
                    "Product",
                    "RealEstateListing",
                ):
                    return self._parse_json_ld(ld)
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: parse key elements
        price_el = soup.select_one(
            'span[data-testid="price"], '
            'span[class*="ds-value"], '
            'span[class*="Price"]'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        addr_el = soup.select_one('h1[class*="address"], h1[data-testid="bdp-heading"]')
        full_address = addr_el.get_text(strip=True) if addr_el else ""
        address, city, state, zip_code = self._split_address(full_address)

        # Facts
        beds, baths, sqft, year_built, lot_size = 0, 0.0, 0, 0, 0
        fact_items = soup.select(
            'span[data-testid="bed-bath-item"], '
            'span[class*="ds-bed-bath-living-area"] span'
        )
        for item in fact_items:
            text = item.get_text(strip=True).lower()
            if "bed" in text:
                beds = self._clean_int(text)
            elif "bath" in text:
                baths = self._clean_float(text)
            elif "sqft" in text and "lot" not in text:
                sqft = self._clean_int(text.replace(",", ""))

        # Year built from facts table
        fact_rows = soup.select('div[class*="fact-value"], span[class*="fact-value"]')
        for row in fact_rows:
            text = row.get_text(strip=True)
            if re.match(r"^(19|20)\d{2}$", text):
                year_built = int(text)
                break

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
            lot_size_sqft=lot_size,
            source="zillow",
        )

    def _map_detail_data(self, data: dict) -> PropertyData:
        """Map Zillow's internal property data to PropertyData."""
        addr = data.get("address", {})
        return PropertyData(
            address=addr.get("streetAddress", ""),
            city=addr.get("city", ""),
            state=addr.get("state", ""),
            zip_code=str(addr.get("zipcode", "")),
            price=float(data.get("price", 0)),
            bedrooms=int(data.get("bedrooms", 0)),
            bathrooms=float(data.get("bathrooms", 0)),
            sqft=int(data.get("livingArea", 0)),
            lot_size_sqft=int(data.get("lotSize", 0)),
            year_built=int(data.get("yearBuilt", 0)),
            property_type=self._map_property_type(data.get("homeType", "")),
            latitude=float(data.get("latitude", 0)),
            longitude=float(data.get("longitude", 0)),
            tax_annual=float(data.get("annualHomeownersTaxes", 0)),
            hoa_monthly=float(data.get("monthlyHoaFee", 0)),
            days_on_market=int(data.get("daysOnZillow", 0)),
            description=data.get("description", ""),
            url=data.get("url", ""),
            mls_id=str(data.get("zpid", "")),
            source="zillow",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_next_data(html: str) -> Optional[dict]:
        match = re.search(
            r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _parse_json_ld(ld: dict) -> Optional[PropertyData]:
        if not isinstance(ld, dict):
            return None

        address_obj = ld.get("address", {})
        geo = ld.get("geo", {})
        floor_size = ld.get("floorSize", {})

        sqft_val = 0
        if isinstance(floor_size, dict):
            sqft_val = int(float(floor_size.get("value", 0)))
        elif isinstance(floor_size, (int, float)):
            sqft_val = int(floor_size)

        price_val = 0.0
        offers = ld.get("offers", {})
        if isinstance(offers, dict):
            price_val = float(offers.get("price", 0))
        elif "price" in ld:
            price_val = float(ld["price"])

        return PropertyData(
            address=address_obj.get("streetAddress", ld.get("name", "")),
            city=address_obj.get("addressLocality", ""),
            state=address_obj.get("addressRegion", ""),
            zip_code=str(address_obj.get("postalCode", "")),
            price=price_val,
            bedrooms=int(ld.get("numberOfRooms", ld.get("numberOfBedrooms", 0))),
            bathrooms=float(ld.get("numberOfBathroomsTotal", 0)),
            sqft=sqft_val,
            year_built=int(ld.get("yearBuilt", 0)),
            latitude=float(geo.get("latitude", 0)),
            longitude=float(geo.get("longitude", 0)),
            source="zillow",
        )

    @staticmethod
    def _map_property_type(raw: str) -> str:
        mapping = {
            "SINGLE_FAMILY": "single_family",
            "MULTI_FAMILY": "multi_family",
            "CONDO": "condo",
            "TOWNHOUSE": "townhouse",
            "APARTMENT": "multi_family",
            "MANUFACTURED": "single_family",
            "LOT": "land",
        }
        return mapping.get(raw.upper(), "single_family")

    @staticmethod
    def _split_address(full: str) -> tuple[str, str, str, str]:
        """Split '123 Main St, Dallas, TX 75201' into components."""
        parts = [p.strip() for p in full.split(",")]
        address = parts[0] if len(parts) >= 1 else ""
        city = parts[1] if len(parts) >= 2 else ""
        state_zip = parts[2] if len(parts) >= 3 else parts[1] if len(parts) == 2 else ""

        state = ""
        zip_code = ""
        sz_parts = state_zip.strip().split()
        if len(sz_parts) >= 2:
            state = sz_parts[0]
            zip_code = sz_parts[1]
        elif len(sz_parts) == 1:
            if sz_parts[0].isdigit():
                zip_code = sz_parts[0]
            else:
                state = sz_parts[0]

        return address, city, state, zip_code
