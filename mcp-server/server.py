"""AI-Consent MCP Server — EU AI Act readiness scoring via MCP.

Exposes AI-Consent assessment tools over the Model Context Protocol.
Uses SSE transport for MCPize deployment; stdio for local execution.

Tools:
  classify_ai_system  — Determine EU AI Act risk category
  assess_agent         — Full compliance readiness assessment
  score_compliance     — Numeric score + breakdown
  check_requirement    — Check a single requirement
  suggest_improvements — Prioritized improvement recommendations
  generate_remediation_plan — Ordered remediation roadmap
  generate_risk_register — Structured AI risk register
  generate_technical_documentation — Draft tech docs
  check_human_oversight — Evaluate human-in-the-loop controls
  check_logging       — Evaluate auditability & traceability
  reassess            — Re-score after improvements
  assess_manifest     — Assess from ai-consent.yaml content
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ai_consent.classifier import classify
from ai_consent.evaluator import (
    _system_from_manifest,
    assess_manifest as _assess_manifest,
    assess_system,
)
from ai_consent.models import (
    AgentManifest,
    ClassificationResult,
    Evidence,
    EvidenceLevel,
    FullAssessment,
    RiskEntry,
    RiskRegister,
    SystemDescription,
    TechnicalDocSection,
    TechnicalDocumentation,
    severity_from_str,
)
from ai_consent.remediation import (
    generate_recommendations,
    generate_remediation_plan,
)
from ai_consent.rules import default_ruleset, load_ruleset
from ai_consent.scorer import compute_score

DISCLAIMER = (
    "AI-Consent provides automated EU AI Act readiness assessments "
    "and engineering guidance. It does not constitute legal advice, "
    "regulatory certification, conformity assessment, or a guarantee "
    "of compliance. Further legal/conformity review may be required."
)

mcp = FastMCP(
    "ai-consent-mcp",
    instructions=(
        "EU AI Act readiness scoring for AI agents. "
        "Scan. Score. Fix. Re-check. "
        "Classify risk, assess compliance, get remediation guidance. "
        "Never represents scores as legal certification."
    ),
)


# ── Helper: normalize tool return ────────────────────────────────────

def _ok(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _error(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


# ── MCP Tools ─────────────────────────────────────────────────────────


@mcp.tool()
def classify_ai_system(
    name: str,
    description: str,
    industry: str = "",
    users: list[str] | None = None,
    decisions: list[str] | None = None,
    data_types: list[str] | None = None,
    deployment_region: list[str] | None = None,
    models: list[str] | None = None,
    tools: list[str] | None = None,
    personal_data: bool = False,
    sensitive_data: bool = False,
) -> str:
    """Classify an AI system under the EU AI Act risk categories.

    Determines whether the described system is likely to be:
    prohibited, high-risk, limited-risk (transparency), GPAI, or minimal-risk.

    Uses deterministic rules. Never invents facts. Returns 'uncertain'
    when insufficient information exists.

    Args:
        name: System or agent name.
        description: What the system does, its intended purpose.
        industry: Industry/sector (e.g. recruitment, healthcare, logistics).
        users: Who uses the system.
        decisions: Types of decisions the system makes or influences.
        data_types: Types of data processed (e.g. personal_data, biometric).
        deployment_region: Regions where deployed, e.g. ['EU'].
        models: Models or providers used.
        tools: Tools/capabilities the agent has access to.
        personal_data: Whether the system processes personal data.
        sensitive_data: Whether the system processes sensitive data.

    Returns:
        JSON with classification, confidence, reasons, potential articles,
        and any missing information needed.
    """
    system = SystemDescription(
        name=name,
        description=description,
        industry=industry,
        users=users or [],
        decisions=decisions or [],
        data_types=data_types or [],
        deployment_region=deployment_region or [],
        models=models or [],
        tools=tools or [],
        personal_data=personal_data,
        sensitive_data=sensitive_data,
    )

    result = classify(system)
    return _ok({
        "classification": result.classification.value,
        "confidence": result.confidence,
        "reasons": result.reasons,
        "potential_articles": result.potential_articles,
        "missing_information": result.missing_information,
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def assess_agent(
    name: str,
    description: str,
    industry: str = "",
    users: list[str] | None = None,
    decisions: list[str] | None = None,
    data_types: list[str] | None = None,
    deployment_region: list[str] | None = None,
    models: list[str] | None = None,
    tools: list[str] | None = None,
    personal_data: bool = False,
    sensitive_data: bool = False,
    evidence: list[dict] | None = None,
) -> str:
    """Perform a complete EU AI Act readiness assessment.

    Returns risk classification, overall score (0-100), dimension-by-dimension
    scores, findings, recommendations, and a prioritized remediation plan.

    Args:
        name: System/agent name.
        description: What the system does and its intended purpose.
        industry: Industry/sector.
        users: Who uses the system.
        decisions: Types of decisions the system makes.
        data_types: Types of data processed.
        deployment_region: Deployment regions.
        models: Models/providers used.
        tools: Tools/capabilities available.
        personal_data: Processes personal data.
        sensitive_data: Processes sensitive data.
        evidence: Optional list of evidence items, each with:
            - requirement_id: Rule ID this evidence supports
            - category: Category
            - description: What the evidence demonstrates
            - level: claimed | documented | technically_evidenced | independently_verified

    Returns:
        JSON FullAssessment with classification, score, dimensions,
        findings, recommendations, remediation plan, and disclaimer.
    """
    system = SystemDescription(
        name=name,
        description=description,
        industry=industry,
        users=users or [],
        decisions=decisions or [],
        data_types=data_types or [],
        deployment_region=deployment_region or [],
        models=models or [],
        tools=tools or [],
        personal_data=personal_data,
        sensitive_data=sensitive_data,
    )

    # Parse evidence
    evidence_list: list[Evidence] = []
    if evidence:
        for ev in evidence:
            level_str = ev.get("level", "claimed")
            try:
                level = EvidenceLevel(level_str)
            except ValueError:
                level = EvidenceLevel.CLAIMED
            evidence_list.append(
                Evidence(
                    category=ev.get("category", "unknown"),
                    requirement_id=ev.get("requirement_id", ""),
                    description=ev.get("description", ""),
                    level=level,
                )
            )

    assessment = assess_system(system, evidence_list=evidence_list)
    return _ok({
        "assessment_version": assessment.assessment_version,
        "ruleset": assessment.ruleset,
        "system": assessment.system.model_dump(),
        "risk": assessment.risk.model_dump(),
        "score": assessment.score.model_dump(),
        "findings_count": len(assessment.findings),
        "findings": [f.model_dump() for f in assessment.findings],
        "recommendations": [r.model_dump() for r in assessment.recommendations],
        "remediation_plan": assessment.remediation_plan.model_dump() if assessment.remediation_plan else None,
        "missing_evidence": assessment.missing_evidence,
        "potential_score": assessment.potential_score,
        "disclaimer": assessment.disclaimer,
    })


@mcp.tool()
def score_compliance(
    name: str,
    description: str,
    industry: str = "",
    evidence: list[dict] | None = None,
) -> str:
    """Return the numeric EU AI Act readiness score and per-dimension breakdown.

    Args:
        name: System name.
        description: What the system does.
        industry: Industry/sector.
        evidence: Optional evidence items.

    Returns:
        JSON with overall_score, status, and dimension scores.
    """
    system = SystemDescription(
        name=name,
        description=description,
        industry=industry,
    )

    from ai_consent.classifier import classify as _cls
    classification = _cls(system)

    evidence_list: list[Evidence] = []
    if evidence:
        for ev in evidence:
            try:
                level = EvidenceLevel(ev.get("level", "claimed"))
            except ValueError:
                level = EvidenceLevel.CLAIMED
            evidence_list.append(
                Evidence(
                    category=ev.get("category", "unknown"),
                    requirement_id=ev.get("requirement_id", ""),
                    description=ev.get("description", ""),
                    level=level,
                )
            )

    score = compute_score(default_ruleset(), classification.classification.value, evidence_list)
    return _ok({
        "overall_score": score.overall_score,
        "status": score.status.value,
        "risk_classification": classification.classification.value,
        "dimensions": [
            {
                "dimension": d.dimension,
                "score": d.score,
                "max_score": d.max_score,
                "passed": d.passed,
                "total": d.total,
            }
            for d in score.dimensions
        ],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def check_requirement(requirement_id: str, evidence: dict | None = None) -> str:
    """Check whether a specific EU AI Act requirement is satisfied.

    Args:
        requirement_id: Rule ID to check (e.g. EUAI-HUMAN-OVERSIGHT-001).
        evidence: Optional evidence object with:
            - description: What the evidence demonstrates
            - level: claimed | documented | technically_evidenced | independently_verified

    Returns:
        JSON with status (satisfied/partially_satisfied/unsatisfied/not_applicable/unknown)
        and guidance.
    """
    ruleset = default_ruleset()
    rule = ruleset.get_rule(requirement_id)

    if rule is None:
        return _error(f"Unknown requirement: {requirement_id}")

    if evidence is None:
        return _ok({
            "requirement_id": requirement_id,
            "title": rule["title"],
            "article": rule["article"],
            "category": rule["category"],
            "severity": rule["severity"],
            "status": "unsatisfied",
            "reason": "No evidence provided.",
            "guidance": rule.get("evidence_guidance", "Provide evidence."),
        })

    level_str = evidence.get("level", "claimed")
    try:
        level = EvidenceLevel(level_str)
    except ValueError:
        level = EvidenceLevel.CLAIMED

    confidence = level.confidence
    if confidence >= 0.85:
        status = "satisfied"
    elif confidence >= 0.6:
        status = "partially_satisfied"
    elif confidence >= 0.3:
        status = "partially_satisfied"
    else:
        status = "unsatisfied"

    return _ok({
        "requirement_id": requirement_id,
        "title": rule["title"],
        "article": rule["article"],
        "category": rule["category"],
        "severity": rule["severity"],
        "status": status,
        "confidence": confidence,
        "guidance": "Satisfactory" if status == "satisfied" else rule.get("evidence_guidance", "Provide stronger evidence."),
    })


@mcp.tool()
def suggest_improvements(
    name: str = "",
    description: str = "",
    industry: str = "",
) -> str:
    """Return prioritized improvements to raise your compliance-readiness score.

    Args:
        name: System name.
        description: What the system does.
        industry: Industry/sector.

    Returns:
        JSON list of prioritized RemediationSteps with potential score gains.
    """
    system = SystemDescription(
        name=name or "unnamed",
        description=description,
        industry=industry,
    )
    assessment = assess_system(system)
    return _ok({
        "current_score": assessment.score.overall_score,
        "potential_score": assessment.potential_score,
        "improvements": [r.model_dump() for r in assessment.recommendations],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def generate_remediation_plan(
    name: str = "",
    description: str = "",
    industry: str = "",
) -> str:
    """Generate a prioritized, three-tier remediation plan.

    Returns fix_first (critical blockers), fix_next (high-value improvements),
    and nice_to_have (maturity improvements).

    Args:
        name: System name.
        description: What the system does.
        industry: Industry/sector.

    Returns:
        JSON RemediationPlan with three tiers of remediation steps.
    """
    system = SystemDescription(
        name=name or "unnamed",
        description=description,
        industry=industry,
    )
    assessment = assess_system(system)

    plan = assessment.remediation_plan
    if plan is None:
        findings = assessment.findings
        plan = generate_remediation_plan(findings)

    return _ok({
        "current_score": assessment.score.overall_score,
        "potential_score": assessment.potential_score,
        "fix_first": [r.model_dump() for r in plan.fix_first],
        "fix_next": [r.model_dump() for r in plan.fix_next],
        "nice_to_have": [r.model_dump() for r in plan.nice_to_have],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def generate_risk_register(
    name: str,
    description: str,
    industry: str = "",
) -> str:
    """Generate a structured AI risk register from the system description.

    Provides JSON and assessment-driven risk entries with categories,
    likelihood, impact, severity, and suggested mitigations.

    Args:
        name: System name.
        description: What the system does.
        industry: Industry/sector.

    Returns:
        JSON RiskRegister with structured risk entries.
    """
    system = SystemDescription(
        name=name,
        description=description,
        industry=industry,
    )
    assessment = assess_system(system)

    entries: list[RiskEntry] = []
    for i, f in enumerate(assessment.findings):
        if f.status == "satisfied":
            continue
        likelihood = "possible" if f.severity.value in ("critical", "high") else "unlikely"
        impact = "major" if f.severity.value == "critical" else "moderate" if f.severity.value == "high" else "minor"
        entries.append(
            RiskEntry(
                risk_id=f"RISK-{i+1:03d}",
                category=f.category,
                description=f"{f.title}: {f.reason}",
                likelihood=likelihood,
                impact=impact,
                severity=f.severity,
                mitigation=f.recommendation or "Implement appropriate controls.",
                residual_risk="To be assessed after mitigation.",
                owner="TBD",
            )
        )

    from datetime import datetime
    register = RiskRegister(
        system=name,
        ruleset="EU-AI-ACT-2026",
        entries=entries,
        generated_at=datetime.now().isoformat(),
    )

    return _ok(register.model_dump())


@mcp.tool()
def generate_technical_documentation(
    name: str,
    description: str,
    models: list[str] | None = None,
    tools: list[str] | None = None,
    system_architecture: str = "",
    intended_users: str = "",
    deployment_environment: str = "",
    limitations: str = "",
    version: str = "0.1.0",
) -> str:
    """Generate a draft technical documentation package from supplied evidence.

    Clearly labeled as draft requiring human review. Not a substitute for
    official Annex IV documentation.

    Args:
        name: System name.
        description: System purpose.
        models: Models or providers used.
        tools: Tools and capabilities.
        system_architecture: Architecture description.
        intended_users: Who uses the system.
        deployment_environment: Where it runs.
        limitations: Known limitations.
        version: System version.

    Returns:
        JSON TechnicalDocumentation with draft sections.
    """
    sections: list[TechnicalDocSection] = []

    sections.append(
        TechnicalDocSection(
            title="1. System Purpose and Intended Use",
            content=f"System: {name}\nVersion: {version}\n\nPurpose: {description}\n\n"
            f"Intended Users: {intended_users or 'Not specified'}\n"
            f"Deployment Environment: {deployment_environment or 'Not specified'}",
            requires_review=True,
        )
    )

    sections.append(
        TechnicalDocSection(
            title="2. Architecture and Design",
            content=f"Architecture: {system_architecture or 'Not specified'}\n\n"
            f"Models/Providers: {', '.join(models) if models else 'Not specified'}\n"
            f"Tools/Capabilities: {', '.join(tools) if tools else 'Not specified'}",
            requires_review=True,
        )
    )

    sections.append(
        TechnicalDocSection(
            title="3. System Limitations and Known Risks",
            content=limitations or "Not specified. This section requires human review to document known limitations, edge cases, and risks.",
            requires_review=True,
        )
    )

    sections.append(
        TechnicalDocSection(
            title="4. Dependencies",
            content=f"Models: {', '.join(models) if models else 'Not specified'}\n"
            f"Tools: {', '.join(tools) if tools else 'Not specified'}",
            requires_review=True,
        )
    )

    sections.append(
        TechnicalDocSection(
            title="5. Version History",
            content=f"Version: {version}\n\n[Additional version history should be added by the development team.]",
            requires_review=True,
        )
    )

    doc = TechnicalDocumentation(
        system_name=name,
        sections=sections,
    )

    return _ok({
        "disclaimer": doc.disclaimer,
        "system_name": doc.system_name,
        "sections": [
            {"title": s.title, "content": s.content, "requires_review": s.requires_review}
            for s in doc.sections
        ],
    })


@mcp.tool()
def check_human_oversight(
    name: str = "",
    description: str = "",
    human_oversight_enabled: bool = False,
    approval_required_for: list[str] | None = None,
    override_capability: bool = False,
    stop_capability: bool = False,
    escalation_paths: bool = False,
    role_ownership: bool = False,
) -> str:
    """Evaluate whether an agent has adequate human-in-the-loop controls.

    Args:
        name: System name.
        description: What the system does.
        human_oversight_enabled: Whether human oversight is active.
        approval_required_for: List of actions requiring human approval.
        override_capability: Whether operators can override system outputs.
        stop_capability: Whether operators can stop/disable the system.
        escalation_paths: Whether escalation paths exist.
        role_ownership: Whether oversight roles are assigned.

    Returns:
        JSON evaluation with score, gaps, and recommendations.
    """
    total_points = 20
    earned = 0
    gaps: list[str] = []

    if human_oversight_enabled:
        earned += 4
    else:
        gaps.append("Human oversight is not enabled")

    if approval_required_for and len(approval_required_for) > 0:
        earned += 6
    else:
        gaps.append("No approval gates defined for consequential actions")

    if override_capability:
        earned += 4
    else:
        gaps.append("No override capability for system outputs")

    if stop_capability:
        earned += 3
    else:
        gaps.append("No stop/disable capability available to operators")

    if escalation_paths:
        earned += 2
    else:
        gaps.append("No escalation paths defined")

    if role_ownership:
        earned += 1
    else:
        gaps.append("No role ownership for oversight functions")

    score = int((earned / total_points) * 100) if total_points > 0 else 0
    status = "adequate" if score >= 75 else "needs_improvement" if score >= 50 else "insufficient"

    return _ok({
        "score": score,
        "status": status,
        "earned_points": earned,
        "max_points": total_points,
        "gaps": gaps,
        "recommendations": [
            "Enable human oversight with approval gates for consequential actions.",
            "Implement override and stop mechanisms accessible to designated operators.",
            "Define clear escalation paths and assign oversight roles.",
        ] if gaps else ["Human oversight controls appear adequate."],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def check_logging(
    name: str = "",
    logging_enabled: bool = False,
    io_logging: bool = False,
    retention_days: int = 0,
    failure_logging: bool = False,
    operator_logging: bool = False,
) -> str:
    """Evaluate whether the agent has sufficient logging for auditability.

    Args:
        name: System name.
        logging_enabled: Whether event logging is active.
        io_logging: Whether input/output traceability exists.
        retention_days: Log retention period in days.
        failure_logging: Whether failures/errors are logged.
        operator_logging: Whether operator actions are logged.

    Returns:
        JSON evaluation with score, gaps, and recommendations.
    """
    total_points = 20
    earned = 0
    gaps: list[str] = []

    if logging_enabled:
        earned += 6
    else:
        gaps.append("Event logging is not enabled")

    if io_logging:
        earned += 6
    else:
        gaps.append("Input/output traceability logging is missing")

    if retention_days >= 180:
        earned += 4
    elif retention_days > 0:
        earned += 2
        gaps.append(f"Log retention ({retention_days} days) is below the recommended 180 days")
    else:
        gaps.append("No log retention policy defined")

    if failure_logging:
        earned += 2
    else:
        gaps.append("Failure and error logging is not configured")

    if operator_logging:
        earned += 2
    else:
        gaps.append("Operator action logging is missing")

    score = int((earned / total_points) * 100) if total_points > 0 else 0
    status = "adequate" if score >= 75 else "needs_improvement" if score >= 50 else "insufficient"

    return _ok({
        "score": score,
        "status": status,
        "earned_points": earned,
        "max_points": total_points,
        "gaps": gaps,
        "recommendations": [
            "Enable structured JSON logging for all AI system events.",
            "Implement input/output traceability with timestamps.",
            "Set log retention to at least 180 days.",
            "Log failures, errors, and operator overrides.",
        ] if gaps else ["Logging controls appear adequate."],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def reassess(
    previous_assessment: str,
    changes: str,
) -> str:
    """Re-score an AI system after implementing improvements.

    Args:
        previous_assessment: Previous assessment JSON (the full assessment output).
        changes: JSON list of changes made, each with:
            - requirement_id: Rule ID that was addressed
            - evidence: { category, description, level }

    Returns:
        JSON with previous score, new score, delta, closed/remaining/new findings.
    """
    try:
        prev_data = json.loads(previous_assessment) if isinstance(previous_assessment, str) else previous_assessment
        changes_data = json.loads(changes) if isinstance(changes, str) else changes
    except json.JSONDecodeError as e:
        return _error(f"Invalid JSON: {e}")

    try:
        prev_assessment = FullAssessment(**prev_data)
    except Exception as e:
        return _error(f"Invalid previous assessment: {e}")

    from ai_consent.evaluator import reassess as _reassess
    try:
        result = _reassess(prev_assessment, changes_data)
    except Exception as e:
        return _error(f"Reassessment failed: {e}")

    return _ok({
        "previous_score": prev_assessment.score.overall_score,
        "current_score": result.score.overall_score,
        "score_delta": result.score.overall_score - prev_assessment.score.overall_score,
        "previous_status": prev_assessment.score.status.value,
        "current_status": result.score.status.value,
        "recommendations": [r.model_dump() for r in result.recommendations],
        "disclaimer": DISCLAIMER,
    })


@mcp.tool()
def assess_manifest(manifest_yaml: str) -> str:
    """Assess an AI agent from its ai-consent.yaml manifest content.

    Provide the YAML content as a string. The MCP will parse it, classify
    the system, score compliance readiness, and return a full assessment
    with findings and remediation.

    Args:
        manifest_yaml: Full ai-consent.yaml content as a string.

    Returns:
        JSON FullAssessment.
    """
    import yaml
    try:
        data = yaml.safe_load(manifest_yaml)
        if data is None:
            return _error("Empty manifest: could not parse YAML")
        manifest = AgentManifest(**data)
    except Exception as e:
        return _error(f"Failed to parse manifest: {e}")

    assessment = _assess_manifest(manifest)
    return _ok({
        "assessment_version": assessment.assessment_version,
        "ruleset": assessment.ruleset,
        "system": assessment.system.model_dump(),
        "risk": assessment.risk.model_dump(),
        "score": assessment.score.model_dump(),
        "findings": [f.model_dump() for f in assessment.findings],
        "recommendations": [r.model_dump() for r in assessment.recommendations],
        "remediation_plan": assessment.remediation_plan.model_dump() if assessment.remediation_plan else None,
        "missing_evidence": assessment.missing_evidence,
        "potential_score": assessment.potential_score,
        "disclaimer": assessment.disclaimer,
    })


if __name__ == "__main__":
    import os
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    if transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
    else:
        mcp.run(transport="stdio")