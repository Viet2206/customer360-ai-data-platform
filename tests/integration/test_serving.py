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
    engine.dispose()

    assert publish.member_count == 3
    assert len(members) == 3
    assert first is not None
    assert first["source_member_id"] == "MEM-00001"
