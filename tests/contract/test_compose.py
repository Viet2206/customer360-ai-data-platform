from pathlib import Path

import yaml


def test_postgres_has_healthcheck_and_persistent_storage() -> None:
    compose = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))
    postgres = compose["services"]["postgres"]

    assert postgres["healthcheck"]
    assert "postgres_data:/var/lib/postgresql/data" in postgres["volumes"]
    assert "postgres_data" in compose["volumes"]


def test_ai_services_are_optional_and_persistent() -> None:
    compose = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))

    assert compose["services"]["opensearch"]["profiles"] == ["ai"]
    assert compose["services"]["ollama"]["profiles"] == ["ai"]
    assert "opensearch_data" in compose["volumes"]
    assert "ollama_data" in compose["volumes"]
    api_environment = compose["services"]["api"]["environment"]
    assert api_environment["CUSTOMER360_KNOWLEDGE_AUTO_REBUILD"] == "true"
