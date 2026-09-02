from pathlib import Path

import pytest

from customer360.retrieval.core import Chunk, SearchHit
from customer360.retrieval.evaluation import (
    RetrievalCase,
    evaluate_retrieval,
    load_retrieval_cases,
)


class FixedSearchStore:
    def __init__(self, sources_by_query: dict[str, list[str]]) -> None:
        self.sources_by_query = sources_by_query

    def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                Chunk(
                    chunk_id=f"chunk-{index}",
                    document_id=Path(source).stem,
                    title="Test",
                    text="Evidence",
                    source=source,
                    section="Test",
                    version="v1",
                ),
                1.0,
            )
            for index, source in enumerate(self.sources_by_query.get(query, [])[:limit])
        ]


def test_versioned_retrieval_cases_cover_the_corpus() -> None:
    cases = load_retrieval_cases(Path("knowledge/evaluation/retrieval-cases.yaml"))

    assert len(cases) == 11
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.expected_sources for case in cases)


def test_evaluate_retrieval_reports_recall_and_failures() -> None:
    cases = [
        RetrievalCase("found", "deductible", ("knowledge/cost-sharing.md",)),
        RetrievalCase("missing", "appeal", ("knowledge/appeals.md",)),
    ]
    store = FixedSearchStore(
        {
            "deductible": ["knowledge/cost-sharing.md"],
            "appeal": ["knowledge/claims.md"],
        }
    )

    result = evaluate_retrieval(store, cases, limit=3)

    assert result.passed == 1
    assert result.total == 2
    assert result.recall_at_k == 0.5
    assert result.failed_case_ids == ("missing",)


def test_retrieval_case_file_requires_cases_list(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("version: v1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cases list"):
        load_retrieval_cases(path)
