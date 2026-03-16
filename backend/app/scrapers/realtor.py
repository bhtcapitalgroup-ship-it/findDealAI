"""
RealDeal AI - Realtor.com Scraper

Extracts property listings from Realtor.com using their internal API-like
endpoints and HTML parsing as a fallback.
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


class RealtorScraper(BaseScraper):
    """Scrape Realtor.com using their API endpoints and HTML parsing."""

    SOURCE_NAME = "realtor"
    BASE_URL = "https://www.realtor.com"
    API_URL = "https://www.realtor.com/api/v1/hulk"
    GRAPHQL_URL = "https://www.realtor.com/frontdoor/graphql"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @rate_limit(calls_per_second=0.4)
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a Realtor.com URL."""
        html = await self._fetch(url)

        if "/realestateandhomes-detail/" in url:
            prop = self._parse_detail_page(html, url)
            return {
                "properties": [prop] if prop else [],
                "total_results": 1 if prop else 0,
                "current_page": 1,
                "total_pages": 1,
            }

        return self._parse_search_page(html)

    async def scrape_search(
        self,
        city: str,
        state: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        beds_min: Optional[int] = None,
        status: str = "for-sale",
        page: int = 1,
        limit: int = 42,
    ) -> dict[str, Any]:
        """
        Search Realtor.com via their GraphQL-like API endpoint.
        Falls back to HTML scraping if the API call fails.
        """
        offset = (page - 1) * limit

        query = self._build_graphql_query(
            city=city,
            state=state,
            status=status,
            min_price=min_price,
            max_price=max_price,
            beds_min=beds_min,
            offset=offset,
            limit=limit,
        )

        try:
            data = await self._post_graphql(query)
            return self._parse_graphql_response(data)
        except (ScrapingError, KeyError, TypeError) as exc:
            logger.warning("Realtor API failed, falling back to HTML: %s", exc)

        # Fallback: HTML
        slug = f"{city.replace(' ', '_')}_{state}".upper()
        url = f"{self.BASE_URL}/realestateandhomes-search/{slug}"
        filters = []
        if min_price:
            filters.append(f"price-{min_price}-na")
        if max_price:
            filters.append(f"price-na-{max_price}")
        if beds_min:
            filters.append(f"beds-{beds_min}")
        if filters:
            url += "/" + "/".join(filters)
        if page > 1:
            url += f"/pg-{page}"

        html = await self._fetch(url)
        return self._parse_search_page(html)

    async def scrape_all_pages(
        self,
        city: str,
        state: str,
        max_pages: int = 20,
        **kwargs,
    ) -> list[PropertyData]:
        """Iterate through all pages for a market."""
        all_properties: list[PropertyData] = []
        seen: set[str] = set()

        for page in range(1, max_pages + 1):
            try:
                result = await self.scrape_search(city, state, page=page, **kwargs)
                properties = result.get("properties", [])

                if not properties:
                    break

                for prop in properties:
                    fp = self._fingerprint(
                        {"address": prop.address, "zip_code": prop.zip_code, "price": prop.price}
                    )
                    if fp not in seen:
                        seen.add(fp)
                        all_properties.append(prop)

                total_pages = result.get("total_pages", 1)
                if page >= total_pages:
                    break

                logger.info(
                    "Realtor page %d/%d: %d properties (%d total)",
                    page, total_pages, len(properties), len(all_properties),
                )
            except ScrapingError as exc:
                logger.error("Failed on page %d: %s", page, exc)
                break

        return all_properties

    def parse(self, raw_html: str) -> list[PropertyData]:
        result = self._parse_search_page(raw_html)
        return result.get("properties", [])

    # ------------------------------------------------------------------
    # GraphQL API
    # ------------------------------------------------------------------

    def _build_graphql_query(
        self,
        city: str,
        state: str,
        status: str = "for-sale",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        beds_min: Optional[int] = None,
        offset: int = 0,
        limit: int = 42,
    ) -> dict:
        variables = {
            "query": {
                "status": ["for_sale"] if status == "for-sale" else [status.replace("-", "_")],
                "primary": True,
            },
            "client_data": {"device_data": {"device_type": "web"}},
            "limit": limit,
            "offset": offset,
            "sort_type": "relevant",
            "operationName": "ConsumerSearchQuery",
        }

        # Location filter
        variables["query"]["search_location"] = {
            "location": f"{city}, {state}",
        }

        # Price filter
        if min_price or max_price:
            price_filter = {}
            if min_price:
                price_filter["min"] = min_price
            if max_price:
                price_filter["max"] = max_price
            variables["query"]["list_price"] = price_filter

        # Beds filter
        if beds_min:
            variables["query"]["beds"] = {"min": beds_min}

        return {
            "query": """
                query ConsumerSearchQuery(
                    $query: HomeSearchCriteria!,
                    $limit: Int,
                    $offset: Int,
                    $sort_type: SearchSortType
                ) {
                    home_search(
                        query: $query,
                        sort: $sort_type,
                        limit: $limit,
                        offset: $offset
                    ) {
                        total
                        results {
                            property_id
                            list_price
                            description {
                                beds
                                baths
                                baths_full
                                sqft
                                lot_sqft
                                type
                                year_built
                                garage
                                text
                            }
                            location {
                                address {
                                    line
                                    city
                                    state_code
                                    postal_code
                                    coordinate {
                                        lat
                                        lon
                                    }
                                }
                            }
                            list_date
                            last_update_date
                            tags
                            href
                            status
                            source {
                                id
                                type
                            }
                            hoa {
                                fee
                            }
                            tax_record {
                                public_record_id
                                assessed_value
                                tax_amount
                                tax_year
                            }
                        }
                    }
                }
            """,
            "variables": variables,
        }

    async def _post_graphql(self, payload: dict) -> dict:
        """POST to the Realtor.com GraphQL endpoint."""
        session = await self._get_session()
        headers = self._get_headers()
        headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/",
        })
        proxy = self._get_proxy()

        for attempt in range(self.MAX_RETRIES):
            try:
                async with session.post(
                    self.GRAPHQL_URL,
                    json=payload,
                    headers=headers,
                    proxy=proxy,
                    ssl=False,
                ) as resp:
                    self._request_count += 1
                    if resp.status == 200:
                        return await resp.json(content_type=None)

                    if resp.status == 429:
                        import asyncio
                        await asyncio.sleep(int(resp.headers.get("Retry-After", 5)))
                        continue

                    logger.warning("GraphQL returned status %d", resp.status)

            except Exception as exc:
                logger.warning("GraphQL request failed (attempt %d): %s", attempt + 1, exc)

            import asyncio
            backoff = self.BASE_BACKOFF * (2 ** attempt)
            await asyncio.sleep(backoff)

        raise ScrapingError("Realtor GraphQL endpoint failed after retries")

    def _parse_graphql_response(self, data: dict) -> dict[str, Any]:
        properties: list[PropertyData] = []
        home_search = data.get("data", {}).get("home_search", {})
        results = home_search.get("results", [])
        total = home_search.get("total", 0)

        for item in results:
            try:
                prop = self._map_graphql_result(item)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Error parsing Realtor result: %s", exc)

        return {
            "properties": properties,
            "total_results": total,
            "current_page": 1,
            "total_pages": max(1, (total + 42 - 1) // 42),
        }

    def _map_graphql_result(self, item: dict) -> Optional[PropertyData]:
        desc = item.get("description", {}) or {}
        location = item.get("location", {}) or {}
        address = location.get("address", {}) or {}
        coord = address.get("coordinate", {}) or {}
        hoa_info = item.get("hoa", {}) or {}
        tax_info = item.get("tax_record", {}) or {}

        property_type_raw = desc.get("type", "")
        property_type = self._map_property_type(property_type_raw)

        hoa_fee = float(hoa_info.get("fee", 0) or 0)
        tax_amount = float(tax_info.get("tax_amount", 0) or 0)

        href = item.get("href", "")
        full_url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href

        return PropertyData(
            address=address.get("line", ""),
            city=address.get("city", ""),
            state=address.get("state_code", ""),
            zip_code=str(address.get("postal_code", "")),
            price=float(item.get("list_price", 0) or 0),
            bedrooms=int(desc.get("beds", 0) or 0),
            bathrooms=float(desc.get("baths", 0) or 0),
            sqft=int(desc.get("sqft", 0) or 0),
            lot_size_sqft=int(desc.get("lot_sqft", 0) or 0),
            year_built=int(desc.get("year_built", 0) or 0),
            property_type=property_type,
            garage=bool(desc.get("garage")),
            hoa_monthly=hoa_fee,
            tax_annual=tax_amount,
            latitude=float(coord.get("lat", 0) or 0),
            longitude=float(coord.get("lon", 0) or 0),
            description=str(desc.get("text", "") or ""),
            url=full_url,
            mls_id=str(item.get("property_id", "")),
            source="realtor",
        )

    # ------------------------------------------------------------------
    # HTML Parsing
    # ------------------------------------------------------------------

    def _parse_search_page(self, html: str) -> dict[str, Any]:
        properties: list[PropertyData] = []
        soup = BeautifulSoup(html, "html.parser")

        # Try embedded JSON data
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Look for search results in various structures
                    results = self._find_nested_results(data)
                    for item in results:
                        prop = self._map_graphql_result(item)
                        if prop and prop.price > 0:
                            properties.append(prop)
            except (json.JSONDecodeError, TypeError):
                continue

        # Parse listing cards
        cards = soup.select(
            'div[data-testid="property-card"], '
            'li[data-testid="result-card"], '
            'div[class*="BasePropertyCard"], '
            'div[class*="PropertyCard"]'
        )

        for card in cards:
            try:
                prop = self._parse_listing_card(card)
                if prop and prop.price > 0:
                    properties.append(prop)
            except Exception as exc:
                logger.debug("Realtor card parse error: %s", exc)

        # Dedup
        seen: set[str] = set()
        unique: list[PropertyData] = []
        for p in properties:
            fp = self._fingerprint({"address": p.address, "zip_code": p.zip_code, "price": p.price})
            if fp not in seen:
                seen.add(fp)
                unique.append(p)

        total_el = soup.select_one(
            'div[data-testid="total-results"], '
            'span[class*="result-count"]'
        )
        total = self._clean_int(total_el.get_text()) if total_el else len(unique)

        return {
            "properties": unique,
            "total_results": total,
            "current_page": 1,
            "total_pages": max(1, (total + 42 - 1) // 42),
        }

    def _parse_listing_card(self, card) -> Optional[PropertyData]:
        price_el = card.select_one(
            'span[data-testid="card-price"], '
            'span[class*="card-price"]'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        addr_el = card.select_one(
            'div[data-testid="card-address"], '
            'div[class*="card-address"]'
        )
        full_address = addr_el.get_text(strip=True) if addr_el else ""

        # Split address lines
        address_parts = full_address.split(",")
        address = address_parts[0].strip() if address_parts else ""
        city = address_parts[1].strip() if len(address_parts) > 1 else ""
        state, zip_code = "", ""
        if len(address_parts) > 2:
            sz = address_parts[2].strip().split()
            state = sz[0] if sz else ""
            zip_code = sz[1] if len(sz) > 1 else ""

        # Beds/Baths/Sqft
        beds, baths, sqft = 0, 0.0, 0
        meta_items = card.select(
            'li[data-testid="property-meta-beds"], '
            'li[data-testid="property-meta-baths"], '
            'li[data-testid="property-meta-sqft"], '
            'span[class*="meta-value"]'
        )
        for item in meta_items:
            text = item.get_text(strip=True).lower()
            testid = item.get("data-testid", "")
            if "bed" in testid or "bed" in text:
                beds = self._clean_int(text)
            elif "bath" in testid or "bath" in text:
                baths = self._clean_float(text)
            elif "sqft" in testid or "sq" in text:
                sqft = self._clean_int(text.replace(",", ""))

        link = card.select_one('a[href*="/realestateandhomes-detail/"]')
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
            source="realtor",
        )

    def _parse_detail_page(self, html: str, url: str = "") -> Optional[PropertyData]:
        soup = BeautifulSoup(html, "html.parser")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, dict) and ld.get("@type") in (
                    "SingleFamilyResidence",
                    "Product",
                    "Residence",
                ):
                    return self._parse_json_ld_detail(ld, url)
            except (json.JSONDecodeError, TypeError):
                continue

        # HTML parsing
        price_el = soup.select_one(
            'div[data-testid="list-price"], '
            'span[class*="ldp-header-price"]'
        )
        price = self._clean_price(price_el.get_text()) if price_el else 0

        addr_el = soup.select_one(
            'h1[data-testid="address-line"], '
            'div[class*="ldp-header-address"]'
        )
        full_address = addr_el.get_text(strip=True) if addr_el else ""
        parts = [p.strip() for p in full_address.split(",")]
        address = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
        state, zip_code = "", ""
        if len(parts) > 2:
            sz = parts[2].strip().split()
            state = sz[0] if sz else ""
            zip_code = sz[1] if len(sz) > 1 else ""

        beds, baths, sqft, year_built, lot_size = 0, 0.0, 0, 0, 0
        for item in soup.select('li[data-testid*="property-meta"], div[class*="key-fact"]'):
            text = item.get_text(strip=True).lower()
            if "bed" in text:
                beds = self._clean_int(text)
            elif "bath" in text:
                baths = self._clean_float(text)
            elif "sqft" in text and "lot" not in text:
                sqft = self._clean_int(text.replace(",", ""))
            elif "built" in text or "year" in text:
                match = re.search(r"(\d{4})", text)
                if match:
                    year_built = int(match.group(1))
            elif "lot" in text and "sqft" in text:
                lot_size = self._clean_int(text.replace(",", ""))

        desc_el = soup.select_one(
            'div[data-testid="listing-description"], '
            'div[class*="ldp-description"]'
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
            lot_size_sqft=lot_size,
            description=description,
            url=url,
            source="realtor",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_nested_results(data: dict, depth: int = 0) -> list[dict]:
        """Recursively search for property results in nested JSON."""
        if depth > 5:
            return []

        if "results" in data and isinstance(data["results"], list):
            return data["results"]

        results: list[dict] = []
        for key, val in data.items():
            if isinstance(val, dict):
                results.extend(RealtorScraper._find_nested_results(val, depth + 1))
            elif isinstance(val, list) and val and isinstance(val[0], dict):
                if any(k in val[0] for k in ("list_price", "property_id", "price")):
                    return val

        return results

    @staticmethod
    def _map_property_type(raw: str) -> str:
        mapping = {
            "single_family": "single_family",
            "condo": "condo",
            "condos": "condo",
            "townhome": "townhouse",
            "townhouse": "townhouse",
            "multi_family": "multi_family",
            "apartment": "multi_family",
            "land": "land",
            "farm": "land",
            "mobile": "single_family",
        }
        return mapping.get(raw.lower().replace("-", "_").replace(" ", "_"), "single_family")

    @staticmethod
    def _parse_json_ld_detail(ld: dict, url: str = "") -> PropertyData:
        address_obj = ld.get("address", {})
        geo = ld.get("geo", {})

        sqft = 0
        floor_size = ld.get("floorSize", {})
        if isinstance(floor_size, dict):
            sqft = int(float(floor_size.get("value", 0)))

        price = 0.0
        offers = ld.get("offers", {})
        if isinstance(offers, dict):
            price = float(offers.get("price", 0))

        return PropertyData(
            address=address_obj.get("streetAddress", ld.get("name", "")),
            city=address_obj.get("addressLocality", ""),
            state=address_obj.get("addressRegion", ""),
            zip_code=str(address_obj.get("postalCode", "")),
            price=price,
            bedrooms=int(ld.get("numberOfRooms", ld.get("numberOfBedrooms", 0))),
            bathrooms=float(ld.get("numberOfBathroomsTotal", 0)),
            sqft=sqft,
            year_built=int(ld.get("yearBuilt", 0)),
            latitude=float(geo.get("latitude", 0)),
            longitude=float(geo.get("longitude", 0)),
            description=str(ld.get("description", "")),
            url=url,
            source="realtor",
        )
