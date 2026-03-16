"""
RealDeal AI - Public Records Scraper

Scrapes county assessor websites and public records portals for tax records,
ownership history, assessment values, and deed information.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup

from app.ai.deal_analyzer import PropertyData
from app.scrapers.base import BaseScraper, ScrapingError, rate_limit

logger = logging.getLogger(__name__)


@dataclass
class TaxRecord:
    """Tax assessment record from county assessor."""

    parcel_id: str = ""
    owner_name: str = ""
    owner_address: str = ""
    property_address: str = ""
    assessed_value: float = 0.0
    market_value: float = 0.0
    land_value: float = 0.0
    improvement_value: float = 0.0
    tax_amount: float = 0.0
    tax_year: int = 0
    tax_rate: float = 0.0
    exemptions: list[str] = field(default_factory=list)
    last_sale_date: str = ""
    last_sale_price: float = 0.0
    legal_description: str = ""
    zoning: str = ""
    land_sqft: int = 0
    building_sqft: int = 0
    year_built: int = 0
    bedrooms: int = 0
    bathrooms: float = 0.0
    stories: int = 0
    property_class: str = ""
    school_district: str = ""
    county: str = ""
    state: str = ""


# Common county assessor URL patterns by state
COUNTY_ASSESSOR_URLS = {
    "TX": {
        "base_pattern": "https://{county}cad.org/property-search",
        "search_pattern": "https://{county}cad.org/property-search?query={address}",
        "counties": {
            "dallas": "dallascad",
            "harris": "hcad",
            "tarrant": "tad",
            "bexar": "bexar",
            "travis": "traviscad",
        },
    },
    "FL": {
        "base_pattern": "https://{county}appraiser.com/property-search",
        "search_pattern": "https://{county}appraiser.com/property-search?address={address}",
        "counties": {
            "miami-dade": "miamidade",
            "broward": "bcpa",
            "palm-beach": "pbcgov",
            "hillsborough": "hcpafl",
            "orange": "ocpafl",
        },
    },
    "CA": {
        "base_pattern": "https://assessor.{county}.gov/propertysearch",
        "search_pattern": "https://assessor.{county}.gov/propertysearch?address={address}",
        "counties": {
            "los-angeles": "lacounty",
            "san-diego": "sdcounty",
            "orange": "ocgov",
            "san-bernardino": "sbcounty",
            "riverside": "riversidecounty",
        },
    },
    "GA": {
        "base_pattern": "https://qpublic.schneidercorp.com/Application.aspx?AppID={app_id}",
        "counties": {
            "fulton": "834",
            "dekalb": "835",
            "gwinnett": "836",
            "cobb": "837",
        },
    },
    "OH": {
        "base_pattern": "https://{county}.oh.us/auditor/search",
        "counties": {
            "franklin": "franklin",
            "cuyahoga": "cuyahoga",
            "hamilton": "hamilton",
            "summit": "summit",
        },
    },
}

# Generic public records search engines
PUBLIC_RECORDS_SOURCES = [
    "https://publicrecords.searchsystems.net",
    "https://www.countyoffice.org/{county}-county-{state}-property-records",
]


class PublicRecordsScraper(BaseScraper):
    """Scrape county assessor data for tax records and ownership information."""

    SOURCE_NAME = "public_records"
    MAX_RETRIES = 2  # County sites can be flaky

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @rate_limit(calls_per_second=0.25)
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a county assessor page."""
        html = await self._fetch(url)
        record = self._parse_assessor_page(html)
        return {"tax_record": record.__dict__ if record else {}, "url": url}

    async def get_tax_record(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str = "",
        county: str = "",
    ) -> Optional[TaxRecord]:
        """
        Look up tax record for a property.
        Tries multiple sources in order of reliability.
        """
        # Strategy 1: Direct county assessor lookup
        if county and state:
            record = await self._search_county_assessor(
                address, city, state, county
            )
            if record and record.assessed_value > 0:
                return record

        # Strategy 2: State-level property search
        record = await self._search_state_records(address, city, state, zip_code)
        if record and record.assessed_value > 0:
            return record

        # Strategy 3: Generic public records search
        record = await self._search_generic_records(address, city, state, zip_code)
        if record:
            return record

        logger.warning(
            "No public records found for %s, %s, %s", address, city, state
        )
        return None

    async def get_ownership_history(
        self,
        address: str,
        city: str,
        state: str,
        county: str = "",
    ) -> list[dict[str, Any]]:
        """Fetch ownership / sale history for a property."""
        full_address = f"{address}, {city}, {state}"

        # Try county assessor's deed/transfer page
        search_url = self._build_county_url(state, county, address, "transfers")
        if not search_url:
            search_url = f"https://www.countyoffice.org/{county or city.lower().replace(' ', '-')}-county-{state.lower()}-property-records/?q={quote(full_address)}"

        try:
            html = await self._fetch(search_url)
            return self._parse_ownership_history(html)
        except ScrapingError as exc:
            logger.warning("Ownership history lookup failed: %s", exc)
            return []

    async def get_tax_for_property(self, property: PropertyData) -> Optional[TaxRecord]:
        """Convenience: look up tax record for a PropertyData."""
        return await self.get_tax_record(
            address=property.address,
            city=property.city,
            state=property.state,
            zip_code=property.zip_code,
        )

    def parse(self, raw_html: str) -> list[PropertyData]:
        """Parse public records into PropertyData (limited fields)."""
        record = self._parse_assessor_page(raw_html)
        if not record:
            return []

        prop = PropertyData(
            address=record.property_address,
            state=record.state,
            sqft=record.building_sqft,
            lot_size_sqft=record.land_sqft,
            year_built=record.year_built,
            bedrooms=record.bedrooms,
            bathrooms=record.bathrooms,
            stories=record.stories,
            tax_annual=record.tax_amount,
            price=record.last_sale_price if record.last_sale_price > 0 else record.market_value,
            source="public_records",
        )
        return [prop]

    # ------------------------------------------------------------------
    # County assessor search
    # ------------------------------------------------------------------

    async def _search_county_assessor(
        self, address: str, city: str, state: str, county: str
    ) -> Optional[TaxRecord]:
        url = self._build_county_url(state, county, address)
        if not url:
            return None

        try:
            html = await self._fetch(url)
            return self._parse_assessor_page(html, state=state, county=county)
        except ScrapingError as exc:
            logger.debug("County assessor search failed: %s", exc)
            return None

    async def _search_state_records(
        self, address: str, city: str, state: str, zip_code: str
    ) -> Optional[TaxRecord]:
        """Try state-level property tax portals."""
        state_urls = {
            "TX": f"https://propaccess.trueautomation.com/clientdb/?cid=110&prop_id=&legal_desc=&prop_val_yr=2025&situs_street={quote(address)}&situs_city={quote(city)}",
            "FL": f"https://www.pbcgov.org/papa/property-search/?address={quote(address)}&city={quote(city)}&zip={zip_code}",
            "CA": f"https://www.californiaassessors.com/search?address={quote(address)}&city={quote(city)}&zip={zip_code}",
            "GA": f"https://qpublic.schneidercorp.com/Search?address={quote(address)}&city={quote(city)}&state={state}",
        }

        url = state_urls.get(state)
        if not url:
            return None

        try:
            html = await self._fetch(url)
            return self._parse_assessor_page(html, state=state)
        except ScrapingError:
            return None

    async def _search_generic_records(
        self, address: str, city: str, state: str, zip_code: str
    ) -> Optional[TaxRecord]:
        """Search generic public records aggregators."""
        full_address = f"{address}, {city}, {state} {zip_code}"

        # Try a generic records search
        url = f"https://www.countyoffice.org/property-records-search/?q={quote(full_address)}"

        try:
            html = await self._fetch(url)
            return self._parse_generic_records(html, state)
        except ScrapingError:
            return None

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------

    def _build_county_url(
        self,
        state: str,
        county: str,
        address: str,
        page_type: str = "search",
    ) -> Optional[str]:
        state_config = COUNTY_ASSESSOR_URLS.get(state.upper())
        if not state_config:
            return None

        county_key = county.lower().replace(" ", "-")
        counties = state_config.get("counties", {})
        county_code = counties.get(county_key)
        if not county_code:
            # Try partial match
            for k, v in counties.items():
                if county_key in k or k in county_key:
                    county_code = v
                    break

        if not county_code:
            return None

        if page_type == "transfers":
            return f"https://{county_code}.org/deed-search?address={quote(address)}"

        pattern = state_config.get("search_pattern", "")
        return pattern.format(county=county_code, address=quote(address))

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_assessor_page(
        self, html: str, state: str = "", county: str = ""
    ) -> Optional[TaxRecord]:
        """Parse a county assessor property page."""
        soup = BeautifulSoup(html, "html.parser")
        record = TaxRecord(state=state, county=county)

        # Try JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, dict):
                    record = self._map_json_ld_to_tax(ld, record)
                    if record.assessed_value > 0:
                        return record
            except (json.JSONDecodeError, TypeError):
                continue

        # Parse table-based layouts (most county sites use these)
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    self._map_label_value(record, label, value)

        # Parse definition-list layouts
        for dl in soup.find_all("dl"):
            terms = dl.find_all("dt")
            defs = dl.find_all("dd")
            for dt, dd in zip(terms, defs):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                self._map_label_value(record, label, value)

        # Parse key-value div layouts
        for div in soup.select(
            'div[class*="detail-row"], '
            'div[class*="property-detail"], '
            'div[class*="data-row"], '
            'div[class*="info-row"]'
        ):
            label_el = div.select_one(
                'span[class*="label"], '
                'dt, '
                'div[class*="label"], '
                'strong'
            )
            value_el = div.select_one(
                'span[class*="value"], '
                'dd, '
                'div[class*="value"], '
                'span:last-child'
            )
            if label_el and value_el:
                label = label_el.get_text(strip=True).lower()
                value = value_el.get_text(strip=True)
                self._map_label_value(record, label, value)

        # Parcel / property ID
        parcel_el = soup.select_one(
            'span[class*="parcel"], '
            'td[class*="parcel"], '
            'div[class*="parcel-id"]'
        )
        if parcel_el and not record.parcel_id:
            record.parcel_id = parcel_el.get_text(strip=True)

        # Owner name
        owner_el = soup.select_one(
            'span[class*="owner"], '
            'td[class*="owner"], '
            'div[class*="owner-name"]'
        )
        if owner_el and not record.owner_name:
            record.owner_name = owner_el.get_text(strip=True)

        if record.assessed_value > 0 or record.owner_name:
            return record
        return None

    def _parse_generic_records(self, html: str, state: str) -> Optional[TaxRecord]:
        """Parse generic public records search results."""
        soup = BeautifulSoup(html, "html.parser")
        record = TaxRecord(state=state)

        # Look for property cards in search results
        cards = soup.select(
            'div[class*="property-card"], '
            'div[class*="result-card"], '
            'div[class*="record-item"]'
        )

        if not cards:
            return None

        # Take the first (most relevant) result
        card = cards[0]

        addr_el = card.select_one('span[class*="address"], div[class*="address"]')
        if addr_el:
            record.property_address = addr_el.get_text(strip=True)

        owner_el = card.select_one('span[class*="owner"], div[class*="owner"]')
        if owner_el:
            record.owner_name = owner_el.get_text(strip=True)

        value_el = card.select_one('span[class*="value"], div[class*="assessed"]')
        if value_el:
            record.assessed_value = self._clean_price(value_el.get_text())

        tax_el = card.select_one('span[class*="tax"], div[class*="tax-amount"]')
        if tax_el:
            record.tax_amount = self._clean_price(tax_el.get_text())

        return record if (record.assessed_value > 0 or record.owner_name) else None

    def _parse_ownership_history(self, html: str) -> list[dict[str, Any]]:
        """Parse deed transfer / ownership history."""
        soup = BeautifulSoup(html, "html.parser")
        history: list[dict[str, Any]] = []

        tables = soup.find_all("table")
        for table in tables:
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if not any(
                kw in " ".join(headers)
                for kw in ("date", "sale", "deed", "transfer", "grantor", "grantee")
            ):
                continue

            for row in table.find_all("tr")[1:]:  # Skip header
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 2:
                    continue

                entry: dict[str, Any] = {}
                for i, header in enumerate(headers):
                    if i < len(cells):
                        val = cells[i]
                        if "date" in header:
                            entry["date"] = val
                        elif "price" in header or "amount" in header or "sale" in header:
                            entry["sale_price"] = self._clean_price(val)
                        elif "grantor" in header or "seller" in header:
                            entry["seller"] = val
                        elif "grantee" in header or "buyer" in header:
                            entry["buyer"] = val
                        elif "deed" in header or "type" in header:
                            entry["deed_type"] = val
                        elif "book" in header:
                            entry["book"] = val
                        elif "page" in header:
                            entry["page"] = val

                if entry:
                    history.append(entry)

        # Also try list-based layouts
        for item in soup.select(
            'div[class*="transfer-item"], '
            'div[class*="sale-history-row"], '
            'li[class*="history-item"]'
        ):
            entry = {}
            date_el = item.select_one('span[class*="date"]')
            price_el = item.select_one('span[class*="price"], span[class*="amount"]')
            buyer_el = item.select_one('span[class*="buyer"], span[class*="grantee"]')
            seller_el = item.select_one('span[class*="seller"], span[class*="grantor"]')

            if date_el:
                entry["date"] = date_el.get_text(strip=True)
            if price_el:
                entry["sale_price"] = self._clean_price(price_el.get_text())
            if buyer_el:
                entry["buyer"] = buyer_el.get_text(strip=True)
            if seller_el:
                entry["seller"] = seller_el.get_text(strip=True)

            if entry:
                history.append(entry)

        logger.info("Found %d ownership records", len(history))
        return history

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _map_label_value(self, record: TaxRecord, label: str, value: str):
        """Map a label-value pair to a TaxRecord field."""
        label = label.strip().rstrip(":").lower()

        if any(kw in label for kw in ("parcel", "pin", "property id", "account")):
            record.parcel_id = value
        elif any(kw in label for kw in ("owner", "taxpayer")):
            if not record.owner_name:
                record.owner_name = value
        elif "mail" in label and "address" in label:
            record.owner_address = value
        elif "situs" in label or ("property" in label and "address" in label):
            record.property_address = value
        elif "assessed" in label and "value" in label:
            record.assessed_value = self._clean_price(value)
        elif "market" in label and "value" in label:
            record.market_value = self._clean_price(value)
        elif "land" in label and "value" in label:
            record.land_value = self._clean_price(value)
        elif "improvement" in label and "value" in label:
            record.improvement_value = self._clean_price(value)
        elif ("tax" in label and "amount" in label) or label in ("taxes", "total tax"):
            record.tax_amount = self._clean_price(value)
        elif "tax" in label and "year" in label:
            record.tax_year = self._clean_int(value)
        elif "tax" in label and "rate" in label:
            record.tax_rate = self._clean_float(value)
        elif ("last" in label or "most recent" in label) and "sale" in label and "date" in label:
            record.last_sale_date = value
        elif ("last" in label or "most recent" in label) and "sale" in label and "price" in label:
            record.last_sale_price = self._clean_price(value)
        elif "legal" in label and "description" in label:
            record.legal_description = value
        elif "zoning" in label:
            record.zoning = value
        elif "land" in label and ("size" in label or "area" in label or "sqft" in label):
            record.land_sqft = self._clean_int(value.replace(",", ""))
        elif ("living" in label or "building" in label) and ("area" in label or "sqft" in label):
            record.building_sqft = self._clean_int(value.replace(",", ""))
        elif "year" in label and "built" in label:
            record.year_built = self._clean_int(value)
        elif label in ("bedrooms", "beds"):
            record.bedrooms = self._clean_int(value)
        elif label in ("bathrooms", "baths"):
            record.bathrooms = self._clean_float(value)
        elif label in ("stories", "floors"):
            record.stories = self._clean_int(value)
        elif "class" in label or "use" in label:
            record.property_class = value
        elif "school" in label and "district" in label:
            record.school_district = value
        elif "exemption" in label:
            record.exemptions.append(value)

    @staticmethod
    def _map_json_ld_to_tax(ld: dict, record: TaxRecord) -> TaxRecord:
        """Map JSON-LD data to a TaxRecord."""
        address = ld.get("address", {})
        if isinstance(address, dict):
            record.property_address = address.get("streetAddress", "")
            record.state = address.get("addressRegion", record.state)

        if "taxID" in ld:
            record.parcel_id = str(ld["taxID"])

        return record
