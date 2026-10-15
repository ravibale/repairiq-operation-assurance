# RepairIQ — Evidence-Linked Repair Operation Overlap (Prototype v0.1)

**Status:** experimental proof of concept; synthetic data and synthetic rules only. Not production-ready; not validated on insurer claims and not intended to automatically reject repair charges.

## What is the innovation being demonstrated?

RepairIQ's proposed product differentiator is an **evidence-preserving, repair-operation-level assurance method**: normalize different descriptions into a canonical operation, apply explicit compatibility checks and output reviewable findings that reference the exact source document and line numbers. This prototype isolates the **labour-operation overlap** part of that method.

Most important: **basic duplicate detection and rules are not novel by themselves**. The value proposition to test is reliable, traceable domain-specific reasoning across heterogeneous inputs, with a human reviewer and outcomes captured in later phases. This project is a minimal feasibility artefact, **not proof of global uniqueness, patentability, superior performance or savings**.

## Implemented scope

- Import one estimate revision per CSV; reject invalid or inconsistent rows.
- Normalize a **small synthetic** set of labour descriptions to operation codes.
- Apply two demonstrator checks:
  - `DUP-001`: repeated normalized operation on the same panel.
  - `OVL-002`: combined front bumper remove/refit alongside separately billed removal or refitting on the same panel.
- Return review-only findings with exact source line numbers, descriptions, a SHA-256 hash of the input file, ruleset version and a recommended evidence request.
- Explicitly abstain on unknown operation descriptions.
- Provide an illustrative potential exposure value **not equivalent to verified savings**.
- Automated unit tests and GitHub Actions configuration.

## Quick start (Python 3.11+, no dependencies)

```bash
python -m unittest discover -s tests -v
python -m repairiq examples/sample_estimate.csv --output example_report.json
```

Inspect `example_report.json` for source-line-linked findings. On the included example, the prototype identifies repeated headlamp replacement lines (4 and 5) and a potential bundled/separate bumper operation overlap (1–3). It abstains on line 6, whose description is unknown.

## Example result (shortened)

```json
{
  "document_id": "EXAMPLE-001",
  "taxonomy_version": "demo-taxonomy-0.1",
  "ruleset_version": "demo-rules-0.1",
  "findings": [
    {
      "rule_id": "DUP-001",
      "source_lines": [4, 5],
      "reviewer_decision": "PENDING_HUMAN_REVIEW"
    },
    {
      "rule_id": "OVL-002",
      "source_lines": [1, 2, 3],
      "reviewer_decision": "PENDING_HUMAN_REVIEW"
    }
  ]
}
```

## Repository structure

```text
repairiq/
  __init__.py
  __main__.py         # Command-line interface
  core.py             # Normalization, validation, rules and reporting
examples/
  sample_estimate.csv # Synthetic only
  sample_report.json  # Generated illustrative output
tests/
  test_core.py        # Automated regression tests
.github/workflows/
  tests.yml           # CI tests (when pushed to GitHub)
README.md
```

## Why source provenance matters

Every finding stores source line numbers, original descriptions and a file content hash. Rules and taxonomy have explicit versions so an auditor can investigate how a finding was generated. This is a simple first step toward RepairIQ's proposed canonical job vector, evidence pack and reviewer-outcome ledger (see project Annexes 1 and 3).

## Planned research and development — not yet implemented

1. Multi-format PDF/XLSX parsers and real source-page coordinates.
2. Wider repair-operation taxonomy with documented permission to use repair methods.
3. Vehicle, damage severity, repair-method compatibility conditions to reduce false alerts.
4. Evidence-backed benchmarking with controlled peer cohorts and uncertainty intervals.
5. Human review UI, signed decision events, approved outcomes and double-count-resistant savings ledger.
6. Controlled insurer-data evaluation, expert-labelled holdout tests, precision/recall and a comparison against a manual or incumbent baseline.
7. Access controls, customer tenant segregation, retention and production security review.

## Limitations and professional safeguards

- The two rules are invented solely to exercise code; they **do not** state that bumper or headlamp work is invalid in any particular real repair. Only an authorised expert may decide that after considering OEM repair methods, vehicle specifics and contract terms.
- There is **no AI/ML model implemented** here; the prototype deliberately starts with transparent deterministic checks.
- No insurer data, customer documents, licensed repair time standards or personal data are included.
- Any `estimated_exposure_gbp` is candidate investigation value and **must never be represented as realised cost savings**. Some findings may refer to overlapping charges.
- Input is restricted to a single document revision; supplementary-version reconciliation is future work.
- The prototype has no authentication, rate limiting or secure storage and should not be exposed as a public service or used on sensitive customer data.

## Suggested technical validation

Prepare a permissioned set of anonymised historical estimates. Have two qualified motor claims/repair assessors independently label duplicate and overlapping labour scenarios; adjudicate disagreements. Report precision, recall, false-positive rate, rule coverage, unmapped operation percentage, source-reference accuracy and reviewer effort vs a manual baseline. Publish the protocol and aggregate outcomes without exposing customer data.

## Licence

No licence is granted in this demonstration repository. Add an appropriate company-selected licence and contributor/IP assignment policy before public distribution.
