"""Rebuildable document retrieval with local and OpenSearch stores."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    text: str
    source: str
    section: str
    version: str


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class IndexBuildResult:
    alias_name: str
    index_name: str
    corpus_digest: str
    document_count: int
    changed: bool


class Embedder(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]: ...


def chunk_markdown(path: Path, *, version: str = "v1", max_words: int = 120) -> list[Chunk]:
    """Split Markdown by headings and bounded word windows with stable IDs."""

    text = path.read_text(encoding="utf-8")
    first_heading = next(
        (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")),
        "",
    )
    title = first_heading or path.stem.replace("-", " ").title()
    section = title
    chunks: list[Chunk] = []
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        while buffer:
            words = buffer[:max_words]
            buffer = buffer[max_words:]
            body = " ".join(words).strip()
            if body:
                digest = hashlib.sha256(
                    f"{path.name}:{version}:{section}:{len(chunks)}:{body}".encode()
                ).hexdigest()[:24]
                chunks.append(Chunk(digest, path.stem, title, body, str(path), section, version))

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            section = line.lstrip("# ").strip() or title
        elif line.strip():
            buffer.extend(line.split())
    flush()
    return chunks


def load_markdown_chunks(root: Path, *, version: str = "v1") -> list[Chunk]:
    """Load a deterministic, recursive Markdown corpus for index rebuilds."""

    paths = [root] if root.is_file() else sorted(root.rglob("*.md"))
    chunks = [chunk for path in paths for chunk in chunk_markdown(path, version=version)]
    if not chunks:
        raise ValueError(f"No Markdown documents found under {root}")
    return chunks


class HashEmbedder:
    """Deterministic embedding used only for tests and smoke demos."""

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in text.casefold().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, dimension: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.base_url}/api/embed", json={"model": self.model, "input": text}, timeout=60
        )
        response.raise_for_status()
        vector = list(response.json()["embeddings"][0])
        if len(vector) != self.dimension:
            raise ValueError(f"Expected embedding dimension {self.dimension}, got {len(vector)}")
        return [float(value) for value in vector]


class InMemoryVectorStore:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._items: list[tuple[Chunk, list[float]]] = []

    def index(self, chunks: list[Chunk]) -> None:
        self._items = [(chunk, self.embedder.embed(chunk.text)) for chunk in chunks]

    def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        query_vector = self.embedder.embed(query)
        hits = [
            SearchHit(
                chunk, sum(left * right for left, right in zip(query_vector, vector, strict=True))
            )
            for chunk, vector in self._items
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]


class OpenSearchVectorStore:
    """OpenSearch k-NN index; trusted document manifests remain in Delta."""

    def __init__(
        self,
        url: str,
        index_name: str,
        embedder: Embedder,
        *,
        client: OpenSearch | None = None,
    ) -> None:
        self.client = client or OpenSearch(hosts=[url])
        self.index_name = index_name
        self.embedder = embedder

    def is_ready(self) -> bool:
        """Return whether the search alias or a legacy direct index exists."""

        return bool(self.client.indices.exists(index=self.index_name))

    def _corpus_digest(self, chunks: list[Chunk]) -> str:
        payload = "\n".join(
            [
                f"embedding-dimension:{self.embedder.dimension}",
                *(f"{chunk.chunk_id}:{chunk.version}:{chunk.text}" for chunk in chunks),
            ]
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def rebuild(self, chunks: list[Chunk]) -> IndexBuildResult:
        """Build a verified physical index and atomically promote its read alias."""

        if not chunks:
            raise ValueError("Cannot build an empty knowledge index")
        corpus_digest = self._corpus_digest(chunks)
        physical_index = f"{self.index_name}-{corpus_digest[:12]}"
        alias_exists = bool(self.client.indices.exists_alias(name=self.index_name))
        current_indexes = (
            set(self.client.indices.get_alias(name=self.index_name)) if alias_exists else set()
        )
        if physical_index in current_indexes:
            return IndexBuildResult(
                self.index_name,
                physical_index,
                corpus_digest,
                len(chunks),
                False,
            )

        if self.client.indices.exists(index=physical_index):
            self.client.indices.delete(index=physical_index)
        self.client.indices.create(
            index=physical_index,
            body={
                "settings": {
                    "index": {"knn": True, "number_of_shards": 1, "number_of_replicas": 0}
                },
                "mappings": {
                    "dynamic": "strict",
                    "_meta": {
                        "corpus_digest": corpus_digest,
                        "embedding_dimension": self.embedder.dimension,
                        "built_at": datetime.now(UTC).isoformat(),
                    },
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.embedder.dimension,
                        },
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "title": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                        "source": {"type": "keyword"},
                        "section": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                        "version": {"type": "keyword"},
                    },
                },
            },
        )
        actions = [
            {
                "_op_type": "index",
                "_index": physical_index,
                "_id": chunk.chunk_id,
                "_source": {**asdict(chunk), "embedding": self.embedder.embed(chunk.text)},
            }
            for chunk in chunks
        ]
        indexed_count, _ = bulk(self.client, actions, refresh=True, raise_on_error=True)
        actual_count = int(self.client.count(index=physical_index)["count"])
        if indexed_count != len(chunks) or actual_count != len(chunks):
            raise RuntimeError(
                "Knowledge index reconciliation failed: "
                f"expected={len(chunks)}, bulk={indexed_count}, actual={actual_count}"
            )

        actions_for_alias: list[dict[str, dict[str, Any]]] = []
        if alias_exists:
            actions_for_alias.extend(
                {"remove": {"index": index, "alias": self.index_name}}
                for index in sorted(current_indexes)
            )
        elif self.client.indices.exists(index=self.index_name):
            actions_for_alias.append({"remove_index": {"index": self.index_name}})
        actions_for_alias.append(
            {"add": {"index": physical_index, "alias": self.index_name, "is_write_index": True}}
        )
        self.client.indices.update_aliases(body={"actions": actions_for_alias})
        return IndexBuildResult(
            self.index_name,
            physical_index,
            corpus_digest,
            actual_count,
            True,
        )

    def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        candidate_count = max(limit * 2, limit)
        lexical = self.client.search(
            index=self.index_name,
            body={"size": candidate_count, "query": {"match": {"text": query}}},
        )
        semantic = self.client.search(
            index=self.index_name,
            body={
                "size": candidate_count,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": self.embedder.embed(query),
                            "k": candidate_count,
                        }
                    }
                },
            },
        )
        scores: dict[str, float] = {}
        sources: dict[str, dict[str, Any]] = {}
        for response in (lexical, semantic):
            for rank, hit in enumerate(response["hits"]["hits"], start=1):
                chunk_id = str(hit["_id"])
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank)
                sources[chunk_id] = dict(hit["_source"])
        results: list[SearchHit] = []
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        for chunk_id, score in ranked:
            source = sources[chunk_id]
            source.pop("embedding", None)
            results.append(SearchHit(Chunk(**source), score))
        return results
