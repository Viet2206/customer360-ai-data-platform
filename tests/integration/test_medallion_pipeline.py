import json
from pathlib import Path

from customer360.generation.synthetic import generate_dataset
from customer360.pipelines.medallion import read_delta, run_pipeline


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
