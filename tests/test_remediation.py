"""Tests for the remediation engine."""

import pytest
from ai_consent.models import (
    Finding,
    RemediationPlan,
    RemediationStep,
    Severity,
)
from ai_consent.remediation import (
    generate_recommendations,
    generate_remediation_plan,
)


def _make_finding(
    req_id: str = "TEST-001",
    category: str = "human_oversight",
    title: str = "Test finding",
    severity: Severity = Severity.CRITICAL,
    status: str = "unsatisfied",
    current: int = 0,
    max_pts: int = 10,
) -> Finding:
    return Finding(
        requirement_id=req_id,
        article="Article 14",
        category=category,
        title=title,
        severity=severity,
        status=status,
        current_points=current,
        max_points=max_pts,
        reason="Test reason",
        recommendation="Fix this",
    )


class TestRecommendations:
    def test_generates_recommendations(self):
        findings = [
            _make_finding("TEST-001", "human_oversight", "Missing approval"),
            _make_finding("TEST-002", "logging_traceability", "No logging"),
        ]
        recs = generate_recommendations(findings)
        assert len(recs) == 2
        for r in recs:
            assert isinstance(r, RemediationStep)
            assert r.severity is not None
            assert r.category is not None
            assert r.recommendation

    def test_satisfied_not_recommended(self):
        findings = [
            _make_finding("TEST-001", status="satisfied", current=10, max_pts=10),
        ]
        recs = generate_recommendations(findings)
        assert len(recs) == 0

    def test_critical_first(self):
        """Critical findings should be listed before low severity."""
        findings = [
            _make_finding("LOW-001", severity=Severity.LOW, max_pts=5),
            _make_finding("CRIT-001", severity=Severity.CRITICAL, max_pts=10),
            _make_finding("MED-001", severity=Severity.MEDIUM, max_pts=3),
        ]
        recs = generate_recommendations(findings)
        assert recs[0].severity == Severity.CRITICAL

    def test_potential_gain_calculated(self):
        findings = [_make_finding("TEST-001", current=2, max_pts=10)]
        recs = generate_recommendations(findings)
        assert recs[0].potential_score_gain == 8


class TestRemediationPlan:
    def test_generates_three_tiers(self):
        findings = [
            _make_finding("C1", "human_oversight", "Critical unsat", Severity.CRITICAL, "unsatisfied"),
            _make_finding("H1", "data_governance", "High unsat", Severity.HIGH, "unsatisfied"),
            _make_finding("M1", "documentation", "Medium", Severity.MEDIUM, "partially_satisfied", current=5, max_pts=10),
            _make_finding("L1", "transparency", "Low", Severity.LOW, "partially_satisfied", current=8, max_pts=10),
        ]
        plan = generate_remediation_plan(findings)
        assert isinstance(plan, RemediationPlan)
        assert isinstance(plan.fix_first, list)
        assert isinstance(plan.fix_next, list)
        assert isinstance(plan.nice_to_have, list)
        # Critical unsat should be in fix_first
        assert len(plan.fix_first) >= 1
        # Low should be in nice_to_have
        assert len(plan.nice_to_have) >= 1

    def test_fix_first_contains_critical_blockers(self):
        findings = [
            _make_finding("C1", "human_oversight", "Critical unsat", Severity.CRITICAL, "unsatisfied", current=0, max_pts=10),
            _make_finding("C2", "risk_management", "Another critical", Severity.CRITICAL, "unsatisfied", current=0, max_pts=10),
        ]
        plan = generate_remediation_plan(findings)
        assert len(plan.fix_first) == 2