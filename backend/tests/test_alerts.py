"""Tests for alert CRUD endpoints (/api/v1/alerts)."""

import uuid

import pytest
from httpx import AsyncClient


class TestCreateAlert:
    """Tests for POST /api/v1/alerts."""

    async def test_create_alert(self, client: AsyncClient, test_user):
        """Creating an alert with valid filters should return 201."""
        response = await client.post(
            "/api/v1/alerts",
            headers=test_user["headers"],
            json={
                "name": "Dallas High Cap",
                "filters": {
                    "min_cap_rate": 8.0,
                    "max_price": 300000,
                    "states": ["TX"],
                    "cities": ["Dallas"],
                },
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dallas High Cap"
        assert data["filters"]["min_cap_rate"] == 8.0
        assert data["filters"]["max_price"] == 300000
        assert data["is_active"] is True


class TestListAlerts:
    """Tests for GET /api/v1/alerts."""

    async def test_list_alerts(self, client: AsyncClient, test_user):
        """Should list all alerts for the current user."""
        # Create two alerts
        for name in ["Alert A", "Alert B"]:
            await client.post(
                "/api/v1/alerts",
                headers=test_user["headers"],
                json={
                    "name": name,
                    "filters": {"min_cap_rate": 6.0},
                },
            )

        response = await client.get(
            "/api/v1/alerts",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_list_alerts_empty(self, client: AsyncClient, test_user):
        """A user with no alerts should see an empty list."""
        response = await client.get(
            "/api/v1/alerts",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        assert response.json() == []


class TestUpdateAlert:
    """Tests for PUT /api/v1/alerts/{alert_id}."""

    async def test_update_alert(self, client: AsyncClient, test_user):
        """Updating an alert should persist name and filter changes."""
        create_resp = await client.post(
            "/api/v1/alerts",
            headers=test_user["headers"],
            json={
                "name": "Original Name",
                "filters": {"min_cap_rate": 6.0},
            },
        )
        alert_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=test_user["headers"],
            json={
                "name": "Updated Name",
                "filters": {"min_cap_rate": 10.0, "max_price": 200000},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["filters"]["min_cap_rate"] == 10.0
        assert data["filters"]["max_price"] == 200000


class TestDeleteAlert:
    """Tests for DELETE /api/v1/alerts/{alert_id}."""

    async def test_delete_alert(self, client: AsyncClient, test_user):
        """Deleting an alert should return 204 and remove it."""
        create_resp = await client.post(
            "/api/v1/alerts",
            headers=test_user["headers"],
            json={
                "name": "To Delete",
                "filters": {"min_cap_rate": 5.0},
            },
        )
        alert_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/alerts/{alert_id}",
            headers=test_user["headers"],
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            f"/api/v1/alerts/{alert_id}",
            headers=test_user["headers"],
        )
        assert get_resp.status_code == 404

    async def test_delete_alert_not_found(self, client: AsyncClient, test_user):
        """Deleting a non-existent alert should return 404."""
        response = await client.delete(
            f"/api/v1/alerts/{uuid.uuid4()}",
            headers=test_user["headers"],
        )
        assert response.status_code == 404


class TestToggleAlertActive:
    """Tests for toggling alert active status."""

    async def test_toggle_alert_active(self, client: AsyncClient, test_user):
        """Setting is_active=False should deactivate the alert."""
        create_resp = await client.post(
            "/api/v1/alerts",
            headers=test_user["headers"],
            json={
                "name": "Toggle Test",
                "filters": {"min_cap_rate": 7.0},
                "is_active": True,
            },
        )
        alert_id = create_resp.json()["id"]

        # Deactivate
        response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=test_user["headers"],
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Reactivate
        response = await client.put(
            f"/api/v1/alerts/{alert_id}",
            headers=test_user["headers"],
            json={"is_active": True},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True


class TestAlertMatchingLogic:
    """Test that alert filter criteria can match against property data."""

    def test_alert_matching_min_cap_rate(self):
        """An alert with min_cap_rate=8 should match cap_rate=10 but not 5."""
        filters = {"min_cap_rate": 8.0, "max_price": 500000}

        # Simulate matching logic
        high_cap_property = {"cap_rate": 10.0, "price": 200000}
        low_cap_property = {"cap_rate": 5.0, "price": 200000}

        def matches(alert_filters: dict, prop: dict) -> bool:
            if "min_cap_rate" in alert_filters:
                if prop.get("cap_rate", 0) < alert_filters["min_cap_rate"]:
                    return False
            if "max_price" in alert_filters:
                if prop.get("price", 0) > alert_filters["max_price"]:
                    return False
            return True

        assert matches(filters, high_cap_property) is True
        assert matches(filters, low_cap_property) is False

    def test_alert_matching_price_filter(self):
        """An alert with max_price=300k should reject a $400k property."""
        filters = {"max_price": 300000}

        cheap = {"price": 250000, "cap_rate": 7.0}
        expensive = {"price": 400000, "cap_rate": 9.0}

        def matches(alert_filters: dict, prop: dict) -> bool:
            if "max_price" in alert_filters:
                if prop.get("price", 0) > alert_filters["max_price"]:
                    return False
            return True

        assert matches(filters, cheap) is True
        assert matches(filters, expensive) is False
