"""Typed application configuration with YAML and environment overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by pipelines and applications."""

    model_config = SettingsConfigDict(
        env_prefix="CUSTOMER360_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"
    data_root: Path = Path("./data")
    database_url: str = "postgresql+psycopg://customer360:customer360@localhost:55432/customer360"
    opensearch_url: str = "http://localhost:59200"
    ollama_url: str = "http://localhost:51434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    knowledge_search_enabled: bool = False
    knowledge_auto_rebuild: bool = False
    knowledge_documents_path: Path = Path("knowledge")
    knowledge_index_name: str = "customer360-knowledge-v1"
    knowledge_embedding_dimension: int = 64
    knowledge_minimum_score: float = 0.02
    config_file: Path = Field(default=Path("configs/base.yaml"), exclude=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Give environment and .env values precedence over YAML constructor values."""

        return env_settings, dotenv_settings, init_settings, file_secret_settings

    @classmethod
    def from_yaml(cls, path: Path | str = Path("configs/base.yaml")) -> Self:
        """Load defaults from YAML, then let CUSTOMER360_* variables override them."""

        config_path = Path(path)
        raw: dict[str, Any] = {}
        if config_path.exists():
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if loaded is not None and not isinstance(loaded, dict):
                raise ValueError(f"Configuration root must be a mapping: {config_path}")
            raw = loaded or {}
        return cls(**raw, config_file=config_path)


def get_settings() -> Settings:
    """Return settings for command-line and application entry points."""

    return Settings.from_yaml()
