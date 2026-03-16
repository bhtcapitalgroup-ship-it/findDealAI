"""TenantBot — AI-powered tenant communication agent."""

import re
from dataclasses import dataclass
from enum import Enum

import anthropic


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


class TenantBot:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def process_message(
        self, message: str, context: TenantContext
    ) -> dict:
        """Process an inbound tenant message and return AI response."""

        # 1. Check for escalation triggers
        if ESCALATION_KEYWORDS.search(message):
            return {
                "response": (
                    f"I understand your concern, {context.tenant_name}. "
                    "I'm escalating this to your property manager for "
                    "immediate attention. They'll be in touch shortly."
                ),
                "escalated": True,
                "reason": "keyword_trigger",
            }

        # 2. Classify intent
        classification = await self.classify_intent(message)

        # 3. Low confidence → escalate
        if classification.confidence < 0.7:
            return {
                "response": (
                    "I want to make sure I get this right. Let me have "
                    "your property manager follow up with you directly."
                ),
                "escalated": True,
                "reason": "low_confidence",
                "classification": classification,
            }

        # 4. Generate contextual response
        response = await self.generate_response(message, context, classification)

        # 5. Trigger side effects
        side_effects = self.get_side_effects(classification)

        return {
            "response": response,
            "escalated": False,
            "classification": classification,
            "side_effects": side_effects,
        }

    async def classify_intent(self, message: str) -> Classification:
        """Classify the intent of a tenant message."""
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {"role": "user", "content": CLASSIFY_PROMPT.format(message=message)}
            ],
        )

        import json
        result = json.loads(response.content[0].text)

        return Classification(
            intent=Intent(result["intent"]),
            subtype=result.get("subtype", ""),
            confidence=result.get("confidence", 0.5),
            entities=result.get("entities", {}),
        )

    async def generate_response(
        self, message: str, context: TenantContext, classification: Classification
    ) -> str:
        """Generate a contextual response using the full tenant context."""
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

        # Include recent conversation history
        messages = []
        for msg in context.recent_messages[-10:]:
            role = "assistant" if msg["sender"] == "ai" else "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        response = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=500,
            system=system,
            messages=messages,
        )

        return response.content[0].text

    def get_side_effects(self, classification: Classification) -> list[dict]:
        """Determine what actions to trigger based on classification."""
        effects = []

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

        return effects
