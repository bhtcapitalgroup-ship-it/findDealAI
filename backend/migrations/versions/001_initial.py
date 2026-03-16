"""001 — Initial schema: users, properties, saved_deals, alerts, market_data.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Enable extensions
    # -------------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # -------------------------------------------------------------------------
    # ENUM types
    # -------------------------------------------------------------------------
    property_type_enum = postgresql.ENUM(
        "single_family",
        "multi_family",
        "condo",
        "townhouse",
        "land",
        "commercial",
        "mixed_use",
        "mobile_home",
        "other",
        name="property_type",
        create_type=True,
    )
    property_type_enum.create(op.get_bind(), checkfirst=True)

    listing_status_enum = postgresql.ENUM(
        "active",
        "pending",
        "sold",
        "off_market",
        "foreclosure",
        "auction",
        "withdrawn",
        name="listing_status",
        create_type=True,
    )
    listing_status_enum.create(op.get_bind(), checkfirst=True)

    listing_source_enum = postgresql.ENUM(
        "zillow",
        "redfin",
        "realtor",
        "mls",
        "public_records",
        "auction",
        "fsbo",
        "other",
        name="listing_source",
        create_type=True,
    )
    listing_source_enum.create(op.get_bind(), checkfirst=True)

    alert_channel_enum = postgresql.ENUM(
        "email",
        "sms",
        "push",
        "webhook",
        name="alert_channel",
        create_type=True,
    )
    alert_channel_enum.create(op.get_bind(), checkfirst=True)

    subscription_tier_enum = postgresql.ENUM(
        "free",
        "starter",
        "pro",
        "enterprise",
        name="subscription_tier",
        create_type=True,
    )
    subscription_tier_enum.create(op.get_bind(), checkfirst=True)

    # -------------------------------------------------------------------------
    # Table: users
    # -------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "subscription_tier",
            subscription_tier_enum,
            nullable=False,
            server_default="free",
        ),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_subscription_tier", "users", ["subscription_tier"])
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)

    # -------------------------------------------------------------------------
    # Table: properties
    # -------------------------------------------------------------------------
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),

        # Address
        sa.Column("address_line1", sa.String(500), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("county", sa.String(255), nullable=True),

        # Geospatial (PostGIS)
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column(
            "location",
            sa.Column("location", sa.Text(), nullable=True),  # Will be cast — see raw SQL below
        ),

        # Listing info
        sa.Column("property_type", property_type_enum, nullable=False),
        sa.Column("listing_status", listing_status_enum, nullable=False, server_default="active"),
        sa.Column("listing_source", listing_source_enum, nullable=False),
        sa.Column("mls_number", sa.String(50), nullable=True),
        sa.Column("listing_url", sa.Text(), nullable=True),

        # Financials
        sa.Column("list_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("estimated_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("last_sold_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("last_sold_date", sa.Date(), nullable=True),
        sa.Column("estimated_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column("hoa_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("tax_annual", sa.Numeric(10, 2), nullable=True),
        sa.Column("insurance_annual", sa.Numeric(10, 2), nullable=True),

        # Characteristics
        sa.Column("bedrooms", sa.SmallInteger(), nullable=True),
        sa.Column("bathrooms", sa.Numeric(4, 1), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("lot_sqft", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.SmallInteger(), nullable=True),
        sa.Column("stories", sa.SmallInteger(), nullable=True),
        sa.Column("units", sa.SmallInteger(), nullable=True, server_default="1"),
        sa.Column("parking_spaces", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photos", postgresql.JSONB(), nullable=True, server_default="[]"),

        # AI-computed scores
        sa.Column("investment_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("cap_rate", sa.Numeric(6, 3), nullable=True),
        sa.Column("cash_on_cash", sa.Numeric(6, 3), nullable=True),
        sa.Column("gross_yield", sa.Numeric(6, 3), nullable=True),
        sa.Column("price_per_sqft", sa.Numeric(10, 2), nullable=True),
        sa.Column("rent_to_price_ratio", sa.Numeric(8, 5), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_analysis", postgresql.JSONB(), nullable=True),

        # Metadata
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("data_quality_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )

    # Drop the nested sa.Column for location and recreate as proper PostGIS column
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS location")
    op.execute(
        "ALTER TABLE properties ADD COLUMN location geography(Point, 4326)"
    )

    # Indexes on properties
    op.create_index("ix_properties_zip_code", "properties", ["zip_code"])
    op.create_index("ix_properties_state_city", "properties", ["state", "city"])
    op.create_index("ix_properties_investment_score", "properties", ["investment_score"], postgresql_using="btree")
    op.create_index("ix_properties_cap_rate", "properties", ["cap_rate"], postgresql_using="btree")
    op.create_index("ix_properties_listing_source", "properties", ["listing_source"])
    op.create_index("ix_properties_listing_status", "properties", ["listing_status"])
    op.create_index("ix_properties_property_type", "properties", ["property_type"])
    op.create_index("ix_properties_list_price", "properties", ["list_price"])
    op.create_index("ix_properties_mls_number", "properties", ["mls_number"], unique=True)
    op.create_index("ix_properties_listed_at", "properties", ["listed_at"])

    # GiST index for geospatial queries (e.g., "properties within 10 miles")
    op.create_index(
        "ix_properties_location_gist",
        "properties",
        ["location"],
        postgresql_using="gist",
    )

    # Trigram index for address fuzzy search / deduplication
    op.create_index(
        "ix_properties_address_trgm",
        "properties",
        ["address_line1"],
        postgresql_using="gin",
        postgresql_ops={"address_line1": "gin_trgm_ops"},
    )

    # Composite index for common filter + sort patterns
    op.create_index(
        "ix_properties_state_score",
        "properties",
        ["state", sa.text("investment_score DESC NULLS LAST")],
    )

    # -------------------------------------------------------------------------
    # Table: saved_deals
    # -------------------------------------------------------------------------
    op.create_table(
        "saved_deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("custom_label", sa.String(100), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("custom_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("offer_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_saved_deals_user_id", "saved_deals", ["user_id"])
    op.create_index("ix_saved_deals_property_id", "saved_deals", ["property_id"])
    op.create_unique_constraint("uq_saved_deals_user_property", "saved_deals", ["user_id", "property_id"])

    # -------------------------------------------------------------------------
    # Table: alerts
    # -------------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("channel", alert_channel_enum, nullable=False, server_default="email"),

        # Filter criteria (stored as structured JSON)
        sa.Column("criteria", postgresql.JSONB(), nullable=False, server_default="{}"),
        # Example criteria:
        # {
        #   "zip_codes": ["90210", "90211"],
        #   "states": ["CA"],
        #   "cities": ["Los Angeles"],
        #   "property_types": ["single_family", "multi_family"],
        #   "min_price": 100000, "max_price": 500000,
        #   "min_bedrooms": 3,
        #   "min_investment_score": 75,
        #   "min_cap_rate": 0.06,
        #   "max_days_on_market": 7
        # }

        sa.Column("frequency", sa.String(50), nullable=False, server_default="instant"),  # instant, daily, weekly
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_is_active", "alerts", ["is_active"])
    op.create_index(
        "ix_alerts_criteria_gin",
        "alerts",
        ["criteria"],
        postgresql_using="gin",
    )

    # -------------------------------------------------------------------------
    # Table: market_data
    # -------------------------------------------------------------------------
    op.create_table(
        "market_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("county", sa.String(255), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),

        # Market metrics
        sa.Column("median_list_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("median_sold_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("median_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column("median_dom", sa.Integer(), nullable=True),  # days on market
        sa.Column("inventory_count", sa.Integer(), nullable=True),
        sa.Column("new_listings_count", sa.Integer(), nullable=True),
        sa.Column("sold_count", sa.Integer(), nullable=True),
        sa.Column("price_per_sqft", sa.Numeric(10, 2), nullable=True),
        sa.Column("sale_to_list_ratio", sa.Numeric(6, 4), nullable=True),
        sa.Column("price_change_yoy", sa.Numeric(6, 3), nullable=True),  # year over year %
        sa.Column("rent_change_yoy", sa.Numeric(6, 3), nullable=True),
        sa.Column("vacancy_rate", sa.Numeric(5, 3), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("median_income", sa.Numeric(12, 2), nullable=True),
        sa.Column("unemployment_rate", sa.Numeric(5, 3), nullable=True),

        # AI insights
        sa.Column("market_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("trend_direction", sa.String(20), nullable=True),  # appreciating, stable, declining
        sa.Column("ai_insights", postgresql.JSONB(), nullable=True),

        # Metadata
        sa.Column("data_source", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_market_data_zip_code", "market_data", ["zip_code"])
    op.create_index("ix_market_data_state_city", "market_data", ["state", "city"])
    op.create_index("ix_market_data_period", "market_data", ["period_start", "period_end"])
    op.create_unique_constraint(
        "uq_market_data_zip_period",
        "market_data",
        ["zip_code", "period_start", "period_end"],
    )

    # -------------------------------------------------------------------------
    # Trigger: auto-update updated_at columns
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in ("users", "properties", "saved_deals", "alerts", "market_data"):
        op.execute(f"""
            CREATE TRIGGER trigger_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)

    # -------------------------------------------------------------------------
    # Trigger: auto-populate location from lat/lon on properties
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION update_property_location()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
                NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_properties_location
        BEFORE INSERT OR UPDATE OF latitude, longitude ON properties
        FOR EACH ROW
        EXECUTE FUNCTION update_property_location();
    """)


def downgrade() -> None:
    # Drop triggers
    for table in ("users", "properties", "saved_deals", "alerts", "market_data"):
        op.execute(f"DROP TRIGGER IF EXISTS trigger_{table}_updated_at ON {table}")
    op.execute("DROP TRIGGER IF EXISTS trigger_properties_location ON properties")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP FUNCTION IF EXISTS update_property_location()")

    # Drop tables in dependency order
    op.drop_table("market_data")
    op.drop_table("alerts")
    op.drop_table("saved_deals")
    op.drop_table("properties")
    op.drop_table("users")

    # Drop enums
    for enum_name in (
        "property_type",
        "listing_status",
        "listing_source",
        "alert_channel",
        "subscription_tier",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
