from pathlib import Path

from customer360.assistant.service import GroundedAssistant
from customer360.retrieval.core import HashEmbedder, InMemoryVectorStore, chunk_markdown


def test_grounded_answer_contains_versioned_citation() -> None:
    chunks = chunk_markdown(Path("tests/fixtures/documents/benefits.md"), max_words=30)
    store = InMemoryVectorStore(HashEmbedder())
    store.index(chunks)

    answer = GroundedAssistant(store, minimum_score=0.01).answer("What is the annual deductible?")

    assert answer.grounded
    assert "$2,500" in answer.text
    assert answer.citations
    assert answer.citations[0].title == "Community Silver Benefits"
    assert answer.citations[0].version == "v1"


def test_assistant_abstains_without_evidence() -> None:
    store = InMemoryVectorStore(HashEmbedder())

    answer = GroundedAssistant(store).answer("Can you diagnose this condition?")

    assert not answer.grounded
    assert not answer.citations
    assert "not have enough trusted evidence" in answer.text
