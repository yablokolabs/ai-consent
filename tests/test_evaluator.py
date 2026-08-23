"""Tests for the full assessment evaluator."""

import pytest
from ai_consent.evaluator import (
    _system_from_manifest,
    assess_manifest,
    assess_system,
)
from ai_consent.models import (
    AgentManifest,
    Evidence,
    EvidenceLevel,
    FullAssessment,
    SystemDescription,
)


class TestEvaluator:
    def test_assess_system_returns_full_assessment(self):
        system = SystemDescription(
            name="test-agent",
            description="A test AI agent for unit testing",
            industry="technology",
            deployment_region=["EU"],
        )
        assessment = assess_system(system)
        assert isinstance(assessment, FullAssessment)
        assert assessment.assessment_version == "1.0"
        assert assessment.ruleset == "EU-AI-ACT-2026"
        assert assessment.system.name == "test-agent"
        assert assessment.risk is not None
        assert assessment.score is not None
        assert 0 <= assessment.score.overall_score <= 100
        assert len(assessment.findings) > 0
        assert len(assessment.recommendations) > 0
        assert assessment.remediation_plan is not None
        assert 0 <= assessment.potential_score <= 100

    def test_assess_with_evidence_improves_score(self):
        system = SystemDescription(
            name="test-agent",
            description="Test agent",
            industry="technology",
        )
        no_evidence = assess_system(system)

        evidence = [
            Evidence(
                category="human_oversight",
                requirement_id="EUAI-HUMAN-001",
                description="Oversight implemented",
                level=EvidenceLevel.TECHNICALLY_EVIDENCED,
            ),
        ]
        with_evidence = assess_system(system, evidence_list=evidence)

        # Score should be higher with evidence
        assert with_evidence.score.overall_score >= no_evidence.score.overall_score

    def test_assess_manifest_from_dict(self):
        manifest = AgentManifest(
            system={"name": "test", "purpose": "Testing", "industry": "technology"},
            deployment={"regions": ["EU"]},
            security={"authentication": True, "authorization": True},
            logging={"enabled": True, "retention_days": 365},
            human_oversight={"enabled": True, "approval_required_for": ["action_x"]},
            data={"personal_data": False},
        )
        assessment = assess_manifest(manifest)
        assert isinstance(assessment, FullAssessment)
        assert assessment.system.name == "test"

    def test_disclaimer_present(self):
        system = SystemDescription(name="test", description="test", industry="tech")
        assessment = assess_system(system)
        assert "legal advice" in assessment.disclaimer.lower()
        assert "does not constitute" in assessment.disclaimer.lower()

    def test_missing_evidence_listed(self):
        system = SystemDescription(name="test", description="test", industry="tech")
        assessment = assess_system(system)
        assert len(assessment.missing_evidence) > 0

    def test_potential_score_not_lower_than_current(self):
        system = SystemDescription(name="test", description="test", industry="tech")
        assessment = assess_system(system)
        assert assessment.potential_score >= assessment.score.overall_score