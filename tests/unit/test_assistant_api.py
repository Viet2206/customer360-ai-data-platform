from pathlib import Path

from fastapi.testclient import TestClient

from customer360.api.main import create_app
from customer360.assistant.service import GroundedAssistant
from customer360.common.config import Settings
from customer360.retrieval.core import HashEmbedder, InMemoryVectorStore, chunk_markdown


def test_assistant_endpoint_returns_citations() -> None:
    store = InMemoryVectorStore(HashEmbedder())
    store.index(chunk_markdown(Path("tests/fixtures/documents/benefits.md")))
    app = create_app(
        Settings(database_url="sqlite://"), GroundedAssistant(store, minimum_score=0.01)
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/assistant", json={"question": "What is the deductible?"})

    assert response.status_code == 200
    assert response.json()["grounded"]
    assert response.json()["citations"]


def test_assistant_endpoint_requires_configured_index() -> None:
    app = create_app(Settings(database_url="sqlite://"))

    with TestClient(app) as client:
        response = client.post("/api/v1/assistant", json={"question": "What is covered?"})

    assert response.status_code == 503
