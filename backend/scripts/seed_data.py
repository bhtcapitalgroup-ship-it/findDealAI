#!/usr/bin/env python3
"""Seed the RealDeal AI database with realistic demo data.

Usage:
    python scripts/seed_data.py          # run from backend/
    make seed                             # run from project root via Makefile

Requires a running PostgreSQL instance matching DATABASE_URL in .env or config.
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running as a standalone script
# ---------------------------------------------------------------------------
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine
from app.models.alert import Alert
from app.models.base import Base
from app.models.market import MarketData
from app.models.property import Property, PropertyType
from app.models.saved_deal import SavedDeal
from app.models.user import PlanTier, User

# ---------------------------------------------------------------------------
# Deterministic seed for reproducibility
# ---------------------------------------------------------------------------
random.seed(42)

# ═══════════════════════════════════════════════════════════════════════════
# Helper data
# ═══════════════════════════════════════════════════════════════════════════

CITIES: list[dict] = [
    {"city": "Austin",        "state": "TX", "zip": "78745", "metro": "Austin-Round Rock-Georgetown"},
    {"city": "Jacksonville",  "state": "FL", "zip": "32210", "metro": "Jacksonville"},
    {"city": "Memphis",       "state": "TN", "zip": "38118", "metro": "Memphis"},
    {"city": "Cleveland",     "state": "OH", "zip": "44102", "metro": "Cleveland-Elyria"},
    {"city": "Indianapolis",  "state": "IN", "zip": "46201", "metro": "Indianapolis-Carmel-Anderson"},
    {"city": "Kansas City",   "state": "MO", "zip": "64130", "metro": "Kansas City"},
    {"city": "Birmingham",    "state": "AL", "zip": "35211", "metro": "Birmingham-Hoover"},
    {"city": "Columbus",      "state": "OH", "zip": "43207", "metro": "Columbus"},
    {"city": "San Antonio",   "state": "TX", "zip": "78223", "metro": "San Antonio-New Braunfels"},
    {"city": "Charlotte",     "state": "NC", "zip": "28205", "metro": "Charlotte-Concord-Gastonia"},
]

# Real street name patterns per city
STREETS: dict[str, list[str]] = {
    "Austin":       ["S Congress Ave", "E Riverside Dr", "Manchaca Rd", "Oltorf St", "Stassney Ln", "William Cannon Dr"],
    "Jacksonville": ["Blanding Blvd", "Cassat Ave", "Normandy Blvd", "Lane Ave S", "Timuquana Rd", "Wesconnett Blvd"],
    "Memphis":      ["Lamar Ave", "Winchester Rd", "Getwell Rd", "Shelby Dr", "Raleigh-Millington Rd", "Elvis Presley Blvd"],
    "Cleveland":    ["Lorain Ave", "Clark Ave", "Denison Ave", "Detroit Ave", "Madison Ave", "Fulton Rd"],
    "Indianapolis": ["E Washington St", "N Meridian St", "Massachusetts Ave", "E 10th St", "N College Ave", "S East St"],
    "Kansas City":  ["Prospect Ave", "Troost Ave", "E 63rd St", "Paseo Blvd", "E 31st St", "Swope Pkwy"],
    "Birmingham":   ["Bessemer Rd", "Center St SW", "Arkadelphia Rd", "Lomb Ave SW", "Princeton Ave SW", "Jeff Davis Ave"],
    "Columbus":     ["Parsons Ave", "S High St", "E Livingston Ave", "Lockbourne Rd", "E Main St", "Refugee Rd"],
    "San Antonio":  ["S Presa St", "Rigsby Ave", "W Southcross Blvd", "S New Braunfels Ave", "Roosevelt Ave", "Pleasanton Rd"],
    "Charlotte":    ["Central Ave", "N Davidson St", "The Plaza", "Shamrock Dr", "Eastway Dr", "Briar Creek Rd"],
}

PROPERTY_TYPES = [PropertyType.SFH, PropertyType.MULTI, PropertyType.TOWNHOUSE]
LISTING_SOURCES = ["zillow", "redfin", "realtor"]


def _rand_address(city: str) -> str:
    """Generate a plausible address for the given city."""
    number = random.randint(100, 9999)
    street = random.choice(STREETS[city])
    return f"{number} {street}"


def _password_hash() -> str:
    """Return a bcrypt-style placeholder hash (demo only, NOT a real hash)."""
    # passlib bcrypt hash of 'demo1234'
    return "$2b$12$LJ3m4ys3Lk0tB8Wv3q3XxO8J2dFbYqR1wN7yZcEaC9K3mH5vG6tOu"


# ═══════════════════════════════════════════════════════════════════════════
# Builder functions
# ═══════════════════════════════════════════════════════════════════════════

def build_users() -> list[User]:
    """Create 3 demo users across the plan tiers."""
    return [
        User(
            id=uuid.UUID("aaaaaaaa-0001-4000-8000-000000000001"),
            email="demo@realdeal.ai",
            hashed_password=_password_hash(),
            full_name="Alex Morgan",
            company_name=None,
            plan_tier=PlanTier.STARTER,
            is_active=True,
            settings={"onboarded": True, "theme": "light"},
        ),
        User(
            id=uuid.UUID("aaaaaaaa-0002-4000-8000-000000000002"),
            email="pro@realdeal.ai",
            hashed_password=_password_hash(),
            full_name="Jordan Rivera",
            company_name="Riverstone Capital LLC",
            plan_tier=PlanTier.GROWTH,
            is_active=True,
            settings={"onboarded": True, "theme": "dark", "default_market": "Austin"},
        ),
        User(
            id=uuid.UUID("aaaaaaaa-0003-4000-8000-000000000003"),
            email="proplus@realdeal.ai",
            hashed_password=_password_hash(),
            full_name="Taylor Chen",
            company_name="Chen Property Group",
            plan_tier=PlanTier.PRO,
            is_active=True,
            settings={"onboarded": True, "theme": "dark", "default_market": "Charlotte"},
        ),
    ]


def build_properties(users: list[User]) -> list[Property]:
    """Create 50 realistic investment properties across the 10 target cities."""
    props: list[Property] = []

    # Distribute 5 properties per city
    for idx in range(50):
        city_info = CITIES[idx % 10]
        city = city_info["city"]
        state = city_info["state"]
        base_zip = city_info["zip"]

        # Vary the last digit of the zip for diversity
        zip_code = base_zip[:4] + str(random.randint(0, 9))

        ptype = random.choice(PROPERTY_TYPES)
        total_units = 1 if ptype == PropertyType.SFH else (random.choice([2, 3, 4]) if ptype == PropertyType.MULTI else 1)

        bedrooms = random.randint(2, 5)
        bathrooms = random.choice([1, 1.5, 2, 2.5, 3])
        sqft = random.randint(800, 3000)
        year_built = random.randint(1950, 2020)

        # Price depends on city tier
        city_tier = {
            "Austin": 1.4, "Charlotte": 1.2, "Columbus": 1.0, "San Antonio": 1.1,
            "Jacksonville": 1.0, "Indianapolis": 0.85, "Kansas City": 0.9,
            "Memphis": 0.75, "Cleveland": 0.7, "Birmingham": 0.7,
        }
        multiplier = city_tier.get(city, 1.0)
        base_price = random.randint(80000, 280000)
        purchase_price = int(base_price * multiplier)
        # Clamp to spec range
        purchase_price = max(80000, min(400000, purchase_price))

        # Current value is generally above purchase price
        appreciation = random.uniform(1.0, 1.4)
        current_value = int(purchase_price * appreciation)

        # Monthly costs
        mortgage_monthly = round(purchase_price * 0.006, 2)  # ~0.6% of price monthly
        insurance_monthly = round(random.uniform(80, 200), 2)
        tax_annual = round(purchase_price * random.uniform(0.008, 0.025), 2)

        address = _rand_address(city)

        prop = Property(
            id=uuid.UUID(f"bbbbbbbb-{idx + 1:04d}-4000-8000-000000000001"),
            landlord_id=random.choice(users).id,
            name=f"{address.split(' ', 1)[1][:30]} Investment",
            address_line1=address,
            city=city,
            state=state,
            zip_code=zip_code,
            property_type=ptype,
            total_units=total_units,
            purchase_price=Decimal(str(purchase_price)),
            current_value=Decimal(str(current_value)),
            mortgage_payment=Decimal(str(mortgage_monthly)),
            insurance_cost=Decimal(str(insurance_monthly)),
            tax_annual=Decimal(str(tax_annual)),
            is_active=True,
        )
        props.append(prop)

    return props


def build_market_data() -> list[MarketData]:
    """Create market-level snapshots for each of the 10 cities."""
    today = date.today()
    entries: list[MarketData] = []

    market_stats: dict[str, dict] = {
        "Austin":       {"median_price": 345000, "median_rent": 1850, "price_growth": 4.2, "rent_growth": 3.8, "inventory": 1240, "dom": 28, "pop": 1028225, "pop_growth": 2.8, "unemp": 3.1, "income": 78500, "crime": 32, "school": 7.2, "mig_in": 45000, "mig_out": 18000},
        "Jacksonville": {"median_price": 275000, "median_rent": 1450, "price_growth": 5.1, "rent_growth": 4.5, "inventory": 890, "dom": 35, "pop": 985843, "pop_growth": 2.1, "unemp": 3.4, "income": 58200, "crime": 45, "school": 6.1, "mig_in": 32000, "mig_out": 14000},
        "Memphis":      {"median_price": 185000, "median_rent": 1150, "price_growth": 3.4, "rent_growth": 3.9, "inventory": 1650, "dom": 42, "pop": 633104, "pop_growth": -0.3, "unemp": 4.8, "income": 42100, "crime": 72, "school": 4.8, "mig_in": 12000, "mig_out": 15000},
        "Cleveland":    {"median_price": 145000, "median_rent": 1050, "price_growth": 2.8, "rent_growth": 3.2, "inventory": 1420, "dom": 48, "pop": 372624, "pop_growth": -0.8, "unemp": 5.1, "income": 38600, "crime": 65, "school": 5.0, "mig_in": 8000, "mig_out": 12000},
        "Indianapolis": {"median_price": 225000, "median_rent": 1250, "price_growth": 4.0, "rent_growth": 3.6, "inventory": 1100, "dom": 32, "pop": 887642, "pop_growth": 1.3, "unemp": 3.6, "income": 52400, "crime": 55, "school": 5.5, "mig_in": 22000, "mig_out": 14000},
        "Kansas City":  {"median_price": 215000, "median_rent": 1200, "price_growth": 3.5, "rent_growth": 3.1, "inventory": 980, "dom": 38, "pop": 508090, "pop_growth": 0.8, "unemp": 3.8, "income": 55800, "crime": 58, "school": 5.8, "mig_in": 16000, "mig_out": 11000},
        "Birmingham":   {"median_price": 165000, "median_rent": 1100, "price_growth": 2.5, "rent_growth": 2.8, "inventory": 1380, "dom": 52, "pop": 196353, "pop_growth": -0.5, "unemp": 4.5, "income": 40300, "crime": 68, "school": 4.5, "mig_in": 9000, "mig_out": 11500},
        "Columbus":     {"median_price": 255000, "median_rent": 1350, "price_growth": 4.5, "rent_growth": 4.0, "inventory": 920, "dom": 30, "pop": 905748, "pop_growth": 1.5, "unemp": 3.3, "income": 56200, "crime": 42, "school": 6.5, "mig_in": 28000, "mig_out": 15000},
        "San Antonio":  {"median_price": 265000, "median_rent": 1400, "price_growth": 3.8, "rent_growth": 3.5, "inventory": 1520, "dom": 36, "pop": 1547253, "pop_growth": 1.9, "unemp": 3.5, "income": 54100, "crime": 48, "school": 5.9, "mig_in": 38000, "mig_out": 20000},
        "Charlotte":    {"median_price": 335000, "median_rent": 1750, "price_growth": 5.5, "rent_growth": 4.8, "inventory": 780, "dom": 25, "pop": 897720, "pop_growth": 2.5, "unemp": 3.0, "income": 68400, "crime": 38, "school": 6.8, "mig_in": 42000, "mig_out": 16000},
    }

    for city_info in CITIES:
        city = city_info["city"]
        stats = market_stats[city]
        entries.append(
            MarketData(
                zip_code=city_info["zip"],
                city=city,
                state=city_info["state"],
                metro_area=city_info["metro"],
                median_price=Decimal(str(stats["median_price"])),
                median_rent=Decimal(str(stats["median_rent"])),
                price_growth_yoy=stats["price_growth"],
                rent_growth_yoy=stats["rent_growth"],
                inventory_count=stats["inventory"],
                days_on_market_avg=stats["dom"],
                population=stats["pop"],
                population_growth=stats["pop_growth"],
                unemployment_rate=stats["unemp"],
                median_income=Decimal(str(stats["income"])),
                crime_index=stats["crime"],
                school_rating_avg=stats["school"],
                migration_inflow=stats["mig_in"],
                migration_outflow=stats["mig_out"],
                snapshot_date=today,
            )
        )

    return entries


def build_saved_deals(pro_user: User, properties: list[Property]) -> list[SavedDeal]:
    """Create 5 saved deals for the pro user."""
    # Pick 5 diverse properties
    selected = [properties[i] for i in [0, 7, 14, 23, 38]]
    deals: list[SavedDeal] = []
    notes_options = [
        "Great cash flow play. Needs minor cosmetic work — $15k rehab budget. Tenant in place.",
        "Below market rent — upside potential after lease expires in 6 months.",
        "Solid B-class neighborhood. Numbers work at asking price. Move fast.",
        "BRRRR candidate: ARV supports full cash-out refi after rehab.",
        "Multiplex with strong unit mix. Run numbers against 5-year hold.",
    ]
    for i, prop in enumerate(selected):
        deal = SavedDeal(
            user_id=pro_user.id,
            property_id=prop.id,
            notes=notes_options[i],
            custom_arv=Decimal(str(int(float(prop.purchase_price or 150000) * random.uniform(1.1, 1.4)))),
            custom_rehab=Decimal(str(random.choice([5000, 12000, 25000, 40000, 65000]))),
            custom_rent=Decimal(str(random.choice([950, 1100, 1350, 1600, 2100]))),
            is_favorite=i < 2,  # first two are favorites
        )
        deals.append(deal)

    return deals


def build_alerts(pro_user: User) -> list[Alert]:
    """Create 3 investment alerts for the pro user."""
    return [
        Alert(
            user_id=pro_user.id,
            name="High Cap Rate Deals",
            filters={
                "min_cap_rate": 8.0,
                "property_types": ["sfh", "multi"],
                "states": ["TX", "TN", "OH"],
            },
            is_active=True,
        ),
        Alert(
            user_id=pro_user.id,
            name="Strong Cash Flow",
            filters={
                "min_cash_flow": 500,
                "max_price": 250000,
                "cities": ["Memphis", "Cleveland", "Birmingham", "Indianapolis"],
            },
            is_active=True,
        ),
        Alert(
            user_id=pro_user.id,
            name="Top Investment Score",
            filters={
                "min_score": 75,
                "property_types": ["sfh", "multi", "townhouse"],
            },
            is_active=True,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Main seed coroutine
# ═══════════════════════════════════════════════════════════════════════════

async def seed() -> None:
    """Insert all seed data inside a single transaction."""
    print("=" * 60)
    print("  RealDeal AI — Database Seeder")
    print("=" * 60)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[+] Tables verified / created.")

    async with async_session_factory() as session:
        session: AsyncSession

        # Check if seed data already exists
        result = await session.execute(
            text("SELECT count(*) FROM users WHERE email = 'demo@realdeal.ai'")
        )
        if result.scalar_one() > 0:
            print("[!] Seed data already exists. Skipping.")
            print("    Run `make reset-db` first to start fresh.")
            return

        # ── Users ─────────────────────────────────────────────────
        users = build_users()
        session.add_all(users)
        await session.flush()
        print(f"[+] Inserted {len(users)} users.")
        for u in users:
            print(f"    - {u.email} ({u.plan_tier.value})")

        # ── Properties ────────────────────────────────────────────
        properties = build_properties(users)
        session.add_all(properties)
        await session.flush()
        print(f"[+] Inserted {len(properties)} properties across 10 cities.")

        # City distribution summary
        city_counts: dict[str, int] = {}
        for p in properties:
            city_counts[p.city] = city_counts.get(p.city, 0) + 1
        for city, count in sorted(city_counts.items()):
            print(f"    - {city}: {count} properties")

        # ── Market Data ───────────────────────────────────────────
        markets = build_market_data()
        session.add_all(markets)
        await session.flush()
        print(f"[+] Inserted {len(markets)} market data snapshots.")

        # ── Saved Deals ───────────────────────────────────────────
        pro_user = users[1]  # pro@realdeal.ai
        deals = build_saved_deals(pro_user, properties)
        session.add_all(deals)
        await session.flush()
        print(f"[+] Inserted {len(deals)} saved deals for {pro_user.email}.")

        # ── Alerts ────────────────────────────────────────────────
        alerts = build_alerts(pro_user)
        session.add_all(alerts)
        await session.flush()
        print(f"[+] Inserted {len(alerts)} alerts for {pro_user.email}.")

        # ── Commit ────────────────────────────────────────────────
        await session.commit()

    print()
    print("=" * 60)
    print("  Seed complete!")
    print()
    print("  Demo accounts (password: demo1234):")
    print("    Free tier : demo@realdeal.ai")
    print("    Pro tier  : pro@realdeal.ai")
    print("    Pro+ tier : proplus@realdeal.ai")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
