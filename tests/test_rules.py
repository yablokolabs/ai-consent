"""Tests for the rules engine."""

import pytest
from ai_consent.rules import default_ruleset, load_ruleset, Ruleset


class TestRuleset:
    def test_loads_default_ruleset(self):
        ruleset = default_ruleset()
        assert isinstance(ruleset, Ruleset)
        assert ruleset.ruleset_id == "EU-AI-ACT-2026"

    def test_has_rules(self):
        ruleset = default_ruleset()
        assert len(ruleset.rules) > 10
        assert len(ruleset.rules) >= 40  # We have 40+ rules

    def test_has_categories(self):
        ruleset = default_ruleset()
        categories = ruleset.categories
        assert "risk_management" in categories
        assert "data_governance" in categories
        assert "human_oversight" in categories
        assert "cybersecurity" in categories
        assert len(categories) == 9

    def test_get_rule(self):
        ruleset = default_ruleset()
        rule = ruleset.get_rule("EUAI-HUMAN-001")
        assert rule is not None
        assert "Human oversight" in rule["title"]
        assert rule["article"] == "Article 14"
        assert rule["severity"] == "critical"

    def test_get_nonexistent_rule(self):
        ruleset = default_ruleset()
        assert ruleset.get_rule("NONEXISTENT") is None

    def test_rules_for_category(self):
        ruleset = default_ruleset()
        ho_rules = ruleset.rules_for_category("human_oversight")
        assert len(ho_rules) >= 3  # At least 3 human oversight rules

    def test_rules_applicable_to_high_risk(self):
        ruleset = default_ruleset()
        applicable = ruleset.rules_applicable_to("high_risk")
        # High-risk should have many applicable rules
        assert len(applicable) > 20

    def test_rules_applicable_to_minimal_risk(self):
        ruleset = default_ruleset()
        applicable = ruleset.rules_applicable_to("minimal_risk")
        # Minimal risk has fewer rules (mostly 'all' rules)
        assert len(applicable) > 0
        assert len(applicable) < len(ruleset.rules_applicable_to("high_risk"))

    def test_all_rules_have_required_fields(self):
        ruleset = default_ruleset()
        for rule in ruleset.rules:
            assert "id" in rule
            assert "article" in rule
            assert "category" in rule
            assert "title" in rule
            assert "description" in rule
            assert "applies_to" in rule
            assert "severity" in rule
            assert "weight" in rule

    def test_weights_are_positive(self):
        ruleset = default_ruleset()
        for rule in ruleset.rules:
            assert rule["weight"] > 0
            assert rule["weight"] <= 100

    def test_severity_values_valid(self):
        ruleset = default_ruleset()
        valid = {"critical", "high", "medium", "low"}
        for rule in ruleset.rules:
            assert rule["severity"] in valid

    def test_categories_valid(self):
        ruleset = default_ruleset()
        valid_cats = {
            "risk_management", "data_governance", "technical_documentation",
            "logging_traceability", "human_oversight", "accuracy_robustness",
            "cybersecurity", "transparency", "governance",
        }
        for rule in ruleset.rules:
            assert rule["category"] in valid_cats


class TestRulesetLoading:
    def test_can_load_custom_path(self):
        import tempfile, json, os
        rules_data = {
            "ruleset_id": "TEST",
            "name": "Test",
            "version": "1.0.0",
            "effective_date": "2026-01-01",
            "jurisdiction": "EU",
            "rules": [
                {
                    "id": "TEST-001",
                    "article": "Test Article",
                    "category": "governance",
                    "title": "Test Rule",
                    "description": "A test rule",
                    "applies_to": ["all"],
                    "severity": "low",
                    "weight": 5,
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules_data, f)
            path = f.name

        try:
            ruleset = load_ruleset(path)
            assert ruleset.ruleset_id == "TEST"
            assert len(ruleset.rules) == 1
            assert ruleset.get_rule("TEST-001") is not None
        finally:
            os.unlink(path)