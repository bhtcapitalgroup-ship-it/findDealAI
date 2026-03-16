"""Shared pytest fixtures for the RealDeal AI test suite."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, StaticPool, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.alert import Alert
from app.models.base import Base
from app.models.market import MarketData
from app.models.property import Property, PropertyType
from app.models.saved_deal import SavedDeal
from app.models.user import PlanTier, User

# ---------------------------------------------------------------------------
# SQLite compatibility: remap PostgreSQL-only types
# ---------------------------------------------------------------------------
# JSONB is not supported by SQLite; remap it to plain JSON for testing.
from sqlalchemy.dialects import sqlite as sqlite_dialect

JSONB._default_dialect = sqlite_dialect.dialect()  # type: ignore[attr-defined]

# Register a compile rule so JSONB renders as JSON on SQLite
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# PostgreSQL UUID type needs to render as CHAR(32) on SQLite
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


# ---------------------------------------------------------------------------
# Test database (SQLite async, in-memory)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override that yields a test database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override the FastAPI dependency
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Async HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client connected to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test user
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_user() -> dict[str, Any]:
    """Create a test user and return user data with auth token."""
    user_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        user = User(
            id=user_id,
            email="testuser@example.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Test User",
            plan_tier=PlanTier.STARTER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(subject=str(user_id))
    return {
        "id": user_id,
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "TestPass123!",
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest_asyncio.fixture
async def test_user_pro() -> dict[str, Any]:
    """Create a PRO-tier test user."""
    user_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        user = User(
            id=user_id,
            email="prouser@example.com",
            hashed_password=hash_password("ProPass123!"),
            full_name="Pro User",
            plan_tier=PlanTier.PRO,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(subject=str(user_id))
    return {
        "id": user_id,
        "email": "prouser@example.com",
        "full_name": "Pro User",
        "password": "ProPass123!",
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


# ---------------------------------------------------------------------------
# Test property
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_property(test_user: dict[str, Any]) -> dict[str, Any]:
    """Create a test property owned by test_user."""
    prop_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        prop = Property(
            id=prop_id,
            landlord_id=test_user["id"],
            name="Test Property",
            address_line1="123 Main St",
            address_line2="Apt 1",
            city="Dallas",
            state="TX",
            zip_code="75201",
            property_type=PropertyType.SFH,
            total_units=1,
            purchase_price=250000.00,
            current_value=280000.00,
            mortgage_payment=1200.00,
            insurance_cost=150.00,
            tax_annual=4500.00,
            is_active=True,
        )
        session.add(prop)
        await session.commit()

    return {
        "id": prop_id,
        "landlord_id": test_user["id"],
        "name": "Test Property",
        "address_line1": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75201",
    }


@pytest_asyncio.fixture
async def second_property(test_user: dict[str, Any]) -> dict[str, Any]:
    """Create a second test property owned by test_user."""
    prop_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        prop = Property(
            id=prop_id,
            landlord_id=test_user["id"],
            name="Second Property",
            address_line1="456 Oak Ave",
            city="Austin",
            state="TX",
            zip_code="78701",
            property_type=PropertyType.MULTI,
            total_units=4,
            purchase_price=500000.00,
            current_value=550000.00,
            mortgage_payment=2400.00,
            insurance_cost=300.00,
            tax_annual=9000.00,
            is_active=True,
        )
        session.add(prop)
        await session.commit()

    return {
        "id": prop_id,
        "landlord_id": test_user["id"],
        "name": "Second Property",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
    }


# ---------------------------------------------------------------------------
# Test market data
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_market_data() -> list[dict[str, Any]]:
    """Insert sample market data for two zip codes."""
    markets = []
    rows = [
        {
            "zip_code": "75201",
            "city": "Dallas",
            "state": "TX",
            "metro_area": "Dallas-Fort Worth",
            "median_price": 350000.0,
            "median_rent": 1800.0,
            "price_growth_yoy": 5.2,
            "rent_growth_yoy": 3.8,
            "inventory_count": 450,
            "days_on_market_avg": 28.0,
            "population": 1340000,
            "population_growth": 1.8,
            "unemployment_rate": 3.5,
            "median_income": 65000.0,
            "crime_index": 42.0,
            "school_rating_avg": 7.0,
            "migration_inflow": 15000,
            "migration_outflow": 8000,
            "snapshot_date": date(2026, 3, 1),
        },
        {
            "zip_code": "78701",
            "city": "Austin",
            "state": "TX",
            "metro_area": "Austin-Round Rock",
            "median_price": 420000.0,
            "median_rent": 2100.0,
            "price_growth_yoy": 7.1,
            "rent_growth_yoy": 4.5,
            "inventory_count": 320,
            "days_on_market_avg": 22.0,
            "population": 1020000,
            "population_growth": 2.5,
            "unemployment_rate": 2.9,
            "median_income": 72000.0,
            "crime_index": 35.0,
            "school_rating_avg": 8.0,
            "migration_inflow": 20000,
            "migration_outflow": 7000,
            "snapshot_date": date(2026, 3, 1),
        },
    ]

    async with TestSessionLocal() as session:
        for row in rows:
            md = MarketData(id=uuid.uuid4(), **row)
            session.add(md)
            markets.append({"id": md.id, **row})
        await session.commit()

    return markets


# ---------------------------------------------------------------------------
# Mock Redis
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Provide a mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.ttl = AsyncMock(return_value=3600)
    redis_mock.exists = AsyncMock(return_value=False)
    redis_mock.pipeline = MagicMock(return_value=redis_mock)
    redis_mock.execute = AsyncMock(return_value=[1, True])
    return redis_mock


# ---------------------------------------------------------------------------
# Mock Celery
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_celery():
    """Provide a mock Celery app in eager mode."""
    celery_mock = MagicMock()
    celery_mock.conf.task_always_eager = True
    celery_mock.conf.task_eager_propagates = True

    task_mock = MagicMock()
    task_mock.delay = MagicMock(return_value=MagicMock(id="mock-task-id"))
    task_mock.apply_async = MagicMock(return_value=MagicMock(id="mock-task-id"))

    celery_mock.send_task = MagicMock(return_value=MagicMock(id="mock-task-id"))
    return celery_mock
