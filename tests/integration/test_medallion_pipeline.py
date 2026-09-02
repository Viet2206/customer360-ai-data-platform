import json
from pathlib import Path

import pytest

from customer360.generation.synthetic import generate_dataset
from customer360.pipelines.medallion import _write_delta, read_delta, run_pipeline


def test_delta_rebuild_accepts_additive_contract_evolution(tmp_path: Path) -> None:
    table_path = tmp_path / "evolving_table"
    _write_delta(table_path, [{"member_id": "M-1"}])

    _write_delta(table_path, [{"member_id": "M-1", "quality_issue_count": 0}])

    assert read_delta(table_path) == [{"member_id": "M-1", "quality_issue_count": 0}]


def test_member_360_vertical_slice(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(source_dir, seed=123, member_count=4)

    manifest_path = run_pipeline(source_dir, data_root)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    members = read_delta(data_root / "gold" / "member_360")
    claims = read_delta(data_root / "gold" / "fact_claim")
    assert manifest["status"] == "succeeded"
    assert manifest["counts"]["bronze"]["members"] == 4
    assert len(members) == 4
    assert len(claims) == 8
    assert all(member["claim_count"] == 2 for member in members)
    assert all(member["total_allowed_amount"] > 0 for member in members)

    repeated_manifest = run_pipeline(source_dir, data_root)
    assert repeated_manifest == manifest_path


def test_identity_resolution_and_quality_quarantine(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(
        source_dir,
        seed=456,
        member_count=4,
        duplicate_count=2,
        inject_defects=True,
    )

    run_pipeline(source_dir, data_root)

    xref = read_delta(data_root / "gold" / "member_identifier_xref")
    decisions = read_delta(data_root / "gold" / "identity_match_decision")
    issues = read_delta(data_root / "quarantine" / "records")
    evaluation = read_delta(data_root / "quality" / "identity_evaluation")[0]
    assert any(row["cluster_size"] == 2 for row in xref)
    assert any(row["decision"] == "match" for row in decisions)
    assert {row["rule_id"] for row in issues} >= {
        "member.email_format",
        "claim.member_exists",
        "claim.amount_reconciles",
    }
    assert evaluation["precision"] == 1.0
    assert evaluation["recall"] == 0.5
    assert all(row["owner"] and row["observed_at"] for row in issues)
    assert all(row["run_id"] for row in decisions)
    assert all(row["decision_model_version"] == "weighted-rules-v1" for row in decisions)


def test_pipeline_rejects_tampered_source_before_bronze(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(source_dir, seed=999, member_count=2)
    members_path = source_dir / "members.csv"
    members_path.write_text(
        members_path.read_text(encoding="utf-8") + "tampered,row\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Checksum mismatch"):
        run_pipeline(source_dir, data_root)

    assert not (data_root / "bronze").exists()


def test_single_member_pipeline_writes_empty_identity_decisions(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(source_dir, seed=1001, member_count=1)

    run_pipeline(source_dir, data_root)

    assert read_delta(data_root / "gold" / "identity_match_decision") == []


def test_clean_replay_clears_previous_quarantine(tmp_path: Path) -> None:
    data_root = tmp_path / "lakehouse"
    defective_source = tmp_path / "defective"
    clean_source = tmp_path / "clean"
    generate_dataset(defective_source, seed=1002, member_count=3, inject_defects=True)
    generate_dataset(clean_source, seed=1003, member_count=3)

    run_pipeline(defective_source, data_root)
    assert read_delta(data_root / "quarantine" / "records")

    run_pipeline(clean_source, data_root)

    assert read_delta(data_root / "quarantine" / "records") == []
