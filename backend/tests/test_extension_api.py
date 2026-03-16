"""Tests for the extension API endpoint."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAnalyzeEndpoint:
    @patch("app.api.v1.extension.get_rent_estimate", new_callable=AsyncMock)
    @patch("app.api.v1.extension.get_rent_comps", new_callable=AsyncMock)
    @patch("app.api.v1.extension.get_neighborhood_data", new_callable=AsyncMock)
    @patch("app.api.v1.extension.generate_verdict", new_callable=AsyncMock)
    @patch("app.api.v1.extension.cache_get", new_callable=AsyncMock)
    @patch("app.api.v1.extension.cache_set", new_callable=AsyncMock)
    def test_analyze_basic(
        self, mock_cache_set, mock_cache_get, mock_verdict,
        mock_hood, mock_comps, mock_rent, client,
    ):
        mock_cache_get.return_value = None
        mock_rent.return_value = {"rent": 2150, "rentRangeLow": 1900, "rentRangeHigh": 2400}
        mock_comps.return_value = []
        mock_hood.return_value = {
            "crime_rate": 30,
            "crime_label": "Low",
            "school_rating": 7,
            "pop_growth": 1.5,
            "rent_growth": 3.2,
            "median_income": 65000,
        }
        mock_verdict.return_value = {
            "verdict": "Good Deal",
            "confidence": "High",
            "summary": "Strong investment opportunity.",
            "risks": ["Market volatility"],
            "opportunities": ["Growing area"],
        }

        resp = client.post("/api/v1/extension/analyze", json={
            "address": "123 Main St, Austin TX 78701",
            "price": 285000,
            "beds": 3,
            "baths": 2,
            "sqft": 1450,
            "year_built": 1998,
            "zip_code": "78701",
        })

        assert resp.status_code == 200
        data = resp.json()

        # Check response structure
        assert "rent_estimate" in data
        assert "metrics" in data
        assert "brrrr" in data
        assert "flip" in data
        assert "verdict" in data
        assert "investment_score" in data

        # Check metrics are computed
        assert data["metrics"]["cap_rate"] > 0
        assert data["metrics"]["monthly_mortgage"] > 0

        # Check verdict
        assert data["verdict"]["verdict"] == "Good Deal"

        # Check investment score
        assert 0 <= data["investment_score"] <= 100

    def test_missing_price_returns_400(self, client):
        resp = client.post("/api/v1/extension/analyze", json={
            "address": "123 Main St",
            "price": 0,
        })
        assert resp.status_code == 400

    def test_null_price_returns_400(self, client):
        resp = client.post("/api/v1/extension/analyze", json={
            "address": "123 Main St",
        })
        assert resp.status_code == 400

    @patch("app.api.v1.extension.cache_get", new_callable=AsyncMock)
    def test_cache_hit_returns_cached(self, mock_cache_get, client):
        cached_data = {
            "property": {"address": "123 Main St", "price": 285000},
            "rent_estimate": {"amount": 2150, "confidence": 85, "source": "rentcast", "comps": []},
            "metrics": {
                "cap_rate": 7.5, "noi": 18000, "monthly_mortgage": 1420,
                "monthly_cash_flow": 350, "annual_cash_flow": 4200,
                "cash_on_cash": 5.3, "total_cash_invested": 79800, "dscr": 1.2,
            },
            "brrrr": {
                "arv": 320000, "rehab_low": 5000, "rehab_high": 15000,
                "refi_amount": 240000, "cash_left_in_deal": 10000,
                "rating": "Good", "score": 65,
            },
            "flip": {
                "arv": 320000, "rehab_low": 5000, "rehab_high": 15000,
                "holding_costs": 12000, "selling_costs": 25600,
                "profit": 22400, "roi": 7.5, "rating": "Marginal",
            },
            "neighborhood": None,
            "verdict": {
                "verdict": "Average", "confidence": "Medium",
                "summary": "Decent deal.", "risks": [], "opportunities": [],
            },
            "investment_score": 58,
        }
        mock_cache_get.return_value = cached_data

        resp = client.post("/api/v1/extension/analyze", json={
            "address": "123 Main St",
            "price": 285000,
            "zpid": "12345",
        })

        assert resp.status_code == 200
        assert resp.json()["investment_score"] == 58
