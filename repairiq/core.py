"""Deterministic proof-of-concept for evidence-linked repair-operation overlap.

This is a demonstrator, NOT a repair method authority or production insurer decision engine.
Only synthetic demonstration rules are included. Flags require expert adjudication.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import csv
import json
from pathlib import Path
from typing import Any

TAXONOMY_VERSION = "demo-taxonomy-0.1"
RULESET_VERSION = "demo-rules-0.1"

# These are illustrative categories, not licensed OEM repair-method rules.
OPERATION_ALIASES = {
    "remove front bumper": "FRONT_BUMPER_REMOVE",
    "front bumper removal": "FRONT_BUMPER_REMOVE",
    "r&i front bumper": "FRONT_BUMPER_REMOVE",
    "refit front bumper": "FRONT_BUMPER_REFIT",
    "reinstall front bumper": "FRONT_BUMPER_REFIT",
    "front bumper refit": "FRONT_BUMPER_REFIT",
    "remove and refit front bumper": "FRONT_BUMPER_RI",
    "r&r front bumper": "FRONT_BUMPER_RI",
    "replace front headlamp": "FRONT_HEADLAMP_REPLACE",
    "front headlamp replacement": "FRONT_HEADLAMP_REPLACE",
    "paint front bumper": "FRONT_BUMPER_PAINT",
}

@dataclass(frozen=True)
class Line:
    source_file: str
    source_hash: str
    document_id: str
    revision: int
    line_number: int
    vehicle_id: str
    panel: str
    original_description: str
    canonical_operation: str | None
    labour_hours: Decimal
    hourly_rate_gbp: Decimal

    @property
    def labour_value_gbp(self) -> Decimal:
        return self.labour_hours * self.hourly_rate_gbp

@dataclass(frozen=True)
class Finding:
    finding_id: str
    rule_id: str
    rule_version: str
    severity: str
    status: str
    explanation: str
    document_id: str
    vehicle_id: str
    source_lines: tuple[int, ...]
    source_descriptions: tuple[str, ...]
    source_sha256: str
    estimated_exposure_gbp: Decimal | None
    required_evidence: str
    reviewer_decision: str = "PENDING_HUMAN_REVIEW"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_lines"] = list(self.source_lines)
        result["source_descriptions"] = list(self.source_descriptions)
        result["estimated_exposure_gbp"] = (str(self.estimated_exposure_gbp) if self.estimated_exposure_gbp is not None else None)
        return result

def _money(value: str, field: str, row: int) -> Decimal:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError) as error:
        raise ValueError(f"Row {row}: invalid {field}") from error
    if not number.is_finite() or number < 0:
        raise ValueError(f"Row {row}: {field} must be a finite non-negative number")
    return number

def load_estimate(path: str | Path) -> list[Line]:
    path = Path(path)
    raw = path.read_bytes()
    digest = sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig")
    from io import StringIO
    reader = csv.DictReader(StringIO(text))
    required = {"document_id", "revision", "vehicle_id", "panel", "description", "labour_hours", "hourly_rate_gbp"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f"Required CSV columns: {', '.join(sorted(required))}")
    lines: list[Line] = []
    identity = None
    seen = set()
    for index, row in enumerate(reader, start=2):
        if not all(row.get(k, "").strip() for k in required):
            raise ValueError(f"Row {index}: missing required field")
        try:
            revision = int(row["revision"])
        except ValueError as error:
            raise ValueError(f"Row {index}: revision must be an integer") from error
        if revision < 1:
            raise ValueError(f"Row {index}: revision must be positive")
        doc_identity = (row["document_id"].strip(), revision, row["vehicle_id"].strip())
        if identity is not None and identity != doc_identity:
            raise ValueError("Input must contain a single document, revision and vehicle; analyse revisions separately")
        identity = doc_identity
        explicit_line = row.get("line_number", "").strip()
        try:
            line_number = int(explicit_line) if explicit_line else index - 1
        except ValueError as error:
            raise ValueError(f"Row {index}: invalid line_number") from error
        if line_number <= 0 or line_number in seen:
            raise ValueError(f"Row {index}: line_number must be unique and positive")
        seen.add(line_number)
        description = row["description"].strip()
        key = " ".join(description.lower().split())
        lines.append(Line(
            source_file=path.name, source_hash=digest, document_id=doc_identity[0],
            revision=revision, line_number=line_number, vehicle_id=doc_identity[2],
            panel=row["panel"].strip().lower(), original_description=description,
            canonical_operation=OPERATION_ALIASES.get(key),
            labour_hours=_money(row["labour_hours"], "labour_hours", index),
            hourly_rate_gbp=_money(row["hourly_rate_gbp"], "hourly_rate_gbp", index),
        ))
    if not lines:
        raise ValueError("CSV has no repair lines")
    return lines

def analyse(lines: list[Line]) -> list[Finding]:
    """Generate REVIEW-ONLY findings from narrow, disclosed demonstration rules.

    Rule DUP-001: exact same known operation within same panel and document.
    Rule OVL-002: separate bumper removal/refit alongside bundled bumper R&I.
    Unknown descriptions are not automatically judged; this is a deliberate abstention.
    """
    if not lines:
        return []
    findings: list[Finding] = []
    by_operation: dict[tuple[str, str], list[Line]] = {}
    for line in lines:
        if line.canonical_operation is not None:
            by_operation.setdefault((line.panel, line.canonical_operation), []).append(line)

    def emit(rule: str, selected: list[Line], explanation: str, evidence: str, exposure: Decimal | None):
        selected = sorted(selected, key=lambda x: x.line_number)
        stable = f"{lines[0].document_id}:{lines[0].revision}:{rule}:{','.join(str(x.line_number) for x in selected)}"
        finding_id = sha256(stable.encode()).hexdigest()[:12]
        findings.append(Finding(
            finding_id=finding_id, rule_id=rule, rule_version=RULESET_VERSION,
            severity="REVIEW", status="POTENTIAL_OVERLAP_NOT_CONFIRMED", explanation=explanation,
            document_id=lines[0].document_id, vehicle_id=lines[0].vehicle_id,
            source_lines=tuple(x.line_number for x in selected),
            source_descriptions=tuple(x.original_description for x in selected),
            source_sha256=lines[0].source_hash,
            estimated_exposure_gbp=exposure, required_evidence=evidence,
        ))

    for (panel, operation), matches in sorted(by_operation.items()):
        if len(matches) > 1:
            # Conservative exposure: the value of the cheaper extra operation is under review,
            # NOT verified savings or proof that the charge is invalid.
            exposure = min(x.labour_value_gbp for x in matches)
            emit("DUP-001", matches, f"Same canonical operation {operation} occurs multiple times on {panel}. Verify separate legitimate work before challenging.",
                 "OEM repair method, operation breakdown and confirmation whether charges describe distinct work.", exposure)

    groups: dict[str, dict[str, list[Line]]] = {}
    for (panel, operation), matches in by_operation.items():
        groups.setdefault(panel, {})[operation] = matches
    for panel, operations in sorted(groups.items()):
        bundled = operations.get("FRONT_BUMPER_RI", [])
        separate = operations.get("FRONT_BUMPER_REMOVE", []) + operations.get("FRONT_BUMPER_REFIT", [])
        if bundled and separate:
            selected = bundled + separate
            exposure = sum((x.labour_value_gbp for x in separate), Decimal("0"))
            emit("OVL-002", selected,
                 "Bundled front bumper remove-and-refit is billed alongside one or more separate remove/refit operations; scope may overlap.",
                 "OEM procedure, insurer-approved estimate logic and itemised explanation of any distinct additional work.", exposure)

    return sorted(findings, key=lambda finding: (finding.rule_id, finding.source_lines))

def create_report(path: str | Path) -> dict[str, Any]:
    lines = load_estimate(path)
    findings = analyse(lines)
    unknown = [x.line_number for x in lines if x.canonical_operation is None]
    return {
        "prototype_status": "EXPERIMENTAL - synthetic rules, no live validation",
        "decision_policy": "HUMAN_REVIEW_REQUIRED - flags are not invoices to be rejected",
        "document_id": lines[0].document_id,
        "revision": lines[0].revision,
        "vehicle_id": lines[0].vehicle_id,
        "source_file": lines[0].source_file,
        "source_sha256": lines[0].source_hash,
        "taxonomy_version": TAXONOMY_VERSION,
        "ruleset_version": RULESET_VERSION,
        "total_lines": len(lines),
        "mapped_lines": len(lines) - len(unknown),
        "unmapped_line_numbers": unknown,
        "findings": [f.to_dict() for f in findings],
        "potential_exposure_gbp": str(sum((f.estimated_exposure_gbp or Decimal("0") for f in findings), Decimal("0"))),
        "exposure_note": "Illustrative candidate review value; may double-count overlaps and is never realised savings.",
    }

def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)
