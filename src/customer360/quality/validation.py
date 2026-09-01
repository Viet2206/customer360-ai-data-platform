"""Boundary quality rules for conformed Silver domains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualityResult:
    valid: dict[str, list[dict[str, Any]]]
    issues: list[dict[str, Any]]
    checks: list[dict[str, Any]]


def validate_domains(domains: dict[str, list[dict[str, Any]]], run_id: str) -> QualityResult:
    """Apply safe rejection rules before records are admitted to Silver."""

    issues: list[dict[str, Any]] = []
    valid = {name: list(rows) for name, rows in domains.items()}

    def reject(dataset: str, rule_id: str, key: str, message: str, row: dict[str, Any]) -> None:
        issues.append(
            {
                "run_id": run_id,
                "dataset": dataset,
                "rule_id": rule_id,
                "severity": "error",
                "action": "quarantine",
                "record_key": key,
                "message": message,
                "record_json": str(row),
            }
        )

    accepted_members: list[dict[str, Any]] = []
    for row in valid["members"]:
        if "@" not in str(row["email"]):
            reject("members", "member.email_format", row["source_member_id"], "Invalid email", row)
        else:
            accepted_members.append(row)
    valid["members"] = accepted_members
    member_ids = {row["source_member_id"] for row in accepted_members}

    accepted_coverage: list[dict[str, Any]] = []
    for row in valid["coverage"]:
        if row["source_member_id"] not in member_ids:
            reject("coverage", "coverage.member_exists", row["coverage_id"], "Orphan coverage", row)
        elif row["coverage_start"] > row["coverage_end"]:
            reject("coverage", "coverage.valid_period", row["coverage_id"], "Invalid dates", row)
        else:
            accepted_coverage.append(row)
    valid["coverage"] = accepted_coverage

    accepted_claims: list[dict[str, Any]] = []
    for row in valid["claims"]:
        reconciled = round(row["plan_paid_amount"] + row["member_responsibility"], 2)
        if row["source_member_id"] not in member_ids:
            reject("claims", "claim.member_exists", row["claim_id"], "Orphan claim", row)
        elif abs(reconciled - row["allowed_amount"]) > 0.01:
            reject("claims", "claim.amount_reconciles", row["claim_id"], "Amounts differ", row)
        else:
            accepted_claims.append(row)
    valid["claims"] = accepted_claims

    rule_ids = (
        "member.email_format",
        "coverage.member_exists",
        "coverage.valid_period",
        "claim.member_exists",
        "claim.amount_reconciles",
    )
    checks = [
        {
            "run_id": run_id,
            "rule_id": rule_id,
            "failed_count": sum(issue["rule_id"] == rule_id for issue in issues),
            "status": "failed"
            if any(issue["rule_id"] == rule_id for issue in issues)
            else "passed",
        }
        for rule_id in rule_ids
    ]
    return QualityResult(valid, issues, checks)
