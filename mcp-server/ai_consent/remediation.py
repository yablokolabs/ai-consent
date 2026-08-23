"""Remediation engine — generates prioritized recommendations and plans
from compliance findings.

Prioritization formula: impact × severity × (1 / implementation_effort)
"""

from __future__ import annotations

from .models import Finding, RemediationPlan, RemediationStep, Severity


_SEVERITY_PRIORITY: dict[Severity, int] = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
}


def _priority_score(finding: Finding) -> int:
    """Compute a priority score for a finding. Higher = fix first."""
    sev = _SEVERITY_PRIORITY.get(finding.severity, 1)
    gap = finding.max_points - finding.current_points
    return sev * gap


def generate_recommendations(findings: list[Finding]) -> list[RemediationStep]:
    """Generate remediation recommendations from findings.

    Args:
        findings: Assessment findings.

    Returns:
        Sorted list of RemediationSteps.
    """
    recommendations: list[RemediationStep] = []

    for f in findings:
        if f.status in ("satisfied", "not_applicable"):
            continue

        # Determine implementation suggestion
        impl_type, impl_sugg = _implementation_suggestion(f)

        recommendations.append(
            RemediationStep(
                finding=f"{f.requirement_id}: {f.title}",
                severity=f.severity,
                category=f.category,
                current_points=f.current_points,
                max_points=f.max_points,
                recommendation=f.recommendation or f"Address: {f.reason}",
                implementation={
                    "type": impl_type,
                    "suggestion": impl_sugg,
                },
                potential_score_gain=f.max_points - f.current_points,
            )
        )

    # Sort by priority: critical gaps first, then by potential gain
    recommendations.sort(
        key=lambda r: (
            -_SEVERITY_PRIORITY.get(r.severity, 1),
            -r.potential_score_gain,
        )
    )

    return recommendations


def generate_remediation_plan(findings: list[Finding]) -> RemediationPlan:
    """Generate a prioritized three-tier remediation plan.

    - fix_first: Critical blockers (severity: critical/high, unsatisfied)
    - fix_next: High-value improvements (medium severity or partially satisfied)
    - nice_to_have: Lower-risk maturity improvements
    """
    recommendations = generate_recommendations(findings)

    fix_first: list[RemediationStep] = []
    fix_next: list[RemediationStep] = []
    nice_to_have: list[RemediationStep] = []

    for r in recommendations:
        if r.severity in (Severity.CRITICAL, Severity.HIGH) and r.current_points == 0:
            fix_first.append(r)
        elif r.severity in (Severity.CRITICAL, Severity.HIGH):
            fix_next.append(r)
        elif r.severity == Severity.MEDIUM:
            fix_next.append(r)
        else:
            nice_to_have.append(r)

    return RemediationPlan(
        fix_first=fix_first,
        fix_next=fix_next,
        nice_to_have=nice_to_have,
    )


def _implementation_suggestion(finding: Finding) -> tuple[str, str]:
    """Generate implementation guidance for a finding based on its category."""
    cat = finding.category
    title = finding.title.lower()

    if cat == "human_oversight":
        if "approval" in title:
            return (
                "human_in_the_loop",
                "Add an approval gateway that requires explicit human sign-off before executing consequential actions.",
            )
        if "override" in title or "stop" in title:
            return (
                "human_in_the_loop",
                "Implement a stop/override mechanism accessible to designated operators at runtime.",
            )
        return (
            "human_in_the_loop",
            "Design human oversight interfaces that allow operators to understand, monitor, and intervene.",
        )

    if cat == "logging_traceability":
        if "retention" in title:
            return (
                "logging",
                "Configure log retention with minimum 6-month duration. Export logs to durable storage.",
            )
        return (
            "logging",
            "Implement structured JSON logging for all AI system inputs, outputs, decisions, and errors with timestamps.",
        )

    if cat == "risk_management":
        return (
            "documentation",
            "Create a risk management document covering known risks, foreseeable misuse, mitigations, and residual risk assessment.",
        )

    if cat == "data_governance":
        if "bias" in title:
            return (
                "data_quality",
                "Implement bias testing across protected groups. Document fairness metrics and remediation measures.",
            )
        return (
            "data_governance",
            "Document data provenance, collection purpose, quality metrics, and minimisation practices.",
        )

    if cat == "technical_documentation":
        return (
            "documentation",
            "Prepare technical documentation covering system purpose, architecture, limitations, models, and intended users.",
        )

    if cat == "accuracy_robustness":
        return (
            "testing",
            "Implement evaluation pipelines with accuracy benchmarks, adversarial testing, and fallback behavior.",
        )

    if cat == "cybersecurity":
        return (
            "security",
            "Implement security controls: authentication, authorization, secret management, input validation, tool sandboxing.",
        )

    if cat == "transparency":
        return (
            "transparency",
            "Add AI disclosure notices, content labeling, and explainability features.",
        )

    if cat == "governance":
        return (
            "governance",
            "Designate accountable owner, establish AI inventory, incident response plan, and compliance review process.",
        )

    return (
        "documentation",
        "Document and implement controls for this requirement.",
    )