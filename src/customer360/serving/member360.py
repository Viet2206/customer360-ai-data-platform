"""Publish and query the rebuildable PostgreSQL Member 360 projection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
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
    Column("identity_source_count", Integer, nullable=False),
    Column("identity_confidence", String(40), nullable=False),
    Column("quality_issue_count", Integer, nullable=False),
    Column("gold_run_id", String(36), nullable=False),
    schema="serving",
)

member_claim_table = Table(
    "member_claim",
    metadata,
    Column("claim_id", String(64), primary_key=True),
    Column(
        "member_id",
        String(36),
        ForeignKey("serving.member_360.member_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("source_member_id", String(64), nullable=False),
    Column("policy_number", String(80), nullable=False),
    Column("service_date", String(10), nullable=False),
    Column("claim_status", String(40), nullable=False),
    Column("claim_status_reason", String(200), nullable=False),
    Column("service_category", String(100), nullable=False),
    Column("provider_name", String(200), nullable=False),
    Column("allowed_amount", Float, nullable=False),
    Column("plan_paid_amount", Float, nullable=False),
    Column("member_responsibility", Float, nullable=False),
    schema="serving",
)

member_identity_source_table = Table(
    "member_identity_source",
    metadata,
    Column(
        "member_id",
        String(36),
        ForeignKey("serving.member_360.member_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("source_member_id", String(64), primary_key=True),
    Column("cluster_size", Integer, nullable=False),
    Column("is_survivor", Boolean, nullable=False),
    Column("run_id", String(36), nullable=False),
    schema="serving",
)

member_identity_decision_table = Table(
    "member_identity_decision",
    metadata,
    Column("decision_id", String(24), primary_key=True),
    Column(
        "member_id",
        String(36),
        ForeignKey("serving.member_360.member_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("left_source_member_id", String(64), nullable=False),
    Column("right_source_member_id", String(64), nullable=False),
    Column("match_score", Float, nullable=False),
    Column("match_threshold", Float, nullable=False),
    Column("decision", String(30), nullable=False),
    Column("confidence_band", String(30), nullable=False),
    Column("decision_model_version", String(80), nullable=False),
    Column("run_id", String(36), nullable=False),
    schema="serving",
)

member_quality_issue_table = Table(
    "member_quality_issue",
    metadata,
    Column("issue_id", String(24), primary_key=True),
    Column(
        "member_id",
        String(36),
        ForeignKey("serving.member_360.member_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    ),
    Column("dataset", String(80), nullable=False),
    Column("rule_id", String(120), nullable=False),
    Column("severity", String(30), nullable=False),
    Column("action", String(40), nullable=False),
    Column("record_key", String(100), nullable=False),
    Column("message", String(300), nullable=False),
    Column("owner", String(120), nullable=False),
    Column("observed_at", String(40), nullable=False),
    Column("run_id", String(36), nullable=False),
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
    claim_count: int
    identity_source_count: int
    identity_decision_count: int
    quality_issue_count: int


def build_engine(database_url: str) -> Engine:
    """Create a pooled SQLAlchemy engine."""

    return create_engine(database_url, pool_pre_ping=True)


def _ensure_member_projection_columns(engine: Engine) -> None:
    """Apply additive compatibility changes to the rebuildable local projection."""

    existing = {
        str(column["name"])
        for column in inspect(engine).get_columns("member_360", schema="serving")
    }
    additions = {
        "identity_source_count": "INTEGER NOT NULL DEFAULT 1",
        "identity_confidence": "VARCHAR(40) NOT NULL DEFAULT 'single_source'",
        "quality_issue_count": "INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for column, definition in additions.items():
            if column not in existing:
                connection.execute(
                    text(f"ALTER TABLE serving.member_360 ADD COLUMN {column} {definition}")
                )


def publish_member_360(data_root: Path, database_url: str) -> PublishResult:
    """Atomically replace the serving projection and record its Gold lineage."""

    rows = read_delta(data_root / "gold" / "member_360")
    if not rows:
        raise ValueError("Gold member_360 is empty")
    gold_run_ids = {str(row["gold_run_id"]) for row in rows}
    if len(gold_run_ids) != 1:
        raise ValueError(f"Expected one Gold run ID, found {sorted(gold_run_ids)}")
    gold_run_id = gold_run_ids.pop()
    published_member_ids = {str(row["member_id"]) for row in rows}
    claims = read_delta(data_root / "gold" / "fact_claim")
    identity_sources = read_delta(data_root / "gold" / "member_identifier_xref")
    identity_decisions = read_delta(data_root / "gold" / "identity_match_decision")
    quality_issues = read_delta(data_root / "quarantine" / "records")
    source_to_member = {
        str(row["source_member_id"]): str(row["member_id"])
        for row in identity_sources
        if str(row["member_id"]) in published_member_ids
    }
    claim_rows = [
        {
            key: row[key]
            for key in (
                "claim_id",
                "member_id",
                "source_member_id",
                "policy_number",
                "service_date",
                "claim_status",
                "claim_status_reason",
                "service_category",
                "provider_name",
                "allowed_amount",
                "plan_paid_amount",
                "member_responsibility",
            )
        }
        for row in claims
    ]
    identity_source_rows = [
        {
            "member_id": row["member_id"],
            "source_member_id": row["source_member_id"],
            "cluster_size": row["cluster_size"],
            "is_survivor": bool(row["is_survivor"]),
            "run_id": row["run_id"],
        }
        for row in identity_sources
        if str(row["member_id"]) in published_member_ids
    ]
    identity_decision_rows = [
        {
            "decision_id": hashlib.sha256(
                f"{row['run_id']}:{row['left_source_member_id']}:{row['right_source_member_id']}".encode()
            ).hexdigest()[:24],
            **{
                key: row[key]
                for key in (
                    "member_id",
                    "left_source_member_id",
                    "right_source_member_id",
                    "match_score",
                    "match_threshold",
                    "decision",
                    "confidence_band",
                    "decision_model_version",
                    "run_id",
                )
            },
        }
        for row in identity_decisions
        if str(row["member_id"]) in published_member_ids
    ]
    quality_issue_rows = [
        {
            "issue_id": hashlib.sha256(
                f"{row['run_id']}:{row['dataset']}:{row['rule_id']}:{row['record_key']}".encode()
            ).hexdigest()[:24],
            "member_id": source_to_member.get(str(row.get("source_member_id"))),
            **{
                key: row[key]
                for key in (
                    "dataset",
                    "rule_id",
                    "severity",
                    "action",
                    "record_key",
                    "message",
                    "owner",
                    "observed_at",
                    "run_id",
                )
            },
        }
        for row in quality_issues
    ]
    publish_id = str(uuid4())
    engine = build_engine(database_url)
    metadata.create_all(engine)
    _ensure_member_projection_columns(engine)
    with engine.begin() as connection:
        connection.execute(delete(member_quality_issue_table))
        connection.execute(delete(member_identity_decision_table))
        connection.execute(delete(member_identity_source_table))
        connection.execute(delete(member_claim_table))
        connection.execute(delete(member_360_table))
        connection.execute(insert(member_360_table), rows)
        if claim_rows:
            connection.execute(insert(member_claim_table), claim_rows)
        if identity_source_rows:
            connection.execute(insert(member_identity_source_table), identity_source_rows)
        if identity_decision_rows:
            connection.execute(insert(member_identity_decision_table), identity_decision_rows)
        if quality_issue_rows:
            connection.execute(insert(member_quality_issue_table), quality_issue_rows)
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
    return PublishResult(
        publish_id,
        gold_run_id,
        len(rows),
        len(claim_rows),
        len(identity_source_rows),
        len(identity_decision_rows),
        len(quality_issue_rows),
    )


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


def list_member_claims(engine: Engine, member_id: str) -> list[dict[str, Any]]:
    """Return claim-level financial and operational detail for a member."""

    statement = (
        select(member_claim_table)
        .where(member_claim_table.c.member_id == member_id)
        .order_by(member_claim_table.c.service_date.desc(), member_claim_table.c.claim_id)
    )
    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()
    return [dict(row) for row in rows]


def get_member_identity(engine: Engine, member_id: str) -> dict[str, list[dict[str, Any]]]:
    """Return source crosswalks and inspectable match decisions for a member."""

    source_statement = (
        select(member_identity_source_table)
        .where(member_identity_source_table.c.member_id == member_id)
        .order_by(member_identity_source_table.c.source_member_id)
    )
    decision_statement = (
        select(member_identity_decision_table)
        .where(member_identity_decision_table.c.member_id == member_id)
        .order_by(member_identity_decision_table.c.match_score.desc())
    )
    with engine.connect() as connection:
        sources = connection.execute(source_statement).mappings().all()
        decisions = connection.execute(decision_statement).mappings().all()
    return {
        "sources": [dict(row) for row in sources],
        "decisions": [dict(row) for row in decisions],
    }


def list_member_quality_issues(engine: Engine, member_id: str) -> list[dict[str, Any]]:
    """Return safe quality metadata linked to a resolved member."""

    statement = (
        select(member_quality_issue_table)
        .where(member_quality_issue_table.c.member_id == member_id)
        .order_by(member_quality_issue_table.c.observed_at.desc())
    )
    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()
    return [dict(row) for row in rows]
