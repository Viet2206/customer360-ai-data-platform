"""Local Delta runner for the first reproducible Member 360 vertical slice."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid4, uuid5

import pyarrow as pa  # type: ignore[import-untyped]
from deltalake import DeltaTable, write_deltalake

SOURCE_NAMES = ("members", "plans", "coverage", "claims")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_delta(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty Delta table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_deltalake(str(path), pa.Table.from_pylist(rows), mode="overwrite")


def read_delta(path: Path) -> list[dict[str, Any]]:
    """Read a small Delta table as records for tests and serving publication."""

    return cast(list[dict[str, Any]], DeltaTable(str(path)).to_pyarrow_table().to_pylist())


def _bronze(source_dir: Path, data_root: Path, run_id: str, ingested_at: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in SOURCE_NAMES:
        source_path = source_dir / f"{name}.csv"
        rows = _read_csv(source_path)
        enriched = [
            {
                **row,
                "_source_file": source_path.name,
                "_ingested_at": ingested_at,
                "_run_id": run_id,
            }
            for row in rows
        ]
        _write_delta(data_root / "bronze" / name, enriched)
        counts[name] = len(enriched)
    return counts


def _silver(data_root: Path) -> dict[str, int]:
    members = read_delta(data_root / "bronze" / "members")
    plans = read_delta(data_root / "bronze" / "plans")
    coverage = read_delta(data_root / "bronze" / "coverage")
    claims = read_delta(data_root / "bronze" / "claims")

    member_rows = [
        {
            "source_member_id": row["source_member_id"].strip(),
            "first_name": row["first_name"].strip().title(),
            "last_name": row["last_name"].strip().title(),
            "full_name": f"{row['first_name'].strip().title()} {row['last_name'].strip().title()}",
            "date_of_birth": row["date_of_birth"],
            "email": row["email"].strip().lower(),
            "phone": row["phone"].strip(),
            "address_line_1": row["address_line_1"].strip(),
            "city": row["city"].strip().title(),
            "state": row["state"].strip().upper(),
            "postal_code": row["postal_code"].strip(),
            "source_updated_at": row["source_updated_at"],
        }
        for row in members
    ]
    plan_rows = [
        {
            "plan_id": row["plan_id"],
            "plan_name": row["plan_name"],
            "metal_level": row["metal_level"].lower(),
            "annual_deductible": float(row["annual_deductible"]),
            "effective_start": row["effective_start"],
            "effective_end": row["effective_end"],
        }
        for row in plans
    ]
    coverage_rows = [
        {
            key: row[key]
            for key in (
                "coverage_id",
                "source_member_id",
                "policy_number",
                "plan_id",
                "coverage_start",
                "coverage_end",
                "status",
            )
        }
        for row in coverage
    ]
    claim_rows = [
        {
            "claim_id": row["claim_id"],
            "source_member_id": row["source_member_id"],
            "policy_number": row["policy_number"],
            "service_date": row["service_date"],
            "claim_status": row["claim_status"].lower(),
            "allowed_amount": float(row["allowed_amount"]),
            "plan_paid_amount": float(row["plan_paid_amount"]),
            "member_responsibility": float(row["member_responsibility"]),
        }
        for row in claims
    ]
    outputs = {
        "members": member_rows,
        "plans": plan_rows,
        "coverage": coverage_rows,
        "claims": claim_rows,
    }
    for name, rows in outputs.items():
        _write_delta(data_root / "silver" / name, rows)
    return {name: len(rows) for name, rows in outputs.items()}


def _gold(data_root: Path, run_id: str) -> dict[str, int]:
    members = read_delta(data_root / "silver" / "members")
    plans = read_delta(data_root / "silver" / "plans")
    coverage = read_delta(data_root / "silver" / "coverage")
    claims = read_delta(data_root / "silver" / "claims")

    member_keys = {
        row["source_member_id"]: str(
            uuid5(NAMESPACE_URL, f"customer360:member:{row['source_member_id']}")
        )
        for row in sorted(members, key=lambda item: item["source_member_id"])
    }
    dim_member = [{"member_id": member_keys[row["source_member_id"]], **row} for row in members]
    dim_plan = list(plans)
    fact_coverage = [{"member_id": member_keys[row["source_member_id"]], **row} for row in coverage]
    fact_claim = [{"member_id": member_keys[row["source_member_id"]], **row} for row in claims]

    plan_by_id = {row["plan_id"]: row for row in plans}
    coverage_by_member = {row["source_member_id"]: row for row in coverage}
    claims_by_member: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in claims:
        claims_by_member[row["source_member_id"]].append(row)

    member_360: list[dict[str, Any]] = []
    for member in members:
        source_id = member["source_member_id"]
        member_claims = claims_by_member[source_id]
        member_coverage = coverage_by_member[source_id]
        plan = plan_by_id[member_coverage["plan_id"]]
        member_360.append(
            {
                "member_id": member_keys[source_id],
                "source_member_id": source_id,
                "full_name": member["full_name"],
                "date_of_birth": member["date_of_birth"],
                "email": member["email"],
                "phone": member["phone"],
                "policy_number": member_coverage["policy_number"],
                "coverage_status": member_coverage["status"],
                "coverage_start": member_coverage["coverage_start"],
                "coverage_end": member_coverage["coverage_end"],
                "plan_id": plan["plan_id"],
                "plan_name": plan["plan_name"],
                "annual_deductible": plan["annual_deductible"],
                "claim_count": len(member_claims),
                "total_allowed_amount": round(
                    sum(float(claim["allowed_amount"]) for claim in member_claims), 2
                ),
                "total_member_responsibility": round(
                    sum(float(claim["member_responsibility"]) for claim in member_claims), 2
                ),
                "latest_claim_status": max(member_claims, key=lambda claim: claim["service_date"])[
                    "claim_status"
                ],
                "gold_run_id": run_id,
            }
        )

    outputs = {
        "dim_member": dim_member,
        "dim_plan": dim_plan,
        "fact_coverage": fact_coverage,
        "fact_claim": fact_claim,
        "member_360": member_360,
    }
    for name, rows in outputs.items():
        _write_delta(data_root / "gold" / name, rows)
    return {name: len(rows) for name, rows in outputs.items()}


def run_pipeline(source_dir: Path, data_root: Path) -> Path:
    """Run Bronze, Silver, and Gold and persist a reconciliation manifest."""

    source_manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    run_id = str(uuid4())
    ingested_at = datetime.now(UTC).isoformat()
    bronze_counts = _bronze(source_dir, data_root, run_id, ingested_at)
    expected = {item["name"]: item["record_count"] for item in source_manifest["files"]}
    if bronze_counts != expected:
        raise ValueError(
            f"Bronze reconciliation failed: expected={expected}, actual={bronze_counts}"
        )
    silver_counts = _silver(data_root)
    gold_counts = _gold(data_root, run_id)
    run_manifest = {
        "run_id": run_id,
        "dataset_id": source_manifest["dataset_id"],
        "started_at": ingested_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "counts": {"bronze": bronze_counts, "silver": silver_counts, "gold": gold_counts},
    }
    audit_dir = data_root / "audit" / "pipeline_runs"
    audit_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = audit_dir / f"{run_id}.json"
    manifest_path.write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path
