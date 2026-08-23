"""Core data models for AI-Consent.

All assessment inputs, outputs, and internal models are defined here
using typed Python with Pydantic.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Risk Classification ──────────────────────────────────────────────


class RiskClassification(str, Enum):
    """EU AI Act risk categories."""

    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"
    GPAI = "gpai"
    MINIMAL_RISK = "minimal_risk"
    UNCERTAIN = "uncertain"


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceLevel(str, Enum):
    """Confidence level of evidence provided."""

    CLAIMED = "claimed"
    DOCUMENTED = "documented"
    TECHNICALLY_EVIDENCED = "technically_evidenced"
    INDEPENDENTLY_VERIFIED = "independently_verified"

    @property
    def confidence(self) -> float:
        """Convert evidence level to a confidence multiplier."""
        return {
            EvidenceLevel.CLAIMED: 0.3,
            EvidenceLevel.DOCUMENTED: 0.6,
            EvidenceLevel.TECHNICALLY_EVIDENCED: 0.85,
            EvidenceLevel.INDEPENDENTLY_VERIFIED: 1.0,
        }[self]


class StatusBand(str, Enum):
    """Readiness status bands."""

    STRONG = "strong_readiness"
    GOOD = "good_remediation_recommended"
    SIGNIFICANT_GAPS = "significant_gaps"
    HIGH_RISK = "high_regulatory_risk"
    CRITICAL = "critical_gaps"


# ── Input Models ──────────────────────────────────────────────────────


class SystemDescription(BaseModel):
    """User-supplied description of an AI system to assess."""

    name: str = Field(description="System or agent name")
    description: str = Field(description="What the system does, its purpose")
    industry: str = Field(default="", description="Industry / sector")
    users: list[str] = Field(default_factory=list, description="Who uses the system")
    decisions: list[str] = Field(
        default_factory=list,
        description="Types of decisions the system makes or influences",
    )
    data_types: list[str] = Field(
        default_factory=list,
        description="Types of data the system processes (e.g. personal_data, biometric, financial)",
    )
    deployment_region: list[str] = Field(
        default_factory=list,
        description="Regions where deployed, e.g. ['EU']",
    )
    models: list[str] = Field(
        default_factory=list,
        description="Models or providers used",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Tools or capabilities the agent has access to",
    )
    personal_data: bool = Field(default=False)
    sensitive_data: bool = Field(default=False)


class Evidence(BaseModel):
    """Evidence supporting a compliance claim."""

    category: str = Field(description="Category this evidence relates to")
    requirement_id: str = Field(description="Rule ID this evidence supports")
    description: str = Field(default="", description="What the evidence demonstrates")
    level: EvidenceLevel = Field(default=EvidenceLevel.CLAIMED)
    details: dict[str, Any] = Field(default_factory=dict)


class AgentManifest(BaseModel):
    """The ai-consent.yaml manifest format for AI agent self-description."""

    system: dict[str, Any] = Field(default_factory=dict)
    deployment: dict[str, Any] = Field(default_factory=dict)
    models: list[dict[str, str]] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    human_oversight: dict[str, Any] = Field(default_factory=dict)
    logging: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    documentation: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


# ── Classification Output ─────────────────────────────────────────────


class ClassificationResult(BaseModel):
    """Result of risk classification."""

    classification: RiskClassification = Field(
        description="Likely EU AI Act risk category"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the classification"
    )
    reasons: list[str] = Field(
        default_factory=list, description="Why this classification was assigned"
    )
    potential_articles: list[str] = Field(
        default_factory=list,
        description="Relevant EU AI Act articles",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Information that would improve classification confidence",
    )


# ── Scoring Output ────────────────────────────────────────────────────


class DimensionScore(BaseModel):
    """Score for a single compliance dimension."""

    dimension: str = Field(description="Dimension name/category")
    score: int = Field(ge=0, le=100, description="Score 0-100")
    max_score: int = Field(ge=0, le=100)
    passed: int = Field(default=0, description="Number of passing rules")
    total: int = Field(default=0, description="Total rules in this dimension")
    findings: list[str] = Field(default_factory=list)


class ScoreResult(BaseModel):
    """Full readiness score result."""

    overall_score: int = Field(ge=0, le=100)
    status: StatusBand
    risk_classification: RiskClassification
    classification_confidence: float = Field(ge=0.0, le=1.0)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall evidence confidence",
    )


# ── Finding and Recommendation ────────────────────────────────────────


class Finding(BaseModel):
    """A single compliance gap or finding."""

    requirement_id: str
    article: str
    category: str
    title: str
    severity: Severity
    status: str = Field(description="satisfied | partially_satisfied | unsatisfied | not_applicable | unknown")
    current_points: int = Field(default=0)
    max_points: int = Field(default=0)
    reason: str = Field(default="")
    recommendation: str = Field(default="")


class RemediationStep(BaseModel):
    """A single recommended remediation action."""

    finding: str = Field(description="What the gap is")
    severity: Severity
    category: str
    current_points: int = Field(default=0)
    max_points: int = Field(default=0)
    recommendation: str = Field(description="What to do")
    implementation: dict[str, str] = Field(default_factory=dict)
    potential_score_gain: int = Field(default=0)


class RemediationPlan(BaseModel):
    """Prioritized remediation plan."""

    fix_first: list[RemediationStep] = Field(default_factory=list)
    fix_next: list[RemediationStep] = Field(default_factory=list)
    nice_to_have: list[RemediationStep] = Field(default_factory=list)


# ── Full Assessment ───────────────────────────────────────────────────


class FullAssessment(BaseModel):
    """Complete AI-Consent assessment output."""

    assessment_version: str = Field(default="1.0")
    ruleset: str = Field(default="EU-AI-ACT-2026")
    system: SystemDescription
    risk: ClassificationResult
    score: ScoreResult
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[RemediationStep] = Field(default_factory=list)
    remediation_plan: RemediationPlan | None = None
    missing_evidence: list[str] = Field(default_factory=list)
    potential_score: int = Field(ge=0, le=100)
    disclaimer: str = (
        "AI-Consent provides automated EU AI Act readiness assessments "
        "and engineering guidance. It does not constitute legal advice, "
        "regulatory certification, conformity assessment, or a guarantee "
        "of compliance. Further legal/conformity review may be required."
    )


class ReassessmentResult(BaseModel):
    """Result of a reassessment after changes."""

    previous_score: int
    current_score: int
    score_delta: int
    closed_findings: list[str] = Field(default_factory=list)
    remaining_findings: list[str] = Field(default_factory=list)
    new_findings: list[Finding] = Field(default_factory=list)
    assessment: FullAssessment


# ── Risk Register ──────────────────────────────────────────────────────


class RiskEntry(BaseModel):
    """A single entry in the AI risk register."""

    risk_id: str
    category: str
    description: str
    likelihood: str = Field(description="e.g. rare, unlikely, possible, likely, almost_certain")
    impact: str = Field(description="e.g. negligible, minor, moderate, major, critical")
    severity: Severity
    mitigation: str = Field(default="")
    residual_risk: str = Field(default="")
    owner: str = Field(default="")


class RiskRegister(BaseModel):
    """Structured AI risk register."""

    system: str
    ruleset: str
    entries: list[RiskEntry] = Field(default_factory=list)
    generated_at: str = Field(default="")


# ── Technical Documentation Draft ─────────────────────────────────────


class TechnicalDocSection(BaseModel):
    """A section of technical documentation."""

    title: str
    content: str
    requires_review: bool = Field(default=True)


class TechnicalDocumentation(BaseModel):
    """Draft technical documentation package."""

    system_name: str
    disclaimer: str = (
        "This document is an AI-generated draft requiring human review. "
        "It does not constitute official technical documentation for EU AI Act compliance."
    )
    sections: list[TechnicalDocSection] = Field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────


def status_band(score: int) -> StatusBand:
    """Map a numeric score to a status band."""
    if score >= 90:
        return StatusBand.STRONG
    if score >= 75:
        return StatusBand.GOOD
    if score >= 50:
        return StatusBand.SIGNIFICANT_GAPS
    if score >= 25:
        return StatusBand.HIGH_RISK
    return StatusBand.CRITICAL


def severity_from_str(s: str) -> Severity:
    """Parse severity string."""
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
    }
    return mapping.get(s.lower(), Severity.MEDIUM)


# ── Dimension weights ─────────────────────────────────────────────────

DIMENSION_NAMES: dict[str, str] = {
    "risk_management": "Risk Management",
    "data_governance": "Data Governance",
    "technical_documentation": "Technical Documentation",
    "logging_traceability": "Logging & Traceability",
    "human_oversight": "Human Oversight",
    "accuracy_robustness": "Accuracy & Robustness",
    "cybersecurity": "Cybersecurity",
    "transparency": "Transparency",
    "governance": "Governance",
}