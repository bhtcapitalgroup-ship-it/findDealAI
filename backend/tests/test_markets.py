"""Tests for market data endpoints (/api/v1/markets)."""

import pytest
from httpx import AsyncClient


class TestGetHeatmap:
    """Tests for GET /api/v1/markets/heatmap."""

    async def test_get_heatmap(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """Should return scored zip code entries."""
        response = await client.get(
            "/api/v1/markets/heatmap",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert len(data["entries"]) >= 1
        # Each entry should have a score
        for entry in data["entries"]:
            assert "score" in entry
            assert 0 <= entry["score"] <= 100
            assert "zip_code" in entry

    async def test_heatmap_filter_by_state(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """Filtering by state should only return matching entries."""
        response = await client.get(
            "/api/v1/markets/heatmap?state=TX",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["state"] == "TX"


class TestGetMarketByZip:
    """Tests for GET /api/v1/markets/{zip_code}."""

    async def test_get_market_by_zip(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """Should return full market data for a known zip code."""
        response = await client.get(
            "/api/v1/markets/75201",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["zip_code"] == "75201"
        assert data["city"] == "Dallas"
        assert data["state"] == "TX"
        assert data["median_price"] == 350000.0

    async def test_get_market_not_found(
        self, client: AsyncClient, test_user
    ):
        """A non-existent zip should return 404."""
        response = await client.get(
            "/api/v1/markets/00000",
            headers=test_user["headers"],
        )
        assert response.status_code == 404


class TestTrendingMarkets:
    """Tests for GET /api/v1/markets/trending."""

    async def test_trending_markets(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """Should return markets sorted by the requested metric."""
        response = await client.get(
            "/api/v1/markets/trending?metric=price_growth_yoy&limit=10",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Verify sorted descending
        for i in range(len(data) - 1):
            assert (data[i].get("price_growth_yoy") or 0) >= (
                data[i + 1].get("price_growth_yoy") or 0
            )

    async def test_trending_invalid_metric(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """An invalid metric should return 400."""
        response = await client.get(
            "/api/v1/markets/trending?metric=invalid_field",
            headers=test_user["headers"],
        )
        assert response.status_code == 400


class TestCompareMarkets:
    """Tests for GET /api/v1/markets/compare."""

    async def test_compare_markets(
        self, client: AsyncClient, test_user, test_market_data
    ):
        """Should return market data for each requested zip code."""
        response = await client.get(
            "/api/v1/markets/compare?zip_codes=75201,78701",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        zip_codes = {m["zip_code"] for m in data}
        assert "75201" in zip_codes
        assert "78701" in zip_codes

    async def test_compare_markets_too_few(
        self, client: AsyncClient, test_user
    ):
        """Comparing fewer than 2 zips should return 400."""
        response = await client.get(
            "/api/v1/markets/compare?zip_codes=75201",
            headers=test_user["headers"],
        )
        assert response.status_code == 400
