"""Boundary quality rules for conformed Silver domains."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from re import fullmatch
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
                "source_member_id": row.get("source_member_id"),
                "message": message,
                "record_json": json.dumps(row, sort_keys=True, default=str),
                "owner": f"{dataset}-data-owner",
                "observed_at": datetime.now(UTC).isoformat(),
            }
        )

    accepted_members: list[dict[str, Any]] = []
    seen_member_ids: set[str] = set()
    for row in valid["members"]:
        source_member_id = str(row["source_member_id"])
        if source_member_id in seen_member_ids:
            reject(
                "members",
                "member.source_id_unique",
                source_member_id,
                "Duplicate source member ID",
                row,
            )
        elif fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(row["email"])) is None:
            reject("members", "member.email_format", row["source_member_id"], "Invalid email", row)
        else:
            accepted_members.append(row)
            seen_member_ids.add(source_member_id)
    valid["members"] = accepted_members
    member_ids = {row["source_member_id"] for row in accepted_members}

    accepted_plans: list[dict[str, Any]] = []
    for row in valid["plans"]:
        if row["effective_start"] > row["effective_end"]:
            reject("plans", "plan.valid_period", row["plan_id"], "Invalid dates", row)
        elif float(row["annual_deductible"]) < 0:
            reject(
                "plans",
                "plan.deductible_nonnegative",
                row["plan_id"],
                "Negative deductible",
                row,
            )
        else:
            accepted_plans.append(row)
    valid["plans"] = accepted_plans
    plan_ids = {row["plan_id"] for row in accepted_plans}

    accepted_coverage: list[dict[str, Any]] = []
    for row in valid["coverage"]:
        if row["source_member_id"] not in member_ids:
            reject("coverage", "coverage.member_exists", row["coverage_id"], "Orphan coverage", row)
        elif row["plan_id"] not in plan_ids:
            reject("coverage", "coverage.plan_exists", row["coverage_id"], "Unknown plan", row)
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
        elif (
            min(
                float(row["allowed_amount"]),
                float(row["plan_paid_amount"]),
                float(row["member_responsibility"]),
            )
            < 0
        ):
            reject("claims", "claim.amount_nonnegative", row["claim_id"], "Negative amount", row)
        elif row["claim_status"] not in {"paid", "pending", "denied"}:
            reject("claims", "claim.status_domain", row["claim_id"], "Unknown status", row)
        else:
            accepted_claims.append(row)
    valid["claims"] = accepted_claims

    rule_ids = (
        "member.source_id_unique",
        "member.email_format",
        "plan.valid_period",
        "plan.deductible_nonnegative",
        "coverage.member_exists",
        "coverage.plan_exists",
        "coverage.valid_period",
        "claim.member_exists",
        "claim.amount_reconciles",
        "claim.amount_nonnegative",
        "claim.status_domain",
    )
    checks = [
        {
            "run_id": run_id,
            "rule_id": rule_id,
            "failed_count": sum(issue["rule_id"] == rule_id for issue in issues),
            "evaluated_count": sum(len(rows) for rows in domains.values()),
            "status": "failed"
            if any(issue["rule_id"] == rule_id for issue in issues)
            else "passed",
        }
        for rule_id in rule_ids
    ]
    return QualityResult(valid, issues, checks)
