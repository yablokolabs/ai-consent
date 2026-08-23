"""CLI for AI-Consent — scan, score, and report from the terminal.

Usage:
    ai-consent scan <manifest.yaml>
    ai-consent classify <manifest.yaml>
    ai-consent --help
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .evaluator import assess_manifest
from .models import AgentManifest, DIMENSION_NAMES


def _load_manifest(path: str) -> AgentManifest:
    """Load an ai-consent.yaml manifest file."""
    p = Path(path)
    if not p.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(p, encoding="utf-8") as f:
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)

    return AgentManifest(**data)


def _term_header() -> str:
    return "AI-CONSENT — EU AI Act Readiness"


def _score_bar(score: int, width: int = 20) -> str:
    """Return a terminal bar for a score."""
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _status_label(status: str) -> str:
    labels = {
        "strong_readiness": "STRONG READINESS",
        "good_remediation_recommended": "GOOD (needs fixes)",
        "significant_gaps": "SIGNIFICANT GAPS",
        "high_regulatory_risk": "HIGH REGULATORY RISK",
        "critical_gaps": "CRITICAL GAPS",
    }
    return labels.get(status, status.upper())


def cmd_scan(args: argparse.Namespace) -> None:
    """Run a full scan on a manifest."""
    manifest = _load_manifest(args.manifest)
    assessment = assess_manifest(manifest)

    print(f"\n╭{'─' * 42}╮")
    print(f"│       {_term_header():^38}       │")
    print(f"╰{'─' * 42}╯")
    print()

    # Risk classification
    risk_label = assessment.risk.classification.value.upper().replace("_", " ")
    print(f"  Risk Class       {risk_label}")
    print(f"  Readiness         {assessment.score.overall_score} / 100")
    print(f"  Status            {_status_label(assessment.score.status.value)}")
    print()

    # Dimension scores
    for dim in assessment.score.dimensions:
        name = DIMENSION_NAMES.get(dim.dimension, dim.dimension)
        if dim.total == 0:
            print(f"  {name:<24} N/A (no applicable rules)")
        else:
            bar = _score_bar(dim.score)
            print(f"  {name:<24} {dim.score:>2} {bar}")

    print()
    critical_count = sum(
        1 for f in assessment.findings if f.severity.value == "critical" and f.status != "satisfied"
    )
    warning_count = sum(
        1 for f in assessment.findings if f.severity.value in ("high", "medium") and f.status != "satisfied"
    )
    passed_count = sum(1 for f in assessment.findings if f.status == "satisfied")

    print(f"  Critical findings: {critical_count}")
    print(f"  Warnings:          {warning_count}")
    print(f"  Passed controls:   {passed_count}")
    print()
    print(f"  Potential after fixes: {assessment.potential_score} / 100")
    print()

    # Top recommendations
    if assessment.recommendations:
        print("Top recommendation:")
        top = assessment.recommendations[0]
        print(f"  → {top.recommendation}")
        print()

    # Verbose: show all findings
    if args.verbose:
        print("\n── Findings ──")
        for f in assessment.findings:
            if f.status != "satisfied":
                icon = "✗" if f.status == "unsatisfied" else "⚠"
                print(f"  {icon} [{f.severity.value.upper()}] {f.requirement_id}: {f.title}")
                print(f"     {f.reason}")
        print()

    # JSON output
    if args.json:
        print(json.dumps(assessment.model_dump(), indent=2, default=str))


def cmd_classify(args: argparse.Namespace) -> None:
    """Run just the classifier on a manifest."""
    from .classifier import classify

    manifest = _load_manifest(args.manifest)
    from .evaluator import _system_from_manifest
    system = _system_from_manifest(manifest)
    result = classify(system)

    print(f"Classification: {result.classification.value}")
    print(f"Confidence:     {result.confidence:.0%}")
    print()
    if result.reasons:
        print("Reasons:")
        for r in result.reasons:
            print(f"  • {r}")
    if result.potential_articles:
        print(f"\nRelevant articles: {', '.join(result.potential_articles)}")
    if result.missing_information:
        print("\nMissing information:")
        for m in result.missing_information:
            print(f"  • {m}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ai-consent",
        description="EU AI Act readiness scoring for AI agents. Scan. Score. Fix. Re-check.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan a manifest for EU AI Act readiness")
    scan_parser.add_argument("manifest", help="Path to ai-consent.yaml manifest")
    scan_parser.add_argument("--json", action="store_true", help="Output JSON")
    scan_parser.add_argument("--verbose", "-v", action="store_true", help="Show all findings")

    # classify
    classify_parser = subparsers.add_parser("classify", help="Classify an AI system's risk level")
    classify_parser.add_argument("manifest", help="Path to ai-consent.yaml manifest")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "classify":
        cmd_classify(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()