"""Tests for the EU AI Act risk classifier."""

import pytest
from ai_consent.classifier import classify
from ai_consent.models import (
    ClassificationResult,
    RiskClassification,
    SystemDescription,
)


def _sys(name: str = "test", description: str = "", industry: str = "",
         decisions: list[str] | None = None, data_types: list[str] | None = None,
         deployment: list[str] | None = None, personal_data: bool = False,
         sensitive_data: bool = False) -> SystemDescription:
    return SystemDescription(
        name=name,
        description=description,
        industry=industry,
        decisions=decisions or [],
        data_types=data_types or [],
        deployment_region=deployment or [],
        personal_data=personal_data,
        sensitive_data=sensitive_data,
    )


class TestClassifier:
    def test_recruitment_is_high_risk(self):
        """Recruitment AI should be classified as high-risk."""
        system = _sys(
            name="recruitment-bot",
            description="Screens job candidates and ranks applications",
            industry="recruitment",
            decisions=["candidate screening", "job application filtering"],
            data_types=["personal_data", "employment_history"],
            deployment=["EU"],
            personal_data=True,
        )
        result = classify(system)
        assert result.classification == RiskClassification.HIGH_RISK
        assert result.confidence >= 0.7

    def test_healthcare_is_high_risk(self):
        """Healthcare decision support should be classified as high-risk."""
        system = _sys(
            name="clinical-ai",
            description="Assists with diagnosis and treatment recommendations",
            industry="healthcare",
            decisions=["diagnosis", "treatment recommendation"],
            data_types=["personal_data", "sensitive_health_data"],
            deployment=["EU"],
            personal_data=True,
            sensitive_data=True,
        )
        result = classify(system)
        assert result.classification == RiskClassification.HIGH_RISK

    def test_chatbot_is_limited_risk(self):
        """Customer support chatbot should not be automatically high-risk."""
        system = _sys(
            name="support-bot",
            description="Answers customer questions and provides order status",
            industry="ecommerce",
            decisions=["respond to queries", "check order status"],
            deployment=["EU"],
            personal_data=True,
        )
        result = classify(system)
        # Should be limited risk (transparency) or minimal, NOT high-risk
        assert result.classification in (
            RiskClassification.LIMITED_RISK,
            RiskClassification.MINIMAL_RISK,
            RiskClassification.UNCERTAIN,
        )
        # Must not be high_risk or prohibited
        assert result.classification not in (
            RiskClassification.HIGH_RISK,
            RiskClassification.PROHIBITED,
        )

    def test_logistics_not_automatically_high_risk(self):
        """Logistics routing should not be falsely classified as high-risk."""
        system = _sys(
            name="logistics-router",
            description="Optimizes delivery routes for warehouse logistics",
            industry="logistics",
            decisions=["route optimization", "delivery scheduling"],
            deployment=["EU"],
            personal_data=False,
        )
        result = classify(system)
        # Should NOT be high-risk just because it uses AI
        assert result.classification not in (
            RiskClassification.HIGH_RISK,
            RiskClassification.PROHIBITED,
        )

    def test_insufficient_info_returns_uncertain(self):
        """Empty or minimal description should return uncertain."""
        system = _sys(
            name="mystery-agent",
            description="",
            industry="",
        )
        result = classify(system)
        assert result.classification == RiskClassification.UNCERTAIN
        assert result.confidence < 0.5
        assert len(result.missing_information) > 0

    def test_internal_summarizer_is_minimal_or_uncertain(self):
        """Internal document summarizer should not be classified as high-risk."""
        system = _sys(
            name="note-summarizer",
            description="Summarizes internal meeting notes for team reference",
            industry="technology",
            decisions=["summarize text"],
            deployment=["EU"],
            personal_data=False,
        )
        result = classify(system)
        assert result.classification in (
            RiskClassification.MINIMAL_RISK,
            RiskClassification.UNCERTAIN,
        )
        assert result.classification not in (
            RiskClassification.HIGH_RISK,
            RiskClassification.PROHIBITED,
        )

    def test_classification_includes_reasons(self):
        """Classification result should include reasons."""
        system = _sys(
            name="recruitment-bot",
            description="Screens job candidates",
            industry="recruitment",
            decisions=["candidate screening"],
            deployment=["EU"],
            personal_data=True,
        )
        result = classify(system)
        assert len(result.reasons) > 0

    def test_prohibited_patterns_detected(self):
        """Systems with social scoring patterns should be flagged as prohibited."""
        system = _sys(
            name="social-scorer",
            description="Social scoring system that evaluates citizen trustworthiness",
            industry="government",
            decisions=["score", "rate", "classify"],
            deployment=["EU"],
        )
        result = classify(system)
        assert result.classification == RiskClassification.PROHIBITED


class TestClassifierOutput:
    def test_result_has_required_fields(self):
        result = classify(_sys(description="test system", industry="tech"))
        assert isinstance(result.classification, RiskClassification)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reasons, list)
        assert isinstance(result.potential_articles, list)
        assert isinstance(result.missing_information, list)

    def test_serializable(self):
        result = classify(_sys(description="test", industry="tech"))
        data = result.model_dump()
        assert "classification" in data
        assert "confidence" in data
        assert isinstance(data["classification"], str)