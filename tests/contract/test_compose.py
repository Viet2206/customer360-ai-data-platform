from pathlib import Path

import yaml


def test_postgres_has_healthcheck_and_persistent_storage() -> None:
    compose = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))
    postgres = compose["services"]["postgres"]

    assert postgres["healthcheck"]
    assert "postgres_data:/var/lib/postgresql/data" in postgres["volumes"]
    assert "postgres_data" in compose["volumes"]
