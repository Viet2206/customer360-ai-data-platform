"""Developer command-line interface."""

from pathlib import Path
from typing import Annotated

import typer

from customer360 import __version__
from customer360.common.config import get_settings
from customer360.generation.synthetic import generate_dataset
from customer360.pipelines.medallion import run_pipeline
from customer360.retrieval.core import HashEmbedder, OpenSearchVectorStore
from customer360.retrieval.evaluation import evaluate_retrieval, load_retrieval_cases
from customer360.serving.member360 import publish_member_360

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


@app.command("generate-data")
def generate_data(
    output_dir: Annotated[Path, typer.Option()] = Path("data/generated/demo"),
    seed: Annotated[int, typer.Option()] = 20250901,
    members: Annotated[int, typer.Option(min=1)] = 12,
    duplicates: Annotated[int, typer.Option(min=0)] = 0,
    inject_defects: Annotated[bool, typer.Option()] = False,
) -> None:
    """Generate a deterministic local payer dataset."""

    dataset = generate_dataset(
        output_dir,
        seed=seed,
        member_count=members,
        duplicate_count=duplicates,
        inject_defects=inject_defects,
    )
    typer.echo(f"manifest={dataset.manifest_path} counts={dataset.counts}")


@app.command("run-pipeline")
def pipeline(
    source_dir: Annotated[Path, typer.Option()] = Path("data/generated/demo"),
    data_root: Annotated[Path, typer.Option()] = Path("data"),
    force: Annotated[bool, typer.Option()] = False,
) -> None:
    """Build the Bronze, Silver, and Gold Delta tables."""

    manifest = run_pipeline(source_dir, data_root, force=force)
    typer.echo(f"pipeline_manifest={manifest} status=ok")


@app.command("publish-serving")
def publish_serving(data_root: Annotated[Path, typer.Option()] = Path("data")) -> None:
    """Publish the Gold Member 360 projection to PostgreSQL."""

    settings = get_settings()
    result = publish_member_360(data_root, settings.database_url)
    typer.echo(
        f"publish_id={result.publish_id} gold_run_id={result.gold_run_id} "
        f"members={result.member_count} status=ok"
    )


@app.command("evaluate-retrieval")
def evaluate_retrieval_command(
    cases_path: Annotated[Path, typer.Option()] = Path("knowledge/evaluation/retrieval-cases.yaml"),
    top_k: Annotated[int, typer.Option(min=1, max=10)] = 5,
    minimum_recall: Annotated[float, typer.Option(min=0.0, max=1.0)] = 0.8,
) -> None:
    """Evaluate top-k OpenSearch retrieval against the versioned query set."""

    settings = get_settings()
    store = OpenSearchVectorStore(
        settings.opensearch_url,
        settings.knowledge_index_name,
        HashEmbedder(settings.knowledge_embedding_dimension),
    )
    cases = load_retrieval_cases(cases_path)
    result = evaluate_retrieval(store, cases, limit=top_k)
    typer.echo(
        f"retrieval_recall_at_{top_k}={result.recall_at_k:.3f} "
        f"passed={result.passed}/{result.total} failed={','.join(result.failed_case_ids) or 'none'}"
    )
    if result.recall_at_k < minimum_recall:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
