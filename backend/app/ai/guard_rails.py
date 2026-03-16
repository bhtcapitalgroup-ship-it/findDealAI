"""Guard Rails — Safety filters for AI-generated responses in property management."""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    category: str     # "fair_housing" | "legal_advice" | "pii_leakage" | "financial_promise"
    severity: str     # "block" | "warn"
    matched_text: str
    explanation: str


@dataclass
class GuardResult:
    safe: bool
    violations: list[Violation] = field(default_factory=list)
    sanitized_response: str | None = None


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Fair Housing Act protected classes and discriminatory language
FAIR_HOUSING_PATTERNS = [
    (
        re.compile(
            r"\b(because of|due to|based on)\s+(your|their|the tenant'?s?)\s+"
            r"(race|color|national origin|religion|sex|familial status|disability|"
            r"sexual orientation|gender identity|age|marital status|source of income)\b",
            re.IGNORECASE,
        ),
        "Response references a protected class in a potentially discriminatory context.",
    ),
    (
        re.compile(
            r"\b(we (don'?t|do not) (rent|lease) to|not (suitable|appropriate) for|"
            r"(prefer|looking for) (tenants|people) (who|that) are|"
            r"this (neighborhood|area|building) is (not|best) for)\b",
            re.IGNORECASE,
        ),
        "Response contains language that could be interpreted as discriminatory steering.",
    ),
    (
        re.compile(
            r"\b(too many (children|kids|people)|family.{0,20}(too large|won'?t fit)|"
            r"(children|kids) (are not|aren'?t) (allowed|permitted)|"
            r"adults.only|no (children|kids|families))\b",
            re.IGNORECASE,
        ),
        "Response contains language that may violate familial status protections.",
    ),
    (
        re.compile(
            r"\b(we (can'?t|cannot|don'?t|do not) accommodate\s+(your\s+)?"
            r"(disability|wheelchair|service animal|emotional support)|"
            r"(disability|handicap).{0,20}(not allowed|prohibited|unacceptable))\b",
            re.IGNORECASE,
        ),
        "Response may violate disability accommodation requirements.",
    ),
]

# Legal advice patterns
LEGAL_ADVICE_PATTERNS = [
    (
        re.compile(
            r"\b(you (should|must|have to|need to)\s+(file|sue|take.+to court|"
            r"contact.+lawyer|hire.+attorney|seek legal)|"
            r"(legal(ly)?|law) (requires|states|mandates|says) (you|that)|"
            r"your (legal )?(rights|obligations) (are|include)|"
            r"(under|per|according to) (the law|state law|federal law|"
            r"the statute|section \d+)|"
            r"you (can|could|may) (be (evicted|sued)|face (legal|criminal))|"
            r"this (constitutes|is considered) (a |)(breach|violation|default))\b",
            re.IGNORECASE,
        ),
        "Response appears to provide legal advice or interpretation.",
    ),
    (
        re.compile(
            r"\b(I('m| am) not (a|your) (lawyer|attorney)|"
            r"this is not legal advice|"
            r"(consult|speak with|contact) (a|an|your) (lawyer|attorney|legal))\b",
            re.IGNORECASE,
        ),
        None,  # Disclaimer is fine — skip these matches
    ),
]

# PII patterns (SSN, credit card, bank account, DOB)
PII_PATTERNS = [
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "Response contains what appears to be a Social Security Number.",
    ),
    (
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "Response contains what appears to be a credit card number.",
    ),
    (
        re.compile(r"\b(account|routing)\s*(number|#|no\.?)\s*:?\s*\d{6,17}\b", re.IGNORECASE),
        "Response contains what appears to be a bank account or routing number.",
    ),
    (
        re.compile(
            r"\b(ssn|social security|social security number)\s*:?\s*\d{3}",
            re.IGNORECASE,
        ),
        "Response references a Social Security Number with digits.",
    ),
    (
        re.compile(
            r"\b(date of birth|dob|born on)\s*:?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",
            re.IGNORECASE,
        ),
        "Response contains a date of birth.",
    ),
]

# Financial promise patterns
FINANCIAL_PROMISE_PATTERNS = [
    (
        re.compile(
            r"\b(I('ll| will)|we('ll| will)|the company will)\s+"
            r"(waive|reduce|lower|forgive|eliminate|remove|credit|refund|"
            r"discount|write off|absorb)\s+"
            r"(the|your|any|all)?\s*(late fee|rent|charge|balance|amount|payment|"
            r"security deposit|fee|cost)\b",
            re.IGNORECASE,
        ),
        "Response promises to waive, reduce, or forgive a financial obligation.",
    ),
    (
        re.compile(
            r"\b(I|we) (guarantee|promise|assure you|commit to|agree to)\s+"
            r".{0,50}(payment|rent|fee|cost|price|amount|deposit)\b",
            re.IGNORECASE,
        ),
        "Response makes a binding financial commitment without landlord authorization.",
    ),
    (
        re.compile(
            r"\b(your rent (will be|is being|has been) (reduced|lowered|changed to)|"
            r"we('re| are) (giving|offering) you a (discount|reduction|credit)|"
            r"(don'?t|no need to) (worry about|pay) (the|your) (late fee|balance))\b",
            re.IGNORECASE,
        ),
        "Response implies a rent reduction or fee waiver.",
    ),
]

# Redaction pattern for PII scrubbing
PII_REDACT_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD REDACTED]"),
    (
        re.compile(r"\b(account|routing)\s*(number|#|no\.?)\s*:?\s*\d{6,17}\b", re.IGNORECASE),
        "[ACCOUNT REDACTED]",
    ),
]


# ---------------------------------------------------------------------------
# Main checking function
# ---------------------------------------------------------------------------

def check_ai_response(response: str) -> GuardResult:
    """
    Run all guard rail checks against an AI-generated response.

    Returns a GuardResult indicating whether the response is safe to send,
    any violations found, and an optional sanitized version of the response.
    """
    violations: list[Violation] = []

    # 1. Fair Housing compliance
    for pattern, explanation in FAIR_HOUSING_PATTERNS:
        matches = pattern.findall(response)
        if matches:
            matched_text = matches[0] if isinstance(matches[0], str) else " ".join(matches[0])
            violations.append(Violation(
                category="fair_housing",
                severity="block",
                matched_text=matched_text,
                explanation=explanation,
            ))

    # 2. Legal advice detection
    for pattern, explanation in LEGAL_ADVICE_PATTERNS:
        if explanation is None:
            # This is a disclaimer pattern — skip
            continue
        matches = pattern.findall(response)
        if matches:
            matched_text = matches[0] if isinstance(matches[0], str) else " ".join(matches[0])
            violations.append(Violation(
                category="legal_advice",
                severity="warn",
                matched_text=matched_text,
                explanation=explanation,
            ))

    # 3. PII leakage prevention
    for pattern, explanation in PII_PATTERNS:
        matches = pattern.findall(response)
        if matches:
            matched_text = matches[0] if isinstance(matches[0], str) else str(matches[0])
            violations.append(Violation(
                category="pii_leakage",
                severity="block",
                matched_text="[REDACTED]",
                explanation=explanation,
            ))

    # 4. Financial promise detection
    for pattern, explanation in FINANCIAL_PROMISE_PATTERNS:
        matches = pattern.findall(response)
        if matches:
            matched_text = matches[0] if isinstance(matches[0], str) else " ".join(matches[0])
            violations.append(Violation(
                category="financial_promise",
                severity="warn",
                matched_text=matched_text,
                explanation=explanation,
            ))

    # Determine safety
    has_blocks = any(v.severity == "block" for v in violations)
    safe = len(violations) == 0

    # Build sanitized response (redact PII even if otherwise safe)
    sanitized = response
    for pattern, replacement in PII_REDACT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    if has_blocks:
        sanitized = (
            "I apologize, but I'm unable to respond to that at this time. "
            "Please contact your property manager directly for assistance."
        )

    result = GuardResult(
        safe=safe,
        violations=violations,
        sanitized_response=sanitized if not safe else None,
    )

    if violations:
        logger.warning(
            "Guard rail violations detected: %s",
            [(v.category, v.severity) for v in violations],
        )

    return result
