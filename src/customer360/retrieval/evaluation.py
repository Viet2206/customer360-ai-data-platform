"""Repeatable retrieval evaluation against a versioned query set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from customer360.retrieval.core import SearchHit


class SearchStore(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[SearchHit]: ...


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    expected_sources: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluation:
    passed: int
    total: int
    recall_at_k: float
    failed_case_ids: tuple[str, ...]


def load_retrieval_cases(path: Path) -> list[RetrievalCase]:
    """Load and validate a compact YAML retrieval benchmark."""

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise ValueError("Retrieval evaluation file must contain a cases list")

    cases: list[RetrievalCase] = []
    for item in raw["cases"]:
        if not isinstance(item, dict):
            raise ValueError("Each retrieval case must be a mapping")
        case_id = item.get("id")
        query = item.get("query")
        sources = item.get("expected_sources")
        if (
            not isinstance(case_id, str)
            or not isinstance(query, str)
            or not isinstance(sources, list)
            or not sources
            or not all(isinstance(source, str) for source in sources)
        ):
            raise ValueError("Each retrieval case requires id, query, and expected_sources")
        cases.append(RetrievalCase(case_id, query, tuple(sources)))

    if not cases:
        raise ValueError("Retrieval evaluation must contain at least one case")
    return cases


def evaluate_retrieval(
    store: SearchStore, cases: list[RetrievalCase], *, limit: int = 5
) -> RetrievalEvaluation:
    """Measure whether an expected source appears in the top-k results."""

    failures: list[str] = []
    for case in cases:
        returned_sources = {hit.chunk.source for hit in store.search(case.query, limit=limit)}
        if returned_sources.isdisjoint(case.expected_sources):
            failures.append(case.case_id)
    passed = len(cases) - len(failures)
    return RetrievalEvaluation(
        passed=passed,
        total=len(cases),
        recall_at_k=passed / len(cases) if cases else 0.0,
        failed_case_ids=tuple(failures),
    )
