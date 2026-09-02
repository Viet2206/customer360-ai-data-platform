from pathlib import Path

import pytest

from customer360.common.config import Settings


def test_settings_load_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "settings.yaml"
    config_file.write_text("environment: test\ndata_root: ./fixtures\n", encoding="utf-8")
    monkeypatch.delenv("CUSTOMER360_ENVIRONMENT", raising=False)

    settings = Settings.from_yaml(config_file)

    assert settings.environment == "test"
    assert settings.data_root == Path("fixtures")
    assert settings.config_file == config_file


def test_environment_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "settings.yaml"
    config_file.write_text("environment: yaml\n", encoding="utf-8")
    monkeypatch.setenv("CUSTOMER360_ENVIRONMENT", "environment-variable")

    settings = Settings.from_yaml(config_file)

    assert settings.environment == "environment-variable"


def test_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "settings.yaml"
    config_file.write_text("- invalid\n- root\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Configuration root must be a mapping"):
        Settings.from_yaml(config_file)


def test_missing_yaml_uses_defaults(tmp_path: Path) -> None:
    settings = Settings.from_yaml(tmp_path / "missing.yaml")

    assert settings.environment == "local"
    assert settings.knowledge_documents_path == Path("knowledge")


def test_empty_yaml_uses_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("", encoding="utf-8")

    settings = Settings.from_yaml(config_file)

    assert settings.environment == "local"
