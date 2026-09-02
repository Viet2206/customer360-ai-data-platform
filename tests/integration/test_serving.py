import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from customer360.generation.synthetic import generate_dataset
from customer360.pipelines.medallion import run_pipeline
from customer360.serving.member360 import (
    build_engine,
    get_member,
    get_member_identity,
    list_member_claims,
    list_member_quality_issues,
    list_members,
    publish_member_360,
)

DATABASE_URL = os.getenv(
    "CUSTOMER360_TEST_DATABASE_URL",
    "postgresql+psycopg://customer360:customer360@localhost:55432/customer360",
)


def _postgres_available() -> bool:
    engine = build_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return True
    except OperationalError:
        return False
    finally:
        engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(not _postgres_available(), reason="local PostgreSQL is not running")
def test_publish_and_query_member_360(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(source_dir, seed=777, member_count=3)
    run_pipeline(source_dir, data_root)

    publish = publish_member_360(data_root, DATABASE_URL)
    engine = build_engine(DATABASE_URL)
    members = list_members(engine)
    first = get_member(engine, members[0]["member_id"])
    claims = list_member_claims(engine, members[0]["member_id"])
    identity = get_member_identity(engine, members[0]["member_id"])
    quality_issues = list_member_quality_issues(engine, members[0]["member_id"])
    engine.dispose()

    assert publish.member_count == 3
    assert len(members) == 3
    assert first is not None
    assert first["source_member_id"] == "MEM-00001"
    assert len(claims) == 2
    assert all(claim["claim_status_reason"] for claim in claims)
    assert len(identity["sources"]) == 1
    assert not identity["decisions"] or identity["decisions"][0]["decision_model_version"]
    assert quality_issues == []
    assert publish.claim_count == 6
    assert publish.identity_source_count == 3


@pytest.mark.integration
@pytest.mark.skipif(not _postgres_available(), reason="local PostgreSQL is not running")
def test_publish_filters_identity_sources_without_serving_member(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(
        source_dir,
        seed=778,
        member_count=4,
        duplicate_count=2,
        inject_defects=True,
    )
    run_pipeline(source_dir, data_root)

    publish = publish_member_360(data_root, DATABASE_URL)
    engine = build_engine(DATABASE_URL)
    members = list_members(engine)
    engine.dispose()

    assert publish.member_count == len(members)
    assert publish.identity_source_count >= publish.member_count
