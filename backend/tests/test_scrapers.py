"""Unit tests for scrapers (mock HTTP responses, no real network calls)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.deal_analyzer import PropertyData
from app.scrapers.base import BaseScraper, ScrapingError, rate_limit
from app.scrapers.realtor import RealtorScraper
from app.scrapers.redfin import RedfinScraper
from app.scrapers.rentometer import RentometerScraper
from app.scrapers.public_records import PublicRecordsScraper
from app.scrapers.zillow import ZillowScraper


# ---------------------------------------------------------------------------
# Sample responses
# ---------------------------------------------------------------------------

ZILLOW_NEXT_DATA = json.dumps({
    "props": {
        "pageProps": {
            "searchPageState": {
                "cat1": {
                    "searchResults": {
                        "listResults": [
                            {
                                "hdpData": {
                                    "homeInfo": {
                                        "streetAddress": "123 Zillow St",
                                        "city": "Dallas",
                                        "state": "TX",
                                        "zipcode": "75201",
                                        "price": 350000,
                                        "bedrooms": 3,
                                        "bathrooms": 2.0,
                                        "livingArea": 1800,
                                        "yearBuilt": 2005,
                                        "homeType": "SINGLE_FAMILY",
                                        "daysOnZillow": 12,
                                        "zpid": "12345678",
                                        "latitude": 32.78,
                                        "longitude": -96.80,
                                    }
                                },
                                "detailUrl": "/homedetails/123-Zillow-St/12345678_zpid/",
                            }
                        ],
                        "totalResultCount": 1,
                    }
                }
            }
        }
    }
})

ZILLOW_SEARCH_HTML = f"""
<html>
<head>
<script id="__NEXT_DATA__" type="application/json">{ZILLOW_NEXT_DATA}</script>
</head>
<body></body>
</html>
"""

REDFIN_CSV_DATA = """ADDRESS,CITY,STATE OR PROVINCE,ZIP OR POSTAL CODE,PRICE,BEDS,BATHS,SQUARE FEET,LOT SIZE,YEAR BUILT,DAYS ON MARKET,HOA/MONTH,URL,MLS#,PROPERTY TYPE,LATITUDE,LONGITUDE
456 Redfin Ave,Austin,TX,78701,425000,4,2.5,2200,5000,2010,18,0,https://www.redfin.com/TX/Austin/456-Redfin-Ave,MLS123,Single Family Residential,30.27,-97.74
789 Oak Dr,Austin,TX,78702,280000,2,1,1100,3000,1985,45,50,https://www.redfin.com/TX/Austin/789-Oak-Dr,MLS456,Condo,30.26,-97.73
"""

REALTOR_GRAPHQL_RESPONSE = {
    "data": {
        "home_search": {
            "total": 1,
            "results": [
                {
                    "property_id": "R9876543",
                    "list_price": 299000,
                    "description": {
                        "beds": 3,
                        "baths": 2.0,
                        "baths_full": 2,
                        "sqft": 1600,
                        "lot_sqft": 7000,
                        "type": "single_family",
                        "year_built": 1998,
                        "garage": True,
                        "text": "Spacious single-family home.",
                    },
                    "location": {
                        "address": {
                            "line": "321 Realtor Blvd",
                            "city": "Houston",
                            "state_code": "TX",
                            "postal_code": "77001",
                            "coordinate": {"lat": 29.76, "lon": -95.37},
                        }
                    },
                    "href": "/realestateandhomes-detail/321-Realtor-Blvd_Houston_TX_77001",
                    "hoa": {"fee": 0},
                    "tax_record": {"tax_amount": 3500, "tax_year": 2025},
                    "status": "for_sale",
                    "source": {"id": "MLS-R1", "type": "mls"},
                }
            ],
        }
    }
}

RENTOMETER_HTML = """
<html>
<body>
<script>
var analysisData = {"median": 1650, "percentile_25": 1400, "percentile_75": 1900, "mean": 1630, "sample_size": 42, "min": 1100, "max": 2300};
</script>
</body>
</html>
"""

PUBLIC_RECORDS_HTML = """
<html>
<body>
<table>
  <tr><td>Parcel ID</td><td>TX-DAL-123456</td></tr>
  <tr><td>Owner Name</td><td>John Smith</td></tr>
  <tr><td>Property Address</td><td>100 County Rd, Dallas TX</td></tr>
  <tr><td>Assessed Value</td><td>$285,000</td></tr>
  <tr><td>Market Value</td><td>$310,000</td></tr>
  <tr><td>Tax Amount</td><td>$4,200</td></tr>
  <tr><td>Tax Year</td><td>2025</td></tr>
  <tr><td>Year Built</td><td>1995</td></tr>
  <tr><td>Bedrooms</td><td>3</td></tr>
  <tr><td>Bathrooms</td><td>2</td></tr>
  <tr><td>Living Area SqFt</td><td>1,650</td></tr>
</table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Zillow
# ---------------------------------------------------------------------------

class TestZillowScraper:
    """Tests for ZillowScraper parsing."""

    def test_zillow_parse_search_results(self):
        """Parsing Zillow search HTML with __NEXT_DATA__ should extract properties."""
        scraper = ZillowScraper()
        properties = scraper.parse(ZILLOW_SEARCH_HTML)

        assert len(properties) == 1
        prop = properties[0]
        assert isinstance(prop, PropertyData)
        assert prop.address == "123 Zillow St"
        assert prop.city == "Dallas"
        assert prop.state == "TX"
        assert prop.zip_code == "75201"
        assert prop.price == 350000
        assert prop.bedrooms == 3
        assert prop.bathrooms == 2.0
        assert prop.sqft == 1800
        assert prop.year_built == 2005
        assert prop.source == "zillow"

    def test_zillow_split_address(self):
        """The address splitter should handle standard US address formats."""
        addr, city, state, zip_code = ZillowScraper._split_address(
            "123 Main St, Dallas, TX 75201"
        )
        assert addr == "123 Main St"
        assert city == "Dallas"
        assert state == "TX"
        assert zip_code == "75201"

    def test_zillow_map_property_type(self):
        """Property type mapping should normalize Zillow types."""
        assert ZillowScraper._map_property_type("SINGLE_FAMILY") == "single_family"
        assert ZillowScraper._map_property_type("CONDO") == "condo"
        assert ZillowScraper._map_property_type("TOWNHOUSE") == "townhouse"
        assert ZillowScraper._map_property_type("MULTI_FAMILY") == "multi_family"
        assert ZillowScraper._map_property_type("UNKNOWN") == "single_family"


# ---------------------------------------------------------------------------
# Redfin
# ---------------------------------------------------------------------------

class TestRedfinScraper:
    """Tests for RedfinScraper CSV parsing."""

    def test_redfin_parse_csv(self):
        """Parsing Redfin CSV should extract property records correctly."""
        scraper = RedfinScraper()
        properties = scraper._parse_csv(REDFIN_CSV_DATA)

        assert len(properties) == 2

        first = properties[0]
        assert first.address == "456 Redfin Ave"
        assert first.city == "Austin"
        assert first.state == "TX"
        assert first.zip_code == "78701"
        assert first.price == 425000
        assert first.bedrooms == 4
        assert first.bathrooms == 2.5
        assert first.sqft == 2200
        assert first.year_built == 2010
        assert first.source == "redfin"

        second = properties[1]
        assert second.price == 280000
        assert second.hoa_monthly == 50.0


# ---------------------------------------------------------------------------
# Realtor
# ---------------------------------------------------------------------------

class TestRealtorScraper:
    """Tests for RealtorScraper GraphQL parsing."""

    def test_realtor_parse_graphql_response(self):
        """Parsing Realtor.com GraphQL response should map all fields."""
        scraper = RealtorScraper()
        result = scraper._parse_graphql_response(REALTOR_GRAPHQL_RESPONSE)

        assert result["total_results"] == 1
        properties = result["properties"]
        assert len(properties) == 1

        prop = properties[0]
        assert prop.address == "321 Realtor Blvd"
        assert prop.city == "Houston"
        assert prop.state == "TX"
        assert prop.zip_code == "77001"
        assert prop.price == 299000
        assert prop.bedrooms == 3
        assert prop.bathrooms == 2.0
        assert prop.sqft == 1600
        assert prop.year_built == 1998
        assert prop.garage is True
        assert prop.tax_annual == 3500
        assert prop.source == "realtor"


# ---------------------------------------------------------------------------
# Rentometer
# ---------------------------------------------------------------------------

class TestRentometerScraper:
    """Tests for RentometerScraper response parsing."""

    def test_rentometer_parse_response(self):
        """Parsing Rentometer HTML should extract rent statistics."""
        scraper = RentometerScraper()
        result = scraper._parse_results_page(RENTOMETER_HTML)

        assert result["median_rent"] == 1650
        assert result["percentile_25"] == 1400
        assert result["percentile_75"] == 1900
        assert result["mean_rent"] == 1630
        assert result["sample_size"] == 42
        assert result["min_rent"] == 1100
        assert result["max_rent"] == 2300


# ---------------------------------------------------------------------------
# Public Records
# ---------------------------------------------------------------------------

class TestPublicRecordsScraper:
    """Tests for PublicRecordsScraper parsing."""

    def test_public_records_parse(self):
        """Parsing a county assessor table should extract tax record fields."""
        scraper = PublicRecordsScraper()
        record = scraper._parse_assessor_page(PUBLIC_RECORDS_HTML, state="TX")

        assert record is not None
        assert record.parcel_id == "TX-DAL-123456"
        assert record.owner_name == "John Smith"
        assert record.assessed_value == 285000.0
        assert record.market_value == 310000.0
        assert record.tax_amount == 4200.0
        assert record.tax_year == 2025
        assert record.year_built == 1995
        assert record.bedrooms == 3
        assert record.bathrooms == 2.0
        assert record.building_sqft == 1650


# ---------------------------------------------------------------------------
# Base Scraper: retry and rate limiting
# ---------------------------------------------------------------------------

class TestBaseScraperRetry:
    """Tests for BaseScraper retry logic."""

    @pytest.mark.asyncio
    async def test_base_scraper_retry_on_failure(self):
        """The scraper should retry up to MAX_RETRIES on failures."""

        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            MAX_RETRIES = 3
            BASE_BACKOFF = 0.01  # fast for tests

            async def scrape(self, url):
                return {}

            def parse(self, raw_html):
                return []

        scraper = TestScraper()

        call_count = 0

        async def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Connection failed")

        # Mock the session
        mock_session = AsyncMock()
        mock_session.request = mock_request
        mock_session.closed = False
        scraper._session = mock_session

        with pytest.raises(ScrapingError):
            await scraper._fetch("http://example.com/test")

        assert call_count == 3  # MAX_RETRIES

    @pytest.mark.asyncio
    async def test_base_scraper_rate_limiting(self):
        """The rate_limit decorator should enforce minimum intervals."""
        import time

        call_times = []

        @rate_limit(calls_per_second=100.0)  # high rate for fast test
        async def limited_fn():
            call_times.append(time.monotonic())
            return True

        await limited_fn()
        await limited_fn()

        assert len(call_times) == 2
        # The second call should be after the first
        assert call_times[1] >= call_times[0]


class TestProxyRotation:
    """Tests for proxy rotation."""

    def test_proxy_rotation(self):
        """With BrightData credentials, each call should produce a proxy URL."""

        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"

            async def scrape(self, url):
                return {}

            def parse(self, raw_html):
                return []

        scraper = TestScraper(
            brightdata_username="user123",
            brightdata_password="pass456",
        )

        proxies = set()
        for _ in range(10):
            proxy = scraper._get_proxy()
            assert proxy is not None
            assert "user123-session-" in proxy
            assert "pass456" in proxy
            assert "brd.superproxy.io" in proxy
            proxies.add(proxy)

        # Session IDs should be randomized so at least some are different
        assert len(proxies) > 1

    def test_no_proxy_without_credentials(self):
        """Without credentials, proxy should be None."""

        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"

            async def scrape(self, url):
                return {}

            def parse(self, raw_html):
                return []

        scraper = TestScraper()
        assert scraper._get_proxy() is None

    def test_explicit_proxy_url(self):
        """An explicit proxy_url should be used directly."""

        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"

            async def scrape(self, url):
                return {}

            def parse(self, raw_html):
                return []

        scraper = TestScraper(proxy_url="http://my-proxy:8080")
        assert scraper._get_proxy() == "http://my-proxy:8080"
