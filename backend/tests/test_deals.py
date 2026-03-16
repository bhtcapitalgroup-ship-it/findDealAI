"""Tests for saved deal endpoints (/api/v1/deals)."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import TestSessionLocal
from app.models.saved_deal import SavedDeal


class TestSaveDeal:
    """Tests for POST /api/v1/deals/save."""

    async def test_save_deal(
        self, client: AsyncClient, test_user, test_property
    ):
        """Saving a deal should return 201 with deal details."""
        response = await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={
                "property_id": str(test_property["id"]),
                "notes": "Great potential investment",
                "custom_arv": 300000.0,
                "custom_rehab": 25000.0,
                "custom_rent": 2000.0,
                "is_favorite": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["property_id"] == str(test_property["id"])
        assert data["notes"] == "Great potential investment"
        assert data["is_favorite"] is True
        assert data["custom_arv"] == 300000.0

    async def test_save_deal_duplicate(
        self, client: AsyncClient, test_user, test_property
    ):
        """Saving the same property twice should return 409."""
        payload = {
            "property_id": str(test_property["id"]),
            "notes": "First save",
        }
        await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json=payload,
        )
        response = await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json=payload,
        )
        assert response.status_code == 409

    async def test_save_deal_nonexistent_property(
        self, client: AsyncClient, test_user
    ):
        """Saving a deal for a non-existent property should return 404."""
        response = await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={"property_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404


class TestListSavedDeals:
    """Tests for GET /api/v1/deals/saved."""

    async def test_list_saved_deals(
        self, client: AsyncClient, test_user, test_property
    ):
        """Should return a list of saved deals for the current user."""
        # Save a deal first
        await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={"property_id": str(test_property["id"])},
        )

        response = await client.get(
            "/api/v1/deals/saved",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_saved_deals_empty(
        self, client: AsyncClient, test_user
    ):
        """A user with no saved deals should see an empty list."""
        response = await client.get(
            "/api/v1/deals/saved",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        assert response.json() == []


class TestUpdateDeal:
    """Tests for PUT /api/v1/deals/{deal_id}."""

    async def test_update_deal_notes(
        self, client: AsyncClient, test_user, test_property
    ):
        """Updating deal notes should persist the change."""
        save_resp = await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={"property_id": str(test_property["id"]), "notes": "Initial"},
        )
        deal_id = save_resp.json()["id"]

        response = await client.put(
            f"/api/v1/deals/{deal_id}",
            headers=test_user["headers"],
            json={"notes": "Updated notes with more detail"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes with more detail"


class TestDeleteDeal:
    """Tests for DELETE /api/v1/deals/{deal_id}."""

    async def test_delete_deal(
        self, client: AsyncClient, test_user, test_property
    ):
        """Deleting a saved deal should return 204."""
        save_resp = await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={"property_id": str(test_property["id"])},
        )
        deal_id = save_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/deals/{deal_id}",
            headers=test_user["headers"],
        )
        assert response.status_code == 204

        # Verify it's gone
        list_resp = await client.get(
            "/api/v1/deals/saved",
            headers=test_user["headers"],
        )
        ids = [d["id"] for d in list_resp.json()]
        assert deal_id not in ids

    async def test_delete_deal_not_found(
        self, client: AsyncClient, test_user
    ):
        """Deleting a non-existent deal should return 404."""
        response = await client.delete(
            f"/api/v1/deals/{uuid.uuid4()}",
            headers=test_user["headers"],
        )
        assert response.status_code == 404


class TestCompareDeals:
    """Tests for POST /api/v1/deals/compare."""

    async def test_compare_deals_too_few(
        self, client: AsyncClient, test_user, test_property
    ):
        """Comparing fewer than 2 properties should return 400."""
        response = await client.post(
            "/api/v1/deals/compare",
            headers=test_user["headers"],
            json=[str(test_property["id"])],
        )
        assert response.status_code == 400


class TestExportCSV:
    """Tests for GET /api/v1/deals/export."""

    async def test_export_csv(
        self, client: AsyncClient, test_user, test_property
    ):
        """Exporting deals should return a CSV file."""
        # Save a deal
        await client.post(
            "/api/v1/deals/save",
            headers=test_user["headers"],
            json={"property_id": str(test_property["id"])},
        )

        response = await client.get(
            "/api/v1/deals/export",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "address" in content or "city" in content
