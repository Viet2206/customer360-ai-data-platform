"""Evidence-first answering with citations and explicit abstention."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from customer360.retrieval.core import SearchHit


class SearchStore(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[SearchHit]: ...


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    title: str
    section: str
    source: str
    version: str


@dataclass(frozen=True)
class Answer:
    text: str
    grounded: bool
    citations: list[Citation]


class GroundedAssistant:
    def __init__(self, store: SearchStore, *, minimum_score: float = 0.1) -> None:
        self.store = store
        self.minimum_score = minimum_score

    def answer(self, question: str) -> Answer:
        hits = [
            hit for hit in self.store.search(question, limit=3) if hit.score >= self.minimum_score
        ]
        if not hits:
            return Answer(
                "I do not have enough trusted evidence to answer that question.", False, []
            )
        citations = [
            Citation(
                hit.chunk.chunk_id,
                hit.chunk.title,
                hit.chunk.section,
                hit.chunk.source,
                hit.chunk.version,
            )
            for hit in hits
        ]
        evidence = " ".join(hit.chunk.text for hit in hits)
        return Answer(evidence, True, citations)
