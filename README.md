# AI-Consent

**Know whether your AI is ready for the EU AI Act — before regulators do.**

```
Agent → Scan → Score → Fix → Re-check
```

AI-Consent is an open-source MCP server that assesses AI agents and systems against EU AI Act requirements. It produces deterministic compliance-readiness scores, identifies gaps, and generates prioritized remediation plans — all without requiring API keys or LLM calls.

> **AI-Consent provides automated EU AI Act readiness assessments and engineering guidance. It does not constitute legal advice, regulatory certification, conformity assessment, or a guarantee of compliance.**

---

## Quick Example

```text
$ ai-consent scan examples/recruitment-agent.yaml

╭──────────────────────────────────────────╮
│       AI-CONSENT — EU AI ACT SCAN       │
╰──────────────────────────────────────────╯

  Risk Class       HIGH RISK
  Readiness         63 / 100
  Status            SIGNIFICANT GAPS

  Risk Management        72 ██████████████░░░░░░
  Data Governance        68 █████████████░░░░░░░
  Technical Docs         80 ████████████████░░░░
  Logging                50 ██████████░░░░░░░░░░
  Human Oversight        35 ███████░░░░░░░░░░░░░
  Accuracy               74 ██████████████░░░░░░
  Cybersecurity          86 █████████████████░░░
  Transparency           90 ██████████████████░░
  Governance             58 ███████████░░░░░░░░░

  Critical findings: 2
  Warnings:          4
  Passed controls:   21

  Potential after fixes: 91 / 100

Top recommendation:
  Add mandatory human approval before candidate rejection.
```

---

## What is AI-Consent?

AI-Consent evaluates AI systems against EU AI Act (Regulation 2024/1689) requirements across nine compliance dimensions:

| Dimension | What it checks |
|-----------|---------------|
| **Risk Management** | Risk assessment, failure modes, mitigation, periodic review, misuse analysis |
| **Data Governance** | Data provenance, quality, bias testing, minimisation, retention |
| **Technical Documentation** | System purpose, architecture, model details, limitations, versioning |
| **Logging & Traceability** | Action logs, input/output traceability, timestamps, retention |
| **Human Oversight** | Approval gates, override capability, escalation paths, stop/disable |
| **Accuracy & Robustness** | Evaluation metrics, regression tests, hallucination testing, fallbacks |
| **Cybersecurity** | Auth, authorization, secrets management, prompt injection, tool sandboxing |
| **Transparency** | AI disclosure, explainability, content labeling, deepfake handling |
| **Governance** | Accountable owner, AI inventory, change management, incident response |

---

## Why It Exists

The EU AI Act entered into force on August 1, 2024 and key obligations become applicable through 2026-2027. Organizations deploying AI systems in or affecting the EU need to assess their readiness.

AI-Consent bridges the gap between legal text and engineering practice:

- **Agents and dev tools** can programmatically check readiness before production
- **Compliance teams** get structured evidence-based assessments
- **Enterprises** can scan entire AI portfolios through MCP

---

## Quick Start

### Install

```bash
git clone https://github.com/yablokolabs/ai-consent.git
cd ai-consent
pip install .
```

### Scan an agent

```bash
ai-consent scan examples/recruitment-agent.yaml
```

### Classify an agent's risk

```bash
ai-consent classify examples/logistics-agent.yaml
```

### JSON output

```bash
ai-consent scan examples/recruitment-agent.yaml --json
```

---

## MCP Installation

### MCPize (Recommended)

```bash
mcpize install ai-consent
```

Or add to your MCP client config:

```json
{
  "mcpServers": {
    "ai-consent": {
      "url": "https://router.mcpize.com/sse/ai-consent"
    }
  }
}
```

### Local stdio

```bash
pip install .[mcp]
python mcp-server/server.py
```

MCP client config (stdio):

```json
{
  "mcpServers": {
    "ai-consent": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "/path/to/ai-consent"
    }
  }
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `classify_ai_system` | Determine EU AI Act risk category from system description |
| `assess_agent` | Full readiness assessment: classification, score, findings, remediation |
| `score_compliance` | Numeric 0-100 score with per-dimension breakdown |
| `check_requirement` | Check a single requirement against evidence |
| `suggest_improvements` | Prioritized recommendations to raise compliance score |
| `generate_remediation_plan` | Three-tier plan: fix-first, fix-next, nice-to-have |
| `generate_risk_register` | Structured AI risk register (JSON) |
| `generate_technical_documentation` | Draft technical docs (requires human review) |
| `check_human_oversight` | Evaluate human-in-the-loop controls |
| `check_logging` | Evaluate auditability and traceability |
| `reassess` | Re-score after improvements (shows delta) |
| `assess_manifest` | Assess from ai-consent.yaml content string |

---

## Agent Manifest

Place an `ai-consent.yaml` in your AI agent repository:

```yaml
system:
  name: recruitment-agent
  version: 1.2.0
  purpose: Candidate screening assistance
  industry: recruitment

deployment:
  regions:
    - EU

models:
  - provider: anthropic
    model: claude-sonnet-4-20250514

data:
  personal_data: true
  sensitive_data: false
  data_lineage_documented: true

human_oversight:
  enabled: true
  approval_required_for:
    - reject_candidate

logging:
  enabled: true
  retention_days: 365

security:
  authentication: true
  authorization: true
  secrets_manager: true
```

Then scan it:

```bash
ai-consent scan ai-consent.yaml
```

---

## Scoring Methodology

### Formula

The overall score (0-100) is a weighted average across 9 dimensions:

```
overall = Σ(dimension_score × dimension_weight) / Σ(dimension_weight)
```

Where:
- **dimension_weight** = sum of all rule weights in that dimension applicable to the system's risk classification
- **dimension_score** = Σ(rule_points_earned) / Σ(rule_max_points) × 100

### Evidence Confidence

Scores are weighted by evidence quality:

| Evidence Level | Confidence | Description |
|---------------|-----------|-------------|
| Claimed only | 0.3 | Statement without supporting evidence |
| Documented | 0.6 | Written policy or documentation exists |
| Technical evidence | 0.85 | Implementation files, configs, test results |
| Independently verified | 1.0 | Third-party audit or certification |

A claim of "we have human oversight" without evidence earns 30% of available points. Technical evidence (implementation code, configuration, test results) earns 85%.

### Status Bands

| Score | Status |
|-------|--------|
| 90-100 | Strong readiness |
| 75-89 | Good, remediation recommended |
| 50-74 | Significant compliance gaps |
| 25-49 | High regulatory risk |
| 0-24 | Critical gaps / unsuitable for production |

> A score of 100 means "no gaps detected by this ruleset" — not "legally certified compliant."

---

## Example Assessments

### Recruitment AI → HIGH RISK

```text
Risk Class: HIGH RISK | Score: 63/100
Critical: No approval gate for candidate rejection, no risk management system
Potential: 91/100 after fixing critical blockers
```

### Customer Support Chatbot → LIMITED RISK

```text
Risk Class: LIMITED RISK | Score: 58/100
Key gaps: No AI disclosure, insufficient logging, no human override
```

### Healthcare Decision Support → HIGH RISK

```text
Risk Class: HIGH RISK | Score: 72/100
Stronger baseline (better documentation, human oversight, security)
Gaps in accuracy testing and data governance
```

### Logistics Routing → MINIMAL RISK

```text
Risk Class: MINIMAL RISK | Score: 55/100
No personal data, no consequential decisions — lower regulatory burden
Still needs basic logging and governance
```

### Internal Summarizer → MINIMAL RISK

```text
Risk Class: MINIMAL RISK | Score: 32/100
Lowest risk classification but minimal controls in place
Even low-risk systems benefit from basic governance
```

---

## Rulesets

Rules are versioned, data-driven JSON files in `rules/`.

Current ruleset: `rules/eu_ai_act_2026.json` (1.0.0)

Each rule:

```json
{
  "id": "EUAI-HUMAN-OVERSIGHT-001",
  "article": "Article 14",
  "category": "human_oversight",
  "title": "Human oversight capability",
  "description": "High-risk AI systems shall be designed so they can be effectively overseen...",
  "applies_to": ["high_risk"],
  "severity": "critical",
  "weight": 10,
  "source": "https://artificialintelligenceact.eu/article/14/",
  "effective_date": "2026-08-02",
  "evidence_guidance": "Human oversight implementation design, HMI tools, oversight procedures."
}
```

Rules are validated against `rules/schema.json`.

---

## Architecture

```text
ai-consent/
├── src/ai_consent/          # Core library (framework-agnostic)
│   ├── models.py            # Pydantic models
│   ├── rules.py             # Ruleset loader
│   ├── classifier.py        # Risk classifier (deterministic)
│   ├── scorer.py            # Scoring engine
│   ├── evaluator.py         # Full assessment orchestrator
│   ├── remediation.py       # Remediation engine
│   └── cli.py               # CLI interface
│
├── mcp-server/              # MCP interface
│   └── server.py            # FastMCP server (12 tools)
│
├── rules/                   # Versioned regulatory rulesets
│   ├── eu_ai_act_2026.json  # EU AI Act policy pack
│   └── schema.json          # Ruleset JSON schema
│
├── examples/                # Example agent manifests
├── tests/                   # Test suite
└── Dockerfile               # Container build
```

**Key principle:** Core compliance logic is independent of MCP. MCP is an interface. The scoring engine is also usable as a Python library and CLI.

### Future Policy Packs

```text
AI-Consent Core
      │
      ├── EU AI Act Policy Pack          (v0.1.0 — now)
      ├── GDPR Policy Pack               (future)
      ├── ISO/IEC 42001 Policy Pack      (future)
      ├── NIST AI RMF Policy Pack        (future)
      └── Enterprise Custom Policy Pack  (future)
```

---

## MCPize Deployment

```bash
mcpize analyze
mcpize doctor
mcpize deploy
```

AI-Consent supports both local stdio and cloud MCPize execution.

---

## Limitations

1. **Not legal advice.** AI-Consent is an engineering tool, not a law firm. Scores reflect readiness against a ruleset interpretation, not legal conformity.
2. **Deterministic but interpretative.** The classifier uses pattern matching, not legal reasoning. Edge cases require human review.
3. **Evidence quality is self-reported.** Until evidence is independently verified, scores depend on the accuracy of self-reported evidence levels.
4. **Ruleset lag.** Regulatory rulesets are versioned but may lag behind official guidance updates.
5. **EU AI Act only.** Currently only covers the EU AI Act. Other frameworks (GDPR, ISO 42001, NIST RMF) are future work.
6. **No external LLM required.** The core scoring engine is fully deterministic and requires no API keys. Optional LLM enrichment may be added later.

---

## Legal Disclaimer

> AI-Consent provides automated EU AI Act readiness assessments and engineering guidance. It does **not** constitute legal advice, regulatory certification, conformity assessment, or a guarantee of compliance. Scores and classifications are engineering readiness indicators, not legal determinations. Organizations should consult qualified legal professionals for regulatory compliance decisions. Never deploy a system solely on the basis of an AI-Consent score.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Yabloko Labs](https://github.com/yablokolabs).