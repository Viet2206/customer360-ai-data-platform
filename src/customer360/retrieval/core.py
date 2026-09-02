"""Rebuildable document retrieval with local and OpenSearch stores."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from opensearchpy import OpenSearch


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

    def __init__(self, url: str, index_name: str, embedder: Embedder) -> None:
        self.client = OpenSearch(hosts=[url])
        self.index_name = index_name
        self.embedder = embedder

    def rebuild(self, chunks: list[Chunk]) -> None:
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
        self.client.indices.create(
            index=self.index_name,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.embedder.dimension,
                        },
                        "document_id": {"type": "keyword"},
                        "version": {"type": "keyword"},
                    }
                },
            },
        )
        for chunk in chunks:
            self.client.index(
                index=self.index_name,
                id=chunk.chunk_id,
                body={**asdict(chunk), "embedding": self.embedder.embed(chunk.text)},
                refresh=False,
            )
        self.client.indices.refresh(index=self.index_name)

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
