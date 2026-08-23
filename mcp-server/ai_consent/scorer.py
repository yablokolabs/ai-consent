"""Scoring engine — deterministic compliance-readiness scoring.

Uses the loaded ruleset and evidence to compute dimension scores
and an overall weighted score from 0-100.
"""

from __future__ import annotations

from .models import (
    DIMENSION_NAMES,
    DimensionScore,
    Evidence,
    EvidenceLevel,
    ScoreResult,
    Severity,
    status_band,
    severity_from_str,
)
from .rules import Ruleset


def _evidence_for_requirement(
    requirement_id: str,
    evidence_list: list[Evidence],
) -> Evidence | None:
    """Find the best evidence for a given requirement."""
    matches = [e for e in evidence_list if e.requirement_id == requirement_id]
    if not matches:
        return None
    # Return the highest-confidence evidence
    return max(matches, key=lambda e: e.level.confidence)


def _score_rule(
    rule: dict,
    evidence: Evidence | None,
) -> tuple[int, str, str]:
    """Score a single rule, returning (points_earned, status, reason)."""
    max_pts = rule["weight"]

    if evidence is None:
        return 0, "unsatisfied", f"No evidence provided for {rule['id']}: {rule['title']}"

    level = evidence.level
    confidence = level.confidence

    # Base score is weight * evidence confidence
    if level == EvidenceLevel.INDEPENDENTLY_VERIFIED:
        earned = max_pts
        status = "satisfied"
        reason = f"Independently verified: {evidence.description or rule['title']}"
    elif level == EvidenceLevel.TECHNICALLY_EVIDENCED:
        earned = int(max_pts * 0.85)
        status = "partially_satisfied" if earned < max_pts else "satisfied"
        reason = f"Technically evidenced (confidence: {confidence:.0%}): {evidence.description or rule['title']}"
    elif level == EvidenceLevel.DOCUMENTED:
        earned = int(max_pts * 0.6)
        status = "partially_satisfied"
        reason = f"Documented but not technically evidenced (confidence: {confidence:.0%}): {evidence.description or rule['title']}"
    elif level == EvidenceLevel.CLAIMED:
        earned = int(max_pts * 0.3)
        status = "partially_satisfied"
        reason = f"Claimed only — no evidence submitted (confidence: {confidence:.0%}): {evidence.description or rule['title']}"
    else:
        earned = 0
        status = "unknown"
        reason = f"Unable to assess: {rule['title']}"

    # Severity modifier: critical rules that are unsatisfied get nothing
    severity = severity_from_str(rule.get("severity", "medium"))
    if severity == Severity.CRITICAL and level in (EvidenceLevel.CLAIMED,):
        earned = int(earned * 0.5)  # Half points for critical items claimed-only

    return min(earned, max_pts), status, reason


def score_dimension(
    ruleset: Ruleset,
    category: str,
    risk_level: str,
    evidence_list: list[Evidence],
) -> DimensionScore:
    """Score a single compliance dimension.

    Args:
        ruleset: The loaded ruleset.
        category: Dimension category key.
        risk_level: The system's risk classification.
        evidence_list: All provided evidence items.

    Returns:
        DimensionScore with computed score.
    """
    applicable = ruleset.rules_for_category(category)

    # Filter to rules that apply for this risk level
    relevant = []
    for r in applicable:
        applies = r.get("applies_to", [])
        if "all" in applies or risk_level in applies:
            relevant.append(r)
        elif risk_level in ("high_risk", "prohibited") and "high_risk" in applies:
            relevant.append(r)

    if not relevant:
        # No applicable rules for this dimension at this risk level.
        # Return score=100 meaning "no obligations detected".
        return DimensionScore(
            dimension=category,
            score=100,
            max_score=100,
            passed=0,
            total=0,
            findings=[],
        )

    total_max = sum(r["weight"] for r in relevant)
    if total_max == 0:
        return DimensionScore(
            dimension=category,
            score=100,
            max_score=100,
            passed=0,
            total=0,
            findings=[],
        )
    total_earned = 0
    passed = 0
    findings: list[str] = []

    for rule in relevant:
        evidence = _evidence_for_requirement(rule["id"], evidence_list)
        earned, status, reason = _score_rule(rule, evidence)
        total_earned += earned

        if status == "satisfied":
            passed += 1
        elif status in ("unsatisfied", "partially_satisfied"):
            findings.append(f"  ✗ {rule['id']}: {rule['title']} — {reason}")

    # Dimension score scaled to 0-100
    if total_max > 0:
        dim_score = int((total_earned / total_max) * 100)
    else:
        dim_score = 100

    return DimensionScore(
        dimension=category,
        score=dim_score,
        max_score=100,
        passed=passed,
        total=len(relevant),
        findings=findings,
    )


def compute_score(
    ruleset: Ruleset,
    risk_level: str,
    evidence_list: list[Evidence],
) -> ScoreResult:
    """Compute the full compliance readiness score.

    Args:
        ruleset: The loaded ruleset.
        risk_level: The system's risk classification.
        evidence_list: All provided evidence items.

    Returns:
        ScoreResult with overall and per-dimension scores.
    """
    categories = [
        "risk_management",
        "data_governance",
        "technical_documentation",
        "logging_traceability",
        "human_oversight",
        "accuracy_robustness",
        "cybersecurity",
        "transparency",
        "governance",
    ]

    dimension_scores: list[DimensionScore] = []
    total_applicable_weight = 0
    weighted_sum = 0

    for cat in categories:
        dim = score_dimension(ruleset, cat, risk_level, evidence_list)
        dimension_scores.append(dim)

        # Weight the dimension based on how many rules apply
        applicable = ruleset.rules_for_category(cat)
        relevant = [r for r in applicable if
                    "all" in r.get("applies_to", []) or
                    risk_level in r.get("applies_to", []) or
                    (risk_level in ("high_risk", "prohibited") and "high_risk" in r.get("applies_to", []))]
        dim_weight = sum(r["weight"] for r in relevant)
        total_applicable_weight += dim_weight
        weighted_sum += dim.score * dim_weight

    if total_applicable_weight > 0:
        overall = int(weighted_sum / total_applicable_weight)
    else:
        overall = 100

    # Compute overall evidence confidence
    if evidence_list:
        avg_confidence = sum(e.level.confidence for e in evidence_list) / len(evidence_list)
    else:
        avg_confidence = 0.0

    return ScoreResult(
        overall_score=overall,
        status=status_band(overall),
        risk_classification=risk_level,
        classification_confidence=0.0,
        dimensions=dimension_scores,
        confidence=avg_confidence,
    )