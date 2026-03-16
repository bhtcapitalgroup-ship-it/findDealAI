"""Tests for property management endpoints (/api/v1/properties)."""

import uuid

import pytest
from httpx import AsyncClient


class TestListProperties:
    """Tests for GET /api/v1/properties."""

    async def test_list_properties(
        self, client: AsyncClient, test_user, test_property
    ):
        """Should return the user's active properties."""
        response = await client.get(
            "/api/v1/properties",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["name"] == "Test Property"

    async def test_list_properties_pagination(
        self, client: AsyncClient, test_user, test_property, second_property
    ):
        """Pagination should respect page and page_size params."""
        response = await client.get(
            "/api/v1/properties?page=1&page_size=1",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert len(data["items"]) == 1
        assert data["total"] == 2

    async def test_list_properties_unauthenticated(self, client: AsyncClient):
        """Unauthenticated requests should be rejected."""
        response = await client.get("/api/v1/properties")
        assert response.status_code == 403


class TestGetPropertyDetail:
    """Tests for GET /api/v1/properties/{property_id}."""

    async def test_get_property_detail(
        self, client: AsyncClient, test_user, test_property
    ):
        """Should return full property detail including units list."""
        response = await client.get(
            f"/api/v1/properties/{test_property['id']}",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Property"
        assert data["city"] == "Dallas"
        assert data["state"] == "TX"
        assert "units" in data

    async def test_get_property_not_found(
        self, client: AsyncClient, test_user
    ):
        """A non-existent property ID should return 404."""
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/properties/{fake_id}",
            headers=test_user["headers"],
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCreateProperty:
    """Tests for POST /api/v1/properties."""

    async def test_create_property(self, client: AsyncClient, test_user):
        """Creating a property with valid data should return 201."""
        response = await client.post(
            "/api/v1/properties",
            headers=test_user["headers"],
            json={
                "name": "New Rental",
                "address_line1": "789 Pine Rd",
                "city": "Houston",
                "state": "TX",
                "zip_code": "77001",
                "property_type": "sfh",
                "total_units": 1,
                "purchase_price": 180000,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Rental"
        assert data["city"] == "Houston"
        assert data["landlord_id"] == str(test_user["id"])


class TestPropertyAnalysis:
    """Tests for GET /api/v1/properties/{property_id}/financials."""

    async def test_property_analysis(
        self, client: AsyncClient, test_user, test_property
    ):
        """Should return a financial summary for the property."""
        response = await client.get(
            f"/api/v1/properties/{test_property['id']}/financials",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == str(test_property["id"])
        assert "total_income" in data
        assert "total_expenses" in data
        assert "noi" in data
        assert "occupancy_rate" in data
