"""Generate a small, deterministic payer dataset for local development and tests."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True)
class GeneratedDataset:
    """Description of one reproducible generated dataset release."""

    output_dir: Path
    manifest_path: Path
    counts: dict[str, int]


FIRST_NAMES = ("Amelia", "Benjamin", "Charlotte", "Daniel", "Elena", "Felix")
LAST_NAMES = ("Nguyen", "Johnson", "Garcia", "Williams", "Brown", "Miller")
PLAN_IDS = ("PLAN-SILVER-01", "PLAN-GOLD-01")


def _stable_id(kind: str, seed: int, number: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"customer360:{kind}:{seed}:{number}"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write an empty source file: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _member_rows(seed: int, member_count: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(member_count):
        first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(index + seed) % len(LAST_NAMES)]
        member_id = f"MEM-{index + 1:05d}"
        rows.append(
            {
                "source_member_id": member_id,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": date(
                    1970 + index % 30, index % 12 + 1, index % 25 + 1
                ).isoformat(),
                "email": f"{first_name}.{last_name}.{index + 1}@example.test".lower(),
                "phone": f"+1-202-555-{1000 + index:04d}",
                "address_line_1": f"{100 + index} Example Avenue",
                "city": "Springfield",
                "state": "VA",
                "postal_code": f"{22150 + index:05d}",
                "source_updated_at": (
                    date(2025, 1, 1) + timedelta(days=rng.randint(0, 30))
                ).isoformat(),
            }
        )
    return rows


def _plan_rows() -> list[dict[str, Any]]:
    return [
        {
            "plan_id": "PLAN-SILVER-01",
            "plan_name": "Community Silver 2500",
            "metal_level": "Silver",
            "annual_deductible": "2500.00",
            "effective_start": "2025-01-01",
            "effective_end": "2025-12-31",
        },
        {
            "plan_id": "PLAN-GOLD-01",
            "plan_name": "Community Gold 1000",
            "metal_level": "Gold",
            "annual_deductible": "1000.00",
            "effective_start": "2025-01-01",
            "effective_end": "2025-12-31",
        },
    ]


def _coverage_rows(member_count: int) -> list[dict[str, Any]]:
    return [
        {
            "coverage_id": f"COV-{index + 1:05d}",
            "source_member_id": f"MEM-{index + 1:05d}",
            "policy_number": f"POL-{20250000 + index + 1}",
            "plan_id": PLAN_IDS[index % len(PLAN_IDS)],
            "coverage_start": "2025-01-01",
            "coverage_end": "2025-12-31",
            "status": "active",
        }
        for index in range(member_count)
    ]


def _claim_rows(seed: int, member_count: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(member_count * 2):
        member_index = index % member_count
        allowed = round(rng.uniform(80, 1800), 2)
        member_amount = round(allowed * rng.choice((0.1, 0.2, 0.3)), 2)
        status = ("paid", "pending", "denied")[index % 3]
        rows.append(
            {
                "claim_id": _stable_id("claim", seed, index),
                "source_member_id": f"MEM-{member_index + 1:05d}",
                "policy_number": f"POL-{20250000 + member_index + 1}",
                "service_date": (date(2025, 1, 15) + timedelta(days=index * 3)).isoformat(),
                "claim_status": status,
                "allowed_amount": f"{allowed:.2f}",
                "plan_paid_amount": f"{max(allowed - member_amount, 0):.2f}",
                "member_responsibility": f"{member_amount:.2f}",
            }
        )
    return rows


def generate_dataset(
    output_dir: Path, *, seed: int = 20250901, member_count: int = 12
) -> GeneratedDataset:
    """Create deterministic source CSVs plus a checksummed release manifest."""

    if member_count < 1:
        raise ValueError("member_count must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    datasets = {
        "members": _member_rows(seed, member_count, rng),
        "plans": _plan_rows(),
        "coverage": _coverage_rows(member_count),
        "claims": _claim_rows(seed, member_count, rng),
    }
    files: list[dict[str, Any]] = []
    for name, rows in datasets.items():
        path = output_dir / f"{name}.csv"
        _write_csv(path, rows)
        files.append(
            {
                "name": name,
                "path": path.name,
                "record_count": len(rows),
                "sha256": _checksum(path),
            }
        )

    manifest = {
        "dataset_id": _stable_id("dataset", seed, member_count),
        "generator": "customer360.synthetic.v1",
        "seed": seed,
        "member_count": member_count,
        "as_of_date": "2025-06-30",
        "files": files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return GeneratedDataset(
        output_dir=output_dir,
        manifest_path=manifest_path,
        counts={name: len(rows) for name, rows in datasets.items()},
    )
