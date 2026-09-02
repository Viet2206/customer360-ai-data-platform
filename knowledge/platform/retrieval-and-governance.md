# Retrieval, grounding, and access governance

The knowledge index is a rebuildable serving projection. It accelerates discovery but does not become the only trusted copy of a document or business fact.

## Corpus ingestion

Only Markdown under the configured knowledge root is indexed. Files are ordered deterministically, divided by headings, split into bounded word windows, and assigned stable content-derived chunk identifiers. Each chunk stores document ID, title, section, source path, version, text, and embedding. Rebuilding deletes and recreates the named local index.

## Hybrid retrieval

OpenSearch runs a lexical BM25 query and a vector nearest-neighbor query. Reciprocal-rank fusion combines their ranks without treating raw scores from different retrieval methods as directly comparable. The API returns the highest fused chunks with provenance. A deterministic hash embedding supports this local demo; a validated production embedding model can replace it behind the same interface.

## Grounded answers and abstention

The assistant retrieves evidence through the same store as direct document search. Chunks below the configured evidence threshold are removed. With sufficient evidence, the current assistant returns an extractive answer and citations. Without sufficient evidence, it states that trusted evidence is insufficient. It must not convert general educational material into a plan-specific promise.

## Access boundary

Streamlit does not connect directly to Delta, PostgreSQL, or OpenSearch. FastAPI is the supported query boundary. The member endpoints apply an access profile before returning direct identifiers. Document search contains no real member data. Production authentication, authorization, audit logging, encryption, network isolation, retention, and prompt-injection defenses remain deployment requirements.

## Freshness and versioning

Every public guide includes a review date and source links. Every indexed chunk includes a version. A production process should crawl or receive approved documents, validate checksums and effective dates, quarantine malformed or duplicate material, run retrieval evaluations, publish a new immutable manifest, and promote the index only after quality gates pass.

## Retrieval evaluation

A versioned query set should include cost-sharing definitions, synthetic plan questions, claims and EOB workflows, prior authorization, appeals, provider networks, pharmacy, identity resolution, quarantine, and lineage. Evaluation measures whether expected documents appear in the top results, citations remain correct, unsupported plan questions abstain, and access controls prevent member data leakage.

