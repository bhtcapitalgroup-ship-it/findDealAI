"""TenantBot — AI-powered tenant communication agent integrated with the backend."""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import (
    ChannelType,
    Conversation,
    ConversationStatus,
    Message,
    SenderType,
)
from app.models.lease import Lease, LeaseStatus
from app.models.maintenance import MaintenanceRequest, MaintenanceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Intent(str, Enum):
    MAINTENANCE = "maintenance"
    PAYMENT = "payment"
    LEASE = "lease"
    COMPLAINT = "complaint"
    GENERAL = "general"


@dataclass
class Classification:
    intent: Intent
    subtype: str
    confidence: float
    entities: dict


@dataclass
class TenantContext:
    tenant_name: str
    unit_number: str
    property_name: str
    rent_amount: float
    rent_due_day: int
    lease_end: str | None
    payment_status: str  # "current" | "past_due" | "partial"
    balance_due: float
    open_maintenance: list[dict]
    recent_messages: list[dict]
    property_rules: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ESCALATION_KEYWORDS = re.compile(
    r"\b(lawyer|attorney|sue|legal action|lawsuit|discriminat|harass|"
    r"threaten|health department|code violation|withhold rent|rent strike)\b",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are a professional AI property management assistant for {property_name}.
You help tenants with maintenance requests, payment questions, and lease inquiries.

RULES:
- Never provide legal advice. Say "I'd recommend consulting with a legal professional."
- Never make promises about rent reductions or lease modifications without landlord approval.
- Never discuss other tenants or share their information.
- Always be empathetic about maintenance issues.
- If unsure, say you'll escalate to the property manager.
- Do not discuss property value, sale plans, or ownership details.
- Keep responses concise and helpful.

TENANT CONTEXT:
- Name: {tenant_name}
- Unit: {unit_number}
- Rent: ${rent_amount}/month, due on day {rent_due_day}
- Payment status: {payment_status}
- Balance due: ${balance_due}
- Lease ends: {lease_end}
- Open maintenance requests: {open_maintenance}

PROPERTY RULES:
{property_rules}"""

CLASSIFY_PROMPT = """Classify this tenant message into one of these intents:
- maintenance: repair requests, broken items, leaks, HVAC issues
- payment: rent balance, payment receipt, payment plan, late fees
- lease: renewal, termination, move-out, lease terms questions
- complaint: noise, neighbor issues, safety concerns
- general: parking, packages, amenities, greetings, other

Message: "{message}"

Respond in JSON: {{"intent": "...", "subtype": "...", "confidence": 0.0-1.0, "entities": {{}}}}
Only respond with JSON, nothing else."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TenantBotService:
    """
    Integrated tenant chatbot service that loads context from the database,
    processes messages through the Claude AI pipeline, and persists results.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(
        self,
        tenant_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None = None,
        channel: ChannelType = ChannelType.WEB,
    ) -> dict:
        """
        End-to-end message processing:
        1. Load tenant context from DB
        2. Get or create conversation
        3. Save inbound message
        4. Run AI pipeline (classify, guard, respond)
        5. Save outbound message
        6. Return result dict
        """
        # 1. Load context
        context = await self._load_tenant_context(tenant_id)

        # 2. Get or create conversation
        conversation = await self._get_or_create_conversation(
            tenant_id, conversation_id, channel
        )

        # 3. Save the inbound tenant message
        tenant_msg = Message(
            conversation_id=conversation.id,
            sender_type=SenderType.TENANT,
            content=message,
        )
        self.db.add(tenant_msg)
        await self.db.flush()

        # 4. Run AI pipeline
        result = await self._run_ai_pipeline(message, context)

        # 5. Save AI response message
        ai_msg = Message(
            conversation_id=conversation.id,
            sender_type=SenderType.AI,
            content=result["response"],
            intent=result.get("classification", {}).get("intent") if isinstance(result.get("classification"), dict) else (
                result["classification"].intent if hasattr(result.get("classification", None), "intent") else None
            ),
            confidence=result.get("classification", {}).get("confidence") if isinstance(result.get("classification"), dict) else (
                result["classification"].confidence if hasattr(result.get("classification", None), "confidence") else None
            ),
            metadata_={"escalated": result["escalated"], "side_effects": result.get("side_effects", [])},
        )
        self.db.add(ai_msg)

        # 6. If escalated, update conversation status
        if result["escalated"]:
            conversation.status = ConversationStatus.ESCALATED

        await self.db.flush()

        result["conversation_id"] = str(conversation.id)
        result["message_id"] = str(ai_msg.id)
        return result

    # ------------------------------------------------------------------
    # AI pipeline internals
    # ------------------------------------------------------------------

    async def _run_ai_pipeline(self, message: str, context: TenantContext) -> dict:
        """Run the full AI pipeline: escalation check, classify, respond."""

        # 1. Escalation keyword check
        if ESCALATION_KEYWORDS.search(message):
            return {
                "response": (
                    f"I understand your concern, {context.tenant_name}. "
                    "I'm escalating this to your property manager for "
                    "immediate attention. They'll be in touch shortly."
                ),
                "escalated": True,
                "reason": "keyword_trigger",
                "classification": None,
                "side_effects": [],
            }

        # 2. Classify intent
        classification = await self._classify_intent(message)

        # 3. Low confidence -> escalate
        if classification.confidence < 0.7:
            return {
                "response": (
                    "I want to make sure I get this right. Let me have "
                    "your property manager follow up with you directly."
                ),
                "escalated": True,
                "reason": "low_confidence",
                "classification": classification,
                "side_effects": [],
            }

        # 4. Generate contextual response
        response_text = await self._generate_response(message, context, classification)

        # 5. Determine side effects
        side_effects = self._get_side_effects(classification)

        return {
            "response": response_text,
            "escalated": False,
            "classification": classification,
            "side_effects": side_effects,
        }

    async def _classify_intent(self, message: str) -> Classification:
        """Classify the intent of a tenant message using Claude Haiku."""
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[
                    {"role": "user", "content": CLASSIFY_PROMPT.format(message=message)}
                ],
            )
            result = json.loads(response.content[0].text)
            return Classification(
                intent=Intent(result["intent"]),
                subtype=result.get("subtype", ""),
                confidence=result.get("confidence", 0.5),
                entities=result.get("entities", {}),
            )
        except Exception as exc:
            logger.error("Intent classification failed: %s", exc)
            return Classification(
                intent=Intent.GENERAL,
                subtype="unknown",
                confidence=0.0,
                entities={},
            )

    async def _generate_response(
        self,
        message: str,
        context: TenantContext,
        classification: Classification,
    ) -> str:
        """Generate a contextual response using Claude Sonnet."""
        system = SYSTEM_PROMPT.format(
            property_name=context.property_name,
            tenant_name=context.tenant_name,
            unit_number=context.unit_number,
            rent_amount=context.rent_amount,
            rent_due_day=context.rent_due_day,
            payment_status=context.payment_status,
            balance_due=context.balance_due,
            lease_end=context.lease_end or "Month-to-month",
            open_maintenance=context.open_maintenance or "None",
            property_rules=context.property_rules or "Standard rules apply.",
        )

        # Build conversation history from recent messages
        messages = []
        for msg in context.recent_messages[-10:]:
            role = "assistant" if msg["sender"] == "ai" else "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6-20250514",
                max_tokens=500,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except Exception as exc:
            logger.error("Response generation failed: %s", exc)
            return (
                "I'm sorry, I'm having trouble processing your request right now. "
                "Your property manager has been notified and will follow up with you."
            )

    def _get_side_effects(self, classification: Classification) -> list[dict]:
        """Determine what background actions to trigger based on classification."""
        effects: list[dict] = []

        if classification.intent == Intent.MAINTENANCE:
            effects.append({
                "action": "create_maintenance_request",
                "category": classification.subtype,
                "entities": classification.entities,
            })
        elif classification.intent == Intent.PAYMENT:
            if classification.subtype == "payment_plan":
                effects.append({
                    "action": "escalate_to_landlord",
                    "reason": "Payment plan request requires landlord approval",
                })
        elif classification.intent == Intent.COMPLAINT:
            effects.append({
                "action": "escalate_to_landlord",
                "reason": f"Tenant complaint: {classification.subtype}",
            })

        return effects

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    async def _load_tenant_context(self, tenant_id: uuid.UUID) -> TenantContext:
        """Load full tenant context from the database for AI prompting."""

        # Fetch tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        # Fetch active lease
        result = await self.db.execute(
            select(Lease)
            .where(Lease.tenant_id == tenant_id, Lease.status == LeaseStatus.ACTIVE)
            .order_by(Lease.start_date.desc())
            .limit(1)
        )
        lease = result.scalar_one_or_none()

        # Fetch unit and property
        unit_number = "N/A"
        property_name = "N/A"
        if lease:
            result = await self.db.execute(select(Unit).where(Unit.id == lease.unit_id))
            unit = result.scalar_one_or_none()
            if unit:
                unit_number = unit.unit_number
                result = await self.db.execute(
                    select(Property).where(Property.id == unit.property_id)
                )
                prop = result.scalar_one_or_none()
                if prop:
                    property_name = prop.name

        # Payment status
        payment_status = "current"
        balance_due = 0.0
        if lease:
            result = await self.db.execute(
                select(Payment)
                .where(
                    Payment.lease_id == lease.id,
                    Payment.status == PaymentStatus.PENDING,
                )
            )
            pending_payments = result.scalars().all()
            if pending_payments:
                balance_due = sum(float(p.amount) for p in pending_payments)
                payment_status = "past_due" if balance_due >= float(lease.rent_amount) else "partial"

        # Open maintenance requests
        result = await self.db.execute(
            select(MaintenanceRequest)
            .where(
                MaintenanceRequest.tenant_id == tenant_id,
                MaintenanceRequest.status.notin_([
                    MaintenanceStatus.COMPLETED,
                    MaintenanceStatus.CANCELLED,
                ]),
            )
            .order_by(MaintenanceRequest.created_at.desc())
            .limit(5)
        )
        open_requests = result.scalars().all()
        open_maintenance = [
            {
                "id": str(r.id),
                "title": r.title,
                "status": r.status.value,
                "urgency": r.urgency.value,
            }
            for r in open_requests
        ]

        # Recent messages from the latest conversation
        recent_messages: list[dict] = []
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        latest_conversation = result.scalar_one_or_none()
        if latest_conversation:
            result = await self.db.execute(
                select(Message)
                .where(Message.conversation_id == latest_conversation.id)
                .order_by(Message.created_at.desc())
                .limit(20)
            )
            msgs = result.scalars().all()
            for m in reversed(msgs):
                recent_messages.append({
                    "sender": m.sender_type.value,
                    "content": m.content,
                })

        return TenantContext(
            tenant_name=f"{tenant.first_name} {tenant.last_name}",
            unit_number=unit_number,
            property_name=property_name,
            rent_amount=float(lease.rent_amount) if lease else 0.0,
            rent_due_day=lease.rent_due_day if lease else 1,
            lease_end=str(lease.end_date) if lease and lease.end_date else None,
            payment_status=payment_status,
            balance_due=balance_due,
            open_maintenance=open_maintenance,
            recent_messages=recent_messages,
            property_rules="Standard property rules apply.",
        )

    async def _get_or_create_conversation(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        channel: ChannelType,
    ) -> Conversation:
        """Retrieve an existing conversation or create a new one."""
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        # Find the landlord_id from tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        # Look for an existing open conversation
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.status == ConversationStatus.OPEN,
                Conversation.channel == channel,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Create new conversation
        conversation = Conversation(
            tenant_id=tenant_id,
            landlord_id=tenant.landlord_id,
            channel=channel,
            status=ConversationStatus.OPEN,
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation
