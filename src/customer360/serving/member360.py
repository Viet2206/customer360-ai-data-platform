"""Publish and query the rebuildable PostgreSQL Member 360 projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from customer360.pipelines.medallion import read_delta

metadata = MetaData()

member_360_table = Table(
    "member_360",
    metadata,
    Column("member_id", String(36), primary_key=True),
    Column("source_member_id", String(64), nullable=False, unique=True),
    Column("full_name", String(200), nullable=False),
    Column("date_of_birth", String(10), nullable=False),
    Column("email", String(320), nullable=False),
    Column("phone", String(40), nullable=False),
    Column("policy_number", String(80), nullable=False),
    Column("coverage_status", String(40), nullable=False),
    Column("coverage_start", String(10), nullable=False),
    Column("coverage_end", String(10), nullable=False),
    Column("plan_id", String(80), nullable=False),
    Column("plan_name", String(200), nullable=False),
    Column("annual_deductible", Float, nullable=False),
    Column("claim_count", Integer, nullable=False),
    Column("total_allowed_amount", Float, nullable=False),
    Column("total_member_responsibility", Float, nullable=False),
    Column("latest_claim_status", String(40), nullable=False),
    Column("gold_run_id", String(36), nullable=False),
    schema="serving",
)

publish_audit_table = Table(
    "serving_publish_audit",
    metadata,
    Column("publish_id", String(36), primary_key=True),
    Column("gold_run_id", String(36), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=False),
    Column("member_count", Integer, nullable=False),
    Column("status", String(30), nullable=False),
    schema="audit",
)


@dataclass(frozen=True)
class PublishResult:
    publish_id: str
    gold_run_id: str
    member_count: int


def build_engine(database_url: str) -> Engine:
    """Create a pooled SQLAlchemy engine."""

    return create_engine(database_url, pool_pre_ping=True)


def publish_member_360(data_root: Path, database_url: str) -> PublishResult:
    """Atomically replace the serving projection and record its Gold lineage."""

    rows = read_delta(data_root / "gold" / "member_360")
    if not rows:
        raise ValueError("Gold member_360 is empty")
    gold_run_ids = {str(row["gold_run_id"]) for row in rows}
    if len(gold_run_ids) != 1:
        raise ValueError(f"Expected one Gold run ID, found {sorted(gold_run_ids)}")
    gold_run_id = gold_run_ids.pop()
    publish_id = str(uuid4())
    engine = build_engine(database_url)
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(delete(member_360_table))
        connection.execute(insert(member_360_table), rows)
        actual_count = connection.scalar(select(func.count()).select_from(member_360_table))
        if actual_count != len(rows):
            raise RuntimeError(
                f"Serving reconciliation failed: expected={len(rows)}, actual={actual_count}"
            )
        connection.execute(
            insert(publish_audit_table),
            {
                "publish_id": publish_id,
                "gold_run_id": gold_run_id,
                "published_at": datetime.now(UTC),
                "member_count": len(rows),
                "status": "succeeded",
            },
        )
    engine.dispose()
    return PublishResult(publish_id, gold_run_id, len(rows))


def list_members(engine: Engine, *, limit: int = 100) -> list[dict[str, Any]]:
    """Return members in stable source-ID order."""

    statement = select(member_360_table).order_by(member_360_table.c.source_member_id).limit(limit)
    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()
    return [dict(row) for row in rows]


def get_member(engine: Engine, member_id: str) -> dict[str, Any] | None:
    """Look up one serving member by golden member ID."""

    statement = select(member_360_table).where(member_360_table.c.member_id == member_id)
    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()
    return dict(row) if row is not None else None
