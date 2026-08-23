"""Rules engine — loads and queries versioned regulatory rulesets.

Conceptually, AI-Consent Core is policy-pack-agnostic.
The EU AI Act is the first policy pack; others follow later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


class Ruleset:
    """A loaded, queryable ruleset."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._rules: list[dict[str, Any]] = data.get("rules", [])
        self._by_id: dict[str, dict[str, Any]] = {r["id"]: r for r in self._rules}
        self._by_category: dict[str, list[dict[str, Any]]] = {}
        for r in self._rules:
            cat = r["category"]
            self._by_category.setdefault(cat, []).append(r)

    @property
    def ruleset_id(self) -> str:
        return self._data["ruleset_id"]

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def version(self) -> str:
        return self._data["version"]

    @property
    def rules(self) -> list[dict[str, Any]]:
        return list(self._rules)

    @property
    def categories(self) -> list[str]:
        return list(self._by_category.keys())

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Return a single rule by id."""
        return self._by_id.get(rule_id)

    def rules_for_category(self, category: str) -> list[dict[str, Any]]:
        """Return all rules in a category."""
        return list(self._by_category.get(category, []))

    def rules_applicable_to(self, risk_level: str) -> list[dict[str, Any]]:
        """Return rules that apply to a given risk level.

        'all' rules always apply. 'high_risk' rules apply to high_risk and prohibited.
        'limited_risk' rules apply to limited_risk and high_risk and prohibited.
        """
        levels = {risk_level}
        if risk_level in ("high_risk", "prohibited"):
            levels |= {"high_risk", "all"}
        if risk_level == "prohibited":
            levels.add("prohibited")
        if risk_level in ("limited_risk", "high_risk", "prohibited"):
            levels.add("limited_risk")
        levels.add("all")

        return [r for r in self._rules if any(l in levels for l in r["applies_to"])]

    def total_weight_for_category(self, category: str, risk_level: str) -> int:
        """Total weight of all applicable rules in a category."""
        applicable = [
            r
            for r in self.rules_for_category(category)
            if any(l in {risk_level, "all"}
                   or (risk_level in ("high_risk", "prohibited") and l in ("high_risk", "all"))
                   or (risk_level == "prohibited" and l == "prohibited")
                   or l == "all"
                   for l in r["applies_to"])
        ]
        return sum(r["weight"] for r in applicable)


def load_ruleset(path: str | Path | None = None) -> Ruleset:
    """Load the default EU AI Act ruleset (or a custom one).

    Args:
        path: Optional path to a JSON ruleset file. If None, loads the built-in
              EU AI Act 2026 ruleset.

    Returns:
        Loaded Ruleset instance.
    """
    if path is None:
        path = _pkg_dir().parent.parent / "rules" / "eu_ai_act_2026.json"
    else:
        path = Path(path)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return Ruleset(data)


def default_ruleset() -> Ruleset:
    """Return the built-in EU AI Act 2026 ruleset."""
    return load_ruleset()