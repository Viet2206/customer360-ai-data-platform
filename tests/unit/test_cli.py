from pathlib import Path

import pytest
from typer.testing import CliRunner

from customer360.cli import app


def test_smoke_command() -> None:
    result = CliRunner().invoke(app, ["smoke"])

    assert result.exit_code == 0
    assert "status=ok" in result.stdout


def test_smoke_reports_missing_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["smoke"])

    assert result.exit_code == 1
    assert "Missing required files" in result.stderr
