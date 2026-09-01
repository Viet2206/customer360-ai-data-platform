"""Developer command-line interface."""

from pathlib import Path

import typer

from customer360 import __version__
from customer360.common.config import get_settings

app = typer.Typer(no_args_is_help=True, help="Customer 360 platform developer commands.")


@app.callback()
def main() -> None:
    """Run Customer 360 developer commands."""


@app.command()
def smoke() -> None:
    """Validate configuration and required local project paths."""

    settings = get_settings()
    required = [Path("intent.md"), settings.config_file]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        typer.echo(f"Missing required files: {', '.join(missing)}", err=True)
        raise typer.Exit(1)
    typer.echo(
        f"customer360={__version__} environment={settings.environment} "
        f"data_root={settings.data_root} status=ok"
    )


if __name__ == "__main__":
    app()
