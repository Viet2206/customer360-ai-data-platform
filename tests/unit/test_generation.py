import json
from pathlib import Path

import pytest

from customer360.generation.synthetic import generate_dataset


def test_generation_is_reproducible(tmp_path: Path) -> None:
    first = generate_dataset(tmp_path / "first", seed=42, member_count=3)
    second = generate_dataset(tmp_path / "second", seed=42, member_count=3)

    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first.counts == {"members": 3, "plans": 2, "coverage": 3, "claims": 6}
    assert [item["sha256"] for item in first_manifest["files"]] == [
        item["sha256"] for item in second_manifest["files"]
    ]
    assert first_manifest["dataset_id"] == second_manifest["dataset_id"]


def test_generation_rejects_empty_population(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="member_count must be positive"):
        generate_dataset(tmp_path, member_count=0)
