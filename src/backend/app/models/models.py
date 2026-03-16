"""SQLAlchemy ORM models for RealDeal AI."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, SmallInteger, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Landlord(Base):
    __tablename__ = "landlords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    company_name = Column(String(200))
    stripe_account_id = Column(String(100))
    plan_tier = Column(String(20), default="starter")
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    properties = relationship("Property", back_populates="landlord")
    tenants = relationship("Tenant", back_populates="landlord")


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    property_type = Column(String(20), nullable=False)
    total_units = Column(Integer, default=1)
    purchase_price = Column(Numeric(12, 2))
    current_value = Column(Numeric(12, 2))
    mortgage_payment = Column(Numeric(10, 2))
    insurance_cost = Column(Numeric(10, 2))
    tax_annual = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    landlord = relationship("Landlord", back_populates="properties")
    units = relationship("Unit", back_populates="property")


class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    unit_number = Column(String(20), nullable=False)
    bedrooms = Column(SmallInteger)
    bathrooms = Column(Numeric(3, 1))
    sqft = Column(Integer)
    market_rent = Column(Numeric(10, 2))
    status = Column(String(20), default="vacant")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    property = relationship("Property", back_populates="units")
    leases = relationship("Lease", back_populates="unit")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(20), nullable=False, index=True)
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
    portal_enabled = Column(Boolean, default=False)
    preferred_language = Column(String(5), default="en")
    stripe_customer_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    landlord = relationship("Landlord", back_populates="tenants")
    leases = relationship("Lease", back_populates="tenant")
    payments = relationship("Payment", back_populates="tenant")


class Lease(Base):
    __tablename__ = "leases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    rent_amount = Column(Numeric(10, 2), nullable=False)
    deposit_amount = Column(Numeric(10, 2))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    rent_due_day = Column(SmallInteger, default=1)
    late_fee_amount = Column(Numeric(10, 2))
    late_fee_grace_days = Column(SmallInteger, default=5)
    lease_type = Column(String(20), default="fixed")
    status = Column(String(20), default="active", index=True)
    ai_analysis = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    unit = relationship("Unit", back_populates="leases")
    tenant = relationship("Tenant", back_populates="leases")
    payments = relationship("Payment", back_populates="lease")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lease_id = Column(UUID(as_uuid=True), ForeignKey("leases.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_type = Column(String(20), nullable=False)
    payment_method = Column(String(20))
    status = Column(String(20), default="pending", index=True)
    stripe_payment_id = Column(String(100))
    due_date = Column(Date, nullable=False, index=True)
    paid_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lease = relationship("Lease", back_populates="payments")
    tenant = relationship("Tenant", back_populates="payments")


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50))
    urgency = Column(String(20), default="routine")
    status = Column(String(20), default="new", index=True)
    ai_diagnosis = Column(JSONB)
    ai_confidence = Column(Numeric(3, 2))
    estimated_cost_low = Column(Numeric(10, 2))
    estimated_cost_high = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))
    scheduled_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    tenant_rating = Column(SmallInteger)
    tenant_feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    contact_name = Column(String(200))
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    trades = Column(ARRAY(String(50)), nullable=False)
    avg_rating = Column(Numeric(3, 2), default=0)
    total_jobs = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), index=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    doc_type = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    ai_analysis = Column(JSONB)
    ocr_text = Column(Text)
    tags = Column(ARRAY(String(50)))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("landlords.id"), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(50))
    confidence = Column(Numeric(3, 2))
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
