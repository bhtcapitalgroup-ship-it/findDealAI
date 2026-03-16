"""Tests for authentication endpoints (/api/v1/auth)."""

import pytest
from httpx import AsyncClient


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient):
        """A new user should be created and receive a JWT token."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass99!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Registering with an existing email should return 409 Conflict."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["email"],
                "password": "AnotherPass1!",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        """An invalid email format should be rejected with 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass99!",
                "full_name": "Bad Email User",
            },
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        """A password shorter than 8 characters should be rejected."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "abc",
                "full_name": "Short Pass",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(self, client: AsyncClient, test_user):
        """Logging in with correct credentials should return a JWT."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user["email"]

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """An incorrect password should return 401 Unauthorized."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword!",
            },
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """A non-existent email should return 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "DoesNotMatter1!",
            },
        )
        assert response.status_code == 401


class TestGetMe:
    """Tests for GET /api/v1/auth/me."""

    async def test_get_me_authenticated(self, client: AsyncClient, test_user):
        """An authenticated user should see their own profile."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=test_user["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["full_name"] == test_user["full_name"]

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """A request without a token should return 403."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403


class TestUpdateProfile:
    """Tests for PUT /api/v1/auth/me."""

    async def test_update_profile(self, client: AsyncClient, test_user):
        """Updating profile fields should persist the changes."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=test_user["headers"],
            json={"full_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"

    async def test_update_profile_duplicate_email(
        self, client: AsyncClient, test_user, test_user_pro
    ):
        """Changing email to one already in use should return 409."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=test_user["headers"],
            json={"email": test_user_pro["email"]},
        )
        assert response.status_code == 409
