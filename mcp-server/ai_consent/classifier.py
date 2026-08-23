"""Risk classifier — determines the likely EU AI Act risk category
for a described AI system using deterministic rules.

Does NOT use an LLM.  Classification is rules-based and explainable.
"""

from __future__ import annotations

from .models import (
    ClassificationResult,
    RiskClassification,
    SystemDescription,
)

# ── Annex III high-risk use-case patterns ────────────────────────────

_HIGH_RISK_PATTERNS: list[tuple[list[str], list[str], str, str]] = [
    # (industry_keywords, decision_keywords, reason, article)
    (
        ["recruitment", "hiring", "employment", "hr", "talent"],
        ["candidate", "applicant", "job application", "screening", "selection",
         "promotion", "termination", "evaluation", "worker"],
        "AI used in employment/recruitment (Annex III.4)",
        "Annex III.4",
    ),
    (
        ["education", "school", "university", "training", "academic"],
        ["admission", "enrolment", "grading", "assessment", "exam", "test",
         "learning outcome", "student"],
        "AI used in education/vocational training (Annex III.3)",
        "Annex III.3",
    ),
    (
        ["healthcare", "medical", "health", "clinical", "hospital", "patient"],
        ["diagnosis", "treatment", "triage", "patient", "clinical decision",
         "medical", "health assessment"],
        "AI used in healthcare/medical decisions (Annex III.5a)",
        "Annex III.5a",
    ),
    (
        ["law enforcement", "police", "justice", "court", "legal", "immigration",
         "border", "asylum"],
        ["risk assessment", "crime", "offender", "suspect", "enforcement",
         "surveillance", "detection"],
        "AI used in law enforcement/justice/migration (Annex III.6-8)",
        "Annex III.6-8",
    ),
    (
        ["critical infrastructure", "energy", "water", "transport", "traffic",
         "electricity", "gas", "heating"],
        ["safety", "infrastructure", "control", "management", "operation"],
        "AI used in critical infrastructure (Annex III.2)",
        "Annex III.2",
    ),
    (
        ["finance", "credit", "insurance", "banking", "lending"],
        ["creditworthiness", "credit score", "risk assessment", "pricing",
         "eligibility", "loan"],
        "AI used in essential financial services (Annex III.5b/c)",
        "Annex III.5b/c",
    ),
    (
        ["public services", "government", "welfare", "benefits"],
        ["eligibility", "benefits", "assistance", "grant", "public service"],
        "AI used in essential public services (Annex III.5a)",
        "Annex III.5a",
    ),
    (
        ["biometrics", "facial recognition", "emotion", "biometric"],
        ["identification", "categorisation", "emotion recognition", "biometric"],
        "AI used in biometric categorisation/emotion recognition (Annex III.1)",
        "Annex III.1",
    ),
]

# ── Prohibited practice patterns ──────────────────────────────────────

_PROHIBITED_PATTERNS: list[tuple[list[str], list[str], str, str]] = [
    (
        ["social scoring", "social credit", "behaviour evaluation"],
        ["classify", "score", "rate", "trustworthiness"],
        "Social scoring / behavioural classification may be prohibited (Article 5)",
        "Article 5(c)",
    ),
    (
        ["subliminal", "manipulation", "deceptive", "exploit"],
        ["manipulate", "deceive", "subliminal", "distort behaviour"],
        "Subliminal/manipulative techniques may be prohibited (Article 5(a))",
        "Article 5(a)",
    ),
    (
        ["vulnerability", "exploit vulnerable"],
        ["exploit", "vulnerable", "disability", "age"],
        "Exploitation of vulnerable persons may be prohibited (Article 5(b))",
        "Article 5(b)",
    ),
    (
        ["predictive policing", "crime prediction"],
        ["predict crime", "criminal risk", "reoffend"],
        "Predictive policing may be prohibited (Article 5(d))",
        "Article 5(d)",
    ),
]

# ── Transparency-only patterns ────────────────────────────────────────

_TRANSPARENCY_PATTERNS: list[tuple[list[str], list[str], str, str]] = [
    (
        ["chatbot", "customer support", "assistant", "conversational"],
        ["respond", "chat", "answer", "assist", "conversation"],
        "Direct interaction with natural persons requires transparency (Article 50)",
        "Article 50",
    ),
]


def _matches_pattern(
    desc: str,
    industry: str,
    decisions: list[str],
    industry_kw: list[str],
    decision_kw: list[str],
) -> bool:
    """Check if description/industry/decisions match a keyword pattern."""
    text = f"{desc.lower()} {industry.lower()} {' '.join(d.lower() for d in decisions)}"
    industry_match = any(kw in text for kw in industry_kw)
    decision_match = any(kw in text for kw in decision_kw)
    # Match if either industry or decisions strongly suggest the domain
    if industry_match and decision_match:
        return True
    if industry_match and len(decision_kw) <= 2:
        return True
    return False


def classify(system: SystemDescription) -> ClassificationResult:
    """Classify an AI system's likely EU AI Act risk category.

    Uses deterministic pattern-matching against the system description,
    industry, and decision types. Does not invent facts — if insufficient
    information exists, returns UNCERTAIN.

    Args:
        system: The AI system description to classify.

    Returns:
        ClassificationResult with category, confidence, reasons, and
        any missing information.
    """
    desc = system.description or ""
    industry = system.industry or ""
    decisions = system.decisions or []
    data_types = system.data_types or []
    deployment = system.deployment_region or []

    reasons: list[str] = []
    articles: list[str] = []
    missing: list[str] = []

    # Build a combined text for matching
    combined = f"{desc.lower()} {industry.lower()} {' '.join(d.lower() for d in decisions)}"

    # ── Check prohibited patterns first ───────────────────────────────
    prohibited_hits = 0
    for industry_kw, decision_kw, reason, article in _PROHIBITED_PATTERNS:
        if _matches_pattern(desc, industry, decisions, industry_kw, decision_kw):
            reasons.append(reason)
            articles.append(article)
            prohibited_hits += 1

    # ── Check Annex III high-risk patterns ────────────────────────────
    high_risk_hits = 0
    for industry_kw, decision_kw, reason, article in _HIGH_RISK_PATTERNS:
        if _matches_pattern(desc, industry, decisions, industry_kw, decision_kw):
            reasons.append(reason)
            articles.append(article)
            high_risk_hits += 1

    # ── Check transparency-only patterns ──────────────────────────────
    transparency_hits = 0
    for industry_kw, decision_kw, reason, article in _TRANSPARENCY_PATTERNS:
        if _matches_pattern(desc, industry, decisions, industry_kw, decision_kw):
            reasons.append(reason)
            articles.append(article)
            transparency_hits += 1

    # ── Personal data flagging ────────────────────────────────────────
    if system.personal_data or any("personal" in dt.lower() for dt in data_types):
        reasons.append("System processes personal data — may trigger data governance obligations.")

    if system.sensitive_data or any("sensitive" in dt.lower() for dt in data_types) or \
       any("biometric" in dt.lower() for dt in data_types):
        reasons.append("System processes sensitive data — heightened obligations likely.")
        if not high_risk_hits:
            missing.append("Clarify whether sensitive data processing triggers Annex III classification.")

    # ── Determine classification ──────────────────────────────────────

    if prohibited_hits > 0:
        classification = RiskClassification.PROHIBITED
        confidence = min(0.95, 0.7 + 0.1 * prohibited_hits)
    elif high_risk_hits > 0:
        classification = RiskClassification.HIGH_RISK
        confidence = min(0.90, 0.6 + 0.1 * high_risk_hits)
        if len(combined.split()) < 20:
            missing.append(
                "Provide more detail about the intended purpose, "
                "users, and decision types."
            )
    elif transparency_hits > 0:
        classification = RiskClassification.LIMITED_RISK
        confidence = 0.75
    elif not desc.strip() or not industry.strip():
        classification = RiskClassification.UNCERTAIN
        confidence = 0.1
        missing.append("Insufficient information: provide system description and industry.")
    else:
        # Default: check if there are any signs of risk
        has_personal = system.personal_data or any(
            "personal" in dt.lower() for dt in data_types
        )
        if has_personal and any(
            kw in combined
            for kw in ["decision", "evaluate", "assess", "score", "filter"]
        ):
            classification = RiskClassification.UNCERTAIN
            confidence = 0.3
            missing.append(
                "System processes personal data and makes evaluative decisions. "
                "Provide details on decision types and industry to refine classification."
            )
        elif any(d in combined for d in ["decision", "evaluate", "assess"]):
            classification = RiskClassification.UNCERTAIN
            confidence = 0.4
            missing.append("Describe the decisions and industry context more precisely.")
        else:
            classification = RiskClassification.MINIMAL_RISK
            confidence = 0.7

    # Deploying in EU triggers most obligations
    if "eu" in deployment or "europe" in deployment:
        if classification == RiskClassification.MINIMAL_RISK:
            reasons.append("Deployed in EU — transparency obligations still apply.")

    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        reasons=reasons,
        potential_articles=sorted(set(articles)),
        missing_information=missing,
    )