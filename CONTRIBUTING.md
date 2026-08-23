# Contributing to AI-Consent

Thank you for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/yablokolabs/ai-consent.git
cd ai-consent
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

- `src/ai_consent/` — Core library (framework-agnostic)
- `mcp-server/` — MCP interface (FastMCP)
- `rules/` — Versioned regulatory rulesets (JSON)
- `examples/` — Example agent manifests
- `tests/` — Test suite

## Adding a New Ruleset

1. Create a new JSON file in `rules/` following `schema.json`
2. Rules are automatically loadable via `load_ruleset(path)`

## Code Style

- Typed Python with Pydantic models for all inputs/outputs
- Keep core logic framework-agnostic (no MCP imports in `src/ai_consent/`)
- Deterministic scoring — no LLM calls required
- Tests for all new features

## License

By contributing, you agree that your contributions will be licensed under the MIT License.