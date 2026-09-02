import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from customer360.api.main import create_app
from customer360.common.config import Settings
from customer360.generation.synthetic import generate_dataset
from customer360.pipelines.medallion import run_pipeline
from customer360.serving.member360 import build_engine, publish_member_360

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


@pytest.mark.end_to_end
@pytest.mark.skipif(not _postgres_available(), reason="local PostgreSQL is not running")
def test_source_to_member_api(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    data_root = tmp_path / "lakehouse"
    generate_dataset(source_dir, seed=888, member_count=2)
    run_pipeline(source_dir, data_root)
    publish_member_360(data_root, DATABASE_URL)

    app = create_app(Settings(database_url=DATABASE_URL))
    with TestClient(app) as client:
        response = client.get("/api/v1/members")
        assert response.status_code == 200
        members = response.json()
        assert len(members) == 2

        detail = client.get(f"/api/v1/members/{members[0]['member_id']}")
        assert detail.status_code == 200
        assert detail.json()["source_member_id"] == "MEM-00001"

        claims = client.get(f"/api/v1/members/{members[0]['member_id']}/claims")
        assert claims.status_code == 200
        assert len(claims.json()) == 2
        assert claims.json()[0]["provider_name"]
        assert claims.json()[0]["claim_status_reason"]

        identity = client.get(f"/api/v1/members/{members[0]['member_id']}/identity")
        assert identity.status_code == 200
        assert identity.json()["sources"]

        quality = client.get(f"/api/v1/members/{members[0]['member_id']}/quality-issues")
        assert quality.status_code == 200
        assert quality.json() == []

        missing = client.get("/api/v1/members/not-a-member")
        assert missing.status_code == 404

        masked = client.get("/api/v1/members", headers={"X-Role": "analytics"})
        assert masked.json()[0]["email"] == "***"
        masked_claims = client.get(
            f"/api/v1/members/{members[0]['member_id']}/claims",
            headers={"X-Role": "analytics"},
        )
        assert masked_claims.json()[0]["policy_number"] == "***"
        restricted_identity = client.get(
            f"/api/v1/members/{members[0]['member_id']}/identity",
            headers={"X-Role": "analytics"},
        )
        assert restricted_identity.status_code == 403

        forbidden = client.get("/api/v1/members", headers={"X-Role": "unknown"})
        assert forbidden.status_code == 403
