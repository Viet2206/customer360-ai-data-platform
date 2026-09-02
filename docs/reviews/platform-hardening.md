# Platform hardening review

This review records the implemented vertical slice and the verification applied to each boundary. The platform uses synthetic payer data only; “ready” below means portfolio-grade and reproducible, not certified for production PHI.

## Verified capability matrix

| Capability | Professional control | Verification |
|---|---|---|
| Synthetic source release | Deterministic seed, contract version, record counts, duplicate ground truth, and SHA-256 manifest | Generation, checksum-tamper, and contract tests |
| Bronze ingestion | Source-aligned records with run, batch, file, and ingestion lineage | Count reconciliation and idempotent replay tests |
| Silver conformance | Normalized domains with rule-level severity, owner, action, source key, and observed time | Valid, defective, orphan, and stale-quarantine tests |
| Delta contract evolution | Explicit schema replacement for rebuildable layers | Replay regression with an additive schema change |
| Identity resolution | Explainable weighted evidence, threshold, confidence band, model version, survivor, and source crosswalk | Labelled precision/recall and single-source tests |
| Gold data product | Canonical member, plan, coverage, claim, identity decision, crosswalk, and Member 360 models | Bronze-to-Gold and financial aggregation assertions |
| PostgreSQL serving | One-transaction replacement of member, claims, identity evidence, quality links, and publish audit | Real PostgreSQL integration tests, including quarantined identities |
| API trust boundary | Typed response models, persona projection, explicit 403/404/503 behavior, bounded query inputs | End-to-end API and masking tests |
| Operations | Liveness, dependency readiness, Prometheus endpoint, request ID, duration, and structured logs | API tests plus live container probes |
| Knowledge indexing | Content-addressed physical indexes, bulk reconciliation, strict mappings, no-op rebuild, atomic alias promotion | Real OpenSearch alias/idempotence integration test |
| Hybrid retrieval | Title/section-aware lexical ranking, deterministic vector retrieval, weighted reciprocal-rank fusion, provenance | Versioned 11-query top-5 benchmark; all queries pass |
| Grounded assistant | Evidence threshold, extractive response, citations, and explicit abstention | Citation, missing-index, and abstention tests |
| Streamlit workspace | Member profile, financial allocation, claim history, identity evidence, quality warnings, search, assistant, and masked persona | Live browser interaction against the rebuilt containers |
| Delivery workflow | Pinned environment, Compose health checks, lint, typing, coverage gate, PostgreSQL/OpenSearch CI services | `make lint`, `make test-all`, `make compose-check`, and CI workflow |

## Runtime ownership

- Delta Gold owns trusted analytical facts and lineage.
- PostgreSQL is a rebuildable low-latency serving projection.
- OpenSearch is a rebuildable knowledge-search projection reached through an atomic alias.
- FastAPI is the supported application boundary and applies persona projection before returning data.
- The UI never reads Delta, PostgreSQL, or OpenSearch directly.

## Deliberate boundaries

- Header roles demonstrate projection behavior but are not production authentication. An identity provider, signed tokens, policy enforcement, audit retention, and rate limiting are required before any real-user deployment.
- Monetary fields are suitable for the synthetic demo; a regulated implementation should standardize currency and fixed-point precision across source contracts, Delta, serving, and API schemas.
- The current resolver is explainable and small-scale. A scaled implementation needs blocked candidate generation, review-queue operations, reversible merge history, and calibrated probabilistic evaluation.
- The assistant is evidence-first and extractive. Generative synthesis should remain disabled until groundedness, citation correctness, prompt-injection, and cross-member isolation evaluations are versioned and enforced.
- Coverage history, payments, claim lines, and interactions remain future data products. The current UI accurately labels the aggregate and record-level features that are implemented.
