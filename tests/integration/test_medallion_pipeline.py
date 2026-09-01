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
