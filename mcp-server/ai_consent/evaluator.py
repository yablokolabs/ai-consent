"""Evaluator — the main entry point that orchestrates classification,
scoring, findings, and remediation into a full assessment.
"""

from __future__ import annotations

from .classifier import classify
from .models import (
    AgentManifest,
    Evidence,
    Finding,
    FullAssessment,
    RemediationPlan,
    RemediationStep,
    RiskClassification,
    Severity,
    SystemDescription,
    severity_from_str,
)
from .remediation import generate_remediation_plan, generate_recommendations
from .rules import Ruleset, default_ruleset
from .scorer import compute_score, score_dimension


def _system_from_manifest(manifest: AgentManifest) -> SystemDescription:
    """Convert an AgentManifest into a SystemDescription for classification."""
    sys_data = manifest.system or {}
    data = manifest.data or {}
    deployment = manifest.deployment or {}
    models = manifest.models or []

    return SystemDescription(
        name=sys_data.get("name", "unnamed-agent"),
        description=sys_data.get("purpose", sys_data.get("description", "")),
        industry=sys_data.get("industry", ""),
        users=sys_data.get("users", []),
        decisions=sys_data.get("decisions", []),
        data_types=data.get("data_types", []),
        deployment_region=deployment.get("regions", []),
        models=[m.get("model", m.get("provider", "")) for m in models],
        tools=sys_data.get("tools", []),
        personal_data=data.get("personal_data", False),
        sensitive_data=data.get("sensitive_data", False),
    )


def _evidence_from_manifest(manifest: AgentManifest) -> list[Evidence]:
    """Extract evidence items from a manifest."""
    evidence_list: list[Evidence] = list(manifest.evidence)

    # Auto-generate evidence from structured manifest fields.
    # Manifest fields count as "documented" because the manifest is a
    # structured configuration file, not a bare claim.
    logging = manifest.logging or {}
    if logging.get("enabled"):
        evidence_list.append(
            Evidence(
                category="logging_traceability",
                requirement_id="EUAI-LOG-001",
                description="Agent logging enabled per manifest",
                level="documented",
            )
        )
        if logging.get("retention_days"):
            evidence_list.append(
                Evidence(
                    category="logging_traceability",
                    requirement_id="EUAI-LOG-003",
                    description=f"Log retention: {logging['retention_days']} days",
                    level="documented",
                )
            )

    security = manifest.security or {}
    if security.get("authentication"):
        evidence_list.append(
            Evidence(
                category="cybersecurity",
                requirement_id="EUAI-SEC-002",
                description="Authentication enabled",
                level="documented",
            )
        )
    if security.get("authorization"):
        evidence_list.append(
            Evidence(
                category="cybersecurity",
                requirement_id="EUAI-SEC-002",
                description="Authorization enabled",
                level="documented",
            )
        )
    if security.get("secrets_manager"):
        evidence_list.append(
            Evidence(
                category="cybersecurity",
                requirement_id="EUAI-SEC-003",
                description="Secrets manager configured",
                level="documented",
            )
        )

    human = manifest.human_oversight or {}
    if human.get("enabled"):
        evidence_list.append(
            Evidence(
                category="human_oversight",
                requirement_id="EUAI-HUMAN-001",
                description="Human oversight enabled per manifest",
                level="documented",
            )
        )
    if human.get("approval_required_for"):
        evidence_list.append(
            Evidence(
                category="human_oversight",
                requirement_id="EUAI-HUMAN-005",
                description=f"Approval required for: {', '.join(human['approval_required_for'])}",
                level="documented",
            )
        )

    data = manifest.data or {}
    if data.get("data_lineage_documented"):
        evidence_list.append(
            Evidence(
                category="data_governance",
                requirement_id="EUAI-DATA-004",
                description="Data lineage documented per manifest",
                level="documented",
            )
        )

    docs = manifest.documentation or {}
    if docs:
        for key, val in docs.items():
            if val:
                evidence_list.append(
                    Evidence(
                        category="technical_documentation",
                        requirement_id="EUAI-TECH-001",
                        description=f"Documentation: {key}",
                        level="documented",
                    )
                )

    governance = manifest.governance or {}
    if governance.get("owner"):
        evidence_list.append(
            Evidence(
                category="governance",
                requirement_id="EUAI-GOV-001",
                description=f"Accountable owner: {governance['owner']}",
                level="documented",
            )
        )
    if governance.get("incident_response"):
        evidence_list.append(
            Evidence(
                category="governance",
                requirement_id="EUAI-GOV-004",
                description="Incident response plan exists",
                level="documented",
            )
        )

    return evidence_list


def assess_system(
    system: SystemDescription,
    ruleset: Ruleset | None = None,
    evidence_list: list[Evidence] | None = None,
) -> FullAssessment:
    """Perform a complete AI-Consent assessment.

    Args:
        system: The AI system to assess.
        ruleset: Ruleset to use (defaults to EU AI Act 2026).
        evidence_list: Optional evidence items.

    Returns:
        FullAssessment with risk classification, scores, findings,
        recommendations, and remediation plan.
    """
    if ruleset is None:
        ruleset = default_ruleset()

    if evidence_list is None:
        evidence_list = []

    # 1. Classify
    classification = classify(system)
    risk_level = classification.classification.value

    # 2. Score
    score_result = compute_score(ruleset, risk_level, evidence_list)
    score_result.classification_confidence = classification.confidence

    # 3. Generate findings
    findings = _generate_findings(ruleset, risk_level, evidence_list)

    # 4. Generate recommendations
    recommendations = generate_recommendations(findings)

    # 5. Generate remediation plan
    remediation_plan = generate_remediation_plan(findings)

    # 6. Compute potential score
    potential_gain = sum(r.potential_score_gain for r in recommendations)
    potential_score = min(100, score_result.overall_score + potential_gain)

    # 7. Missing evidence
    missing_evidence = classification.missing_information.copy()
    for f in findings:
        if f.status in ("unsatisfied", "unknown", "partially_satisfied"):
            missing_evidence.append(f"Missing evidence for {f.requirement_id}: {f.title}")

    return FullAssessment(
        assessment_version="1.0",
        ruleset=ruleset.ruleset_id,
        system=system,
        risk=classification,
        score=score_result,
        findings=findings,
        recommendations=recommendations,
        remediation_plan=remediation_plan,
        missing_evidence=sorted(set(missing_evidence)),
        potential_score=potential_score,
    )


def assess_manifest(
    manifest: AgentManifest,
    ruleset: Ruleset | None = None,
) -> FullAssessment:
    """Assess an ai-consent.yaml manifest.

    Args:
        manifest: Parsed AgentManifest.
        ruleset: Optional ruleset override.

    Returns:
        FullAssessment.
    """
    system = _system_from_manifest(manifest)
    evidence_list = _evidence_from_manifest(manifest)
    return assess_system(system, ruleset, evidence_list)


def reassess(
    previous: FullAssessment,
    changes: list[dict],
    ruleset: Ruleset | None = None,
) -> FullAssessment:
    """Reassess after changes have been made.

    Args:
        previous: The previous assessment.
        changes: List of changes made, each with requirement_id and new evidence.
        ruleset: Optional ruleset override.

    Returns:
        New FullAssessment with updated scores.
    """
    if ruleset is None:
        ruleset = default_ruleset()

    # Build evidence from previous assessment + changes
    # We use a simplified approach: take previous evidence and update
    new_evidence_map: dict[str, Evidence] = {}

    # Parse previous evidence from findings
    for f in previous.findings:
        if f.status == "satisfied":
            new_evidence_map[f.requirement_id] = Evidence(
                category=f.category,
                requirement_id=f.requirement_id,
                description=f"Previously satisfied: {f.title}",
                level="claimed",
            )

    # Apply changes
    for change in changes:
        req_id = change.get("requirement_id", "")
        evidence = change.get("evidence", {})
        level_str = evidence.get("level", "claimed")
        level_map = {
            "claimed": "claimed",
            "documented": "documented",
            "technically_evidenced": "technically_evidenced",
            "independently_verified": "independently_verified",
        }

        from .models import EvidenceLevel as EL
        level = EL(level_map.get(level_str, "claimed"))

        new_evidence_map[req_id] = Evidence(
            category=evidence.get("category", "unknown"),
            requirement_id=req_id,
            description=evidence.get("description", "Updated evidence"),
            level=level,
        )

    evidence_list = list(new_evidence_map.values())
    return assess_system(previous.system, ruleset, evidence_list)


def _generate_findings(
    ruleset: Ruleset,
    risk_level: str,
    evidence_list: list[Evidence],
) -> list[Finding]:
    """Generate detailed findings for each rule."""
    findings: list[Finding] = []
    evidence_by_id = {e.requirement_id: e for e in evidence_list}

    for rule in ruleset.rules:
        applies = rule.get("applies_to", [])
        if "all" not in applies and risk_level not in applies:
            if not (risk_level in ("high_risk", "prohibited") and "high_risk" in applies):
                continue

        evidence = evidence_by_id.get(rule["id"])
        weight = rule["weight"]

        if evidence is None:
            findings.append(
                Finding(
                    requirement_id=rule["id"],
                    article=rule.get("article", ""),
                    category=rule["category"],
                    title=rule["title"],
                    severity=severity_from_str(rule.get("severity", "medium")),
                    status="unsatisfied",
                    current_points=0,
                    max_points=weight,
                    reason=f"No evidence provided: {rule['description']}",
                    recommendation=rule.get("evidence_guidance", "Provide evidence for this requirement."),
                )
            )
        else:
            confidence = evidence.level.confidence
            if confidence >= 0.85:
                status = "satisfied"
                pts = weight
            elif confidence >= 0.6:
                status = "partially_satisfied"
                pts = int(weight * confidence)
            elif confidence >= 0.3:
                status = "partially_satisfied"
                pts = int(weight * confidence)
            else:
                status = "unsatisfied"
                pts = 0

            findings.append(
                Finding(
                    requirement_id=rule["id"],
                    article=rule.get("article", ""),
                    category=rule["category"],
                    title=rule["title"],
                    severity=severity_from_str(rule.get("severity", "medium")),
                    status=status,
                    current_points=pts,
                    max_points=weight,
                    reason=f"Evidence: {evidence.description} (level: {evidence.level.value}, confidence: {confidence:.0%})",
                    recommendation="",
                )
            )

    return findings