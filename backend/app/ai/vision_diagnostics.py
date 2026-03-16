"""AI Vision Diagnostics — Analyze maintenance photos to diagnose issues."""

import base64
import json
import logging
import uuid
from dataclasses import dataclass

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.maintenance import (
    MaintenanceCategory,
    MaintenanceRequest,
    MaintenanceStatus,
    MaintenanceUrgency,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Diagnosis:
    category: str
    severity: int  # 1-5
    urgency: str  # emergency | urgent | routine
    description: str
    possible_causes: list[str]
    recommended_action: str
    trade_needed: str
    estimated_cost_low: float
    estimated_cost_high: float
    confidence: float


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIAGNOSIS_PROMPT = """Analyze this photo from a residential rental property maintenance request.

The tenant described the issue as: "{description}"

Identify and respond in JSON format:
{{
    "category": "water_damage|mold|structural_damage|hvac_issue|electrical|appliance_damage|pest_evidence|other",
    "severity": 1-5,
    "urgency": "emergency|urgent|routine",
    "description": "What you see in detail",
    "possible_causes": ["cause1", "cause2"],
    "recommended_action": "What the landlord should do",
    "trade_needed": "plumber|electrician|hvac_tech|general_contractor|pest_control|appliance_repair|other",
    "confidence": 0.0-1.0
}}

Severity scale:
1 = Cosmetic only (scuff, minor stain)
2 = Minor functional impact (dripping faucet)
3 = Moderate impact (slow leak, partial AC failure)
4 = Significant habitability impact (no hot water, major leak)
5 = Safety hazard (exposed wiring, gas leak signs, structural failure)

Urgency rules:
- emergency: Safety risk or active damage spreading (respond <=4 hours)
- urgent: Habitability impact (respond <=24 hours)
- routine: Non-critical issue (respond <=7 days)

Only respond with JSON."""

COST_ESTIMATES = {
    "plumber": {
        (1, 2): (150, 400),
        (3, 4): (400, 1500),
        (5, 5): (1500, 5000),
    },
    "electrician": {
        (1, 2): (100, 350),
        (3, 4): (350, 1200),
        (5, 5): (1200, 4000),
    },
    "hvac_tech": {
        (1, 2): (100, 400),
        (3, 4): (400, 2000),
        (5, 5): (2000, 7000),
    },
    "general_contractor": {
        (1, 2): (200, 600),
        (3, 4): (600, 3000),
        (5, 5): (3000, 10000),
    },
    "pest_control": {
        (1, 2): (100, 300),
        (3, 4): (300, 800),
        (5, 5): (800, 2500),
    },
    "appliance_repair": {
        (1, 2): (80, 250),
        (3, 4): (250, 600),
        (5, 5): (600, 1500),
    },
}

# Map AI category strings to our model enums
CATEGORY_MAP = {
    "water_damage": MaintenanceCategory.PLUMBING,
    "mold": MaintenanceCategory.OTHER,
    "structural_damage": MaintenanceCategory.STRUCTURAL,
    "hvac_issue": MaintenanceCategory.HVAC,
    "electrical": MaintenanceCategory.ELECTRICAL,
    "appliance_damage": MaintenanceCategory.APPLIANCE,
    "pest_evidence": MaintenanceCategory.PEST,
    "other": MaintenanceCategory.OTHER,
}

URGENCY_MAP = {
    "emergency": MaintenanceUrgency.EMERGENCY,
    "urgent": MaintenanceUrgency.URGENT,
    "routine": MaintenanceUrgency.ROUTINE,
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class VisionDiagnosticsService:
    """
    Integrated vision diagnostics service that analyzes maintenance photos
    using Claude Sonnet's vision capabilities and updates the database.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def diagnose(
        self,
        image_data: list[bytes],
        description: str = "",
    ) -> Diagnosis:
        """
        Analyze one or more maintenance photos and return a structured
        diagnosis. Does not touch the database; use diagnose_and_update()
        to also persist the result.
        """
        content: list[dict] = []
        for img in image_data:
            b64 = base64.standard_b64encode(img).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })

        content.append({
            "type": "text",
            "text": DIAGNOSIS_PROMPT.format(
                description=description or "No description provided"
            ),
        })

        response = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )

        result = json.loads(response.content[0].text)

        cost_low, cost_high = self._estimate_cost(
            result["trade_needed"], result["severity"]
        )

        return Diagnosis(
            category=result["category"],
            severity=result["severity"],
            urgency=result["urgency"],
            description=result["description"],
            possible_causes=result["possible_causes"],
            recommended_action=result["recommended_action"],
            trade_needed=result["trade_needed"],
            estimated_cost_low=cost_low,
            estimated_cost_high=cost_high,
            confidence=result["confidence"],
        )

    async def diagnose_and_update(
        self,
        request_id: uuid.UUID,
        image_data: list[bytes],
        description: str = "",
    ) -> Diagnosis:
        """
        Run vision diagnosis on photos attached to a maintenance request
        and update the database record with the results.
        """
        diagnosis = await self.diagnose(image_data, description)

        # Update the maintenance request record
        result = await self.db.execute(
            select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
        )
        request = result.scalar_one()

        request.ai_diagnosis = {
            "category": diagnosis.category,
            "severity": diagnosis.severity,
            "urgency": diagnosis.urgency,
            "description": diagnosis.description,
            "possible_causes": diagnosis.possible_causes,
            "recommended_action": diagnosis.recommended_action,
            "trade_needed": diagnosis.trade_needed,
        }
        request.ai_confidence = diagnosis.confidence
        request.estimated_cost_low = diagnosis.estimated_cost_low
        request.estimated_cost_high = diagnosis.estimated_cost_high

        # Map to model enums
        request.category = CATEGORY_MAP.get(
            diagnosis.category, MaintenanceCategory.OTHER
        )
        request.urgency = URGENCY_MAP.get(
            diagnosis.urgency, MaintenanceUrgency.ROUTINE
        )

        # Advance status to diagnosed
        if request.status == MaintenanceStatus.NEW:
            request.status = MaintenanceStatus.DIAGNOSED

        await self.db.flush()

        logger.info(
            "Diagnosis for request %s: %s (severity=%d, urgency=%s, confidence=%.2f)",
            request_id,
            diagnosis.category,
            diagnosis.severity,
            diagnosis.urgency,
            diagnosis.confidence,
        )

        return diagnosis

    def _estimate_cost(self, trade: str, severity: int) -> tuple[float, float]:
        """Look up estimated cost range by trade and severity."""
        trade_costs = COST_ESTIMATES.get(trade, COST_ESTIMATES["general_contractor"])
        for (low_sev, high_sev), cost_range in trade_costs.items():
            if low_sev <= severity <= high_sev:
                return cost_range
        return (200, 2000)
