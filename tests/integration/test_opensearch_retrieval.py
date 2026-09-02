from pathlib import Path
from uuid import uuid4

import pytest
from opensearchpy import OpenSearch

from customer360.retrieval.core import HashEmbedder, OpenSearchVectorStore, chunk_markdown

OPENSEARCH_URL = "http://localhost:59200"


def _opensearch_available() -> bool:
    return bool(OpenSearch(hosts=[OPENSEARCH_URL]).ping())


@pytest.mark.integration
@pytest.mark.skipif(not _opensearch_available(), reason="local OpenSearch is not running")
def test_versioned_index_build_is_atomic_and_idempotent() -> None:
    alias_name = f"customer360-test-{uuid4().hex[:10]}"
    client = OpenSearch(hosts=[OPENSEARCH_URL])
    store = OpenSearchVectorStore(
        OPENSEARCH_URL,
        alias_name,
        HashEmbedder(),
        client=client,
    )
    chunks = chunk_markdown(Path("tests/fixtures/documents/benefits.md"))
    result = None
    try:
        result = store.rebuild(chunks)
        repeated = store.rebuild(chunks)
        hits = store.search("annual deductible", limit=3)

        assert result.changed
        assert result.index_name != result.alias_name
        assert result.document_count == len(chunks)
        assert client.indices.exists_alias(name=alias_name)
        assert not repeated.changed
        assert repeated.index_name == result.index_name
        assert any("deductible" in hit.chunk.text.casefold() for hit in hits)
    finally:
        if result is not None and client.indices.exists(index=result.index_name):
            client.indices.delete(index=result.index_name)
