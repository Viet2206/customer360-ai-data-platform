# Open Member 360 AI Data Platform

## Project intent

Build a reproducible, open-source **US health-insurance Member 360 data platform** that demonstrates how data engineering, data quality, identity resolution, analytics, and grounded AI work together.

The platform should:

- Integrate structured, semi-structured, and unstructured member, coverage, claims, payment, interaction, provider, and plan data.
- Resolve source identities into a durable enterprise member ID with match confidence and survivorship rules.
- Preserve source history and lineage while exposing trusted, analytics-ready Gold models.
- Detect, quarantine, and remediate data-quality failures with an auditable history.
- Support both structured Member 360 queries and document-based retrieval for a member-service assistant.
- Return cited, permission-aware answers and explicitly abstain when evidence is insufficient.
- Monitor pipeline health, data quality, identity matching, retrieval, and answer quality.
- Run locally with Docker Compose and without a paid cloud subscription.

Repository name: `customer360-ai-data-platform`.

> **Scope:** This project models a health insurer/payer, not a clinical-care system. It uses synthetic data only and must not claim HIPAA compliance. Its purpose is portfolio learning and architecture demonstration, not medical advice or production use.

## Primary demo story

A member-service analyst should be able to search for a synthetic member and see:

- The reconciled profile and the source records that contributed to it.
- Current and historical coverage.
- Claims, claim status, payments, and out-of-pocket amounts.
- Recent service interactions and complaints.
- Applicable plan benefits and supporting policy documents.
- Data-quality warnings and identity-match confidence.

The assistant should answer questions such as:

- “Why is this claim still pending?”
- “What is this member's current coverage and deductible status?”
- “Which plan document supports this benefit explanation?”
- “Are there unresolved data-quality issues for this member?”

Every answer must distinguish structured facts from document evidence, include citations, and avoid inventing missing claim adjudication details.

## Data sources

Primary public or synthetic sources:

- [Synthea](https://github.com/synthetichealth/synthea): seeded synthetic patients/members, coverage, claims, encounters, payers, and transactions. Generate a versioned project dataset from a fixed seed and retain selected CSV, FHIR R4, and CPCDS outputs rather than depending only on a mutable download.
- [CMS Exchange Public Use Files](https://www.cms.gov/marketplace/resources/data/public-use-files): plans, benefits, premiums, networks, and service areas.
- [HealthCare.gov glossary and documents](https://www.healthcare.gov/glossary/): public reference content for document retrieval.

Generate additional synthetic data with known ground truth for:

- Premium and claim payments.
- Call-centre interactions, emails, and complaints.
- Website events.
- Daily member, address, coverage, and policy changes.
- Duplicate and conflicting identities used to evaluate entity resolution.

Do not commit large raw datasets. Commit versioned download/generation scripts, checksums or source metadata, schemas, licences, and small test fixtures only. A fresh clone must be able to recreate the demo data.

Public datasets that cannot be linked at member level must remain separate benchmark/reference tracks. Never create a false patient-level join merely to make the demo look more complete.

## Architecture principles

1. **Deliver one thin vertical slice first.** One member journey working end to end is more valuable than many disconnected infrastructure components.
2. **Keep raw data immutable.** Bronze data records source, ingestion time, batch/run ID, and file or record provenance.
3. **Apply quality controls at every boundary.** Validate source contracts before ingestion, business rules in Silver, and reconciliation rules in Gold.
4. **Separate canonical models from serving views.** Gold contains conformed facts and dimensions; a Member 360 serving view may be denormalized for API and analytics access.
5. **Treat identity resolution as a first-class subsystem.** Retain clusters, candidate pairs, match rules/scores, golden IDs, survivorship decisions, and manual-review status.
6. **Separate retrieval paths.** Query structured facts from trusted Gold/API models and retrieve explanatory text from indexed documents; combine them only in the answer layer.
7. **Make trust visible.** Every response should expose citations, data freshness, applicable quality warnings, and an abstention path.
8. **Design for incremental processing and replay.** Pipelines should be idempotent, partition-aware, testable, and safe to rerun.
9. **Use synthetic data and least privilege.** Classify sensitive fields, redact them from logs and prompts, and keep secrets out of source control.
10. **Preserve source meaning.** Keep original codes and values beside normalized payer concepts so transformations remain traceable and mappings can evolve.
11. **Define business semantics as code.** Version metric definitions, status mappings, monetary calculations, and source-to-target rules alongside the pipelines that implement them.

## Logical data architecture

```text
PostgreSQL sources + CSV/JSON/FHIR/CPCDS + plan data + documents
                                  |
                        Ingestion and contracts
                                  |
                 Bronze: immutable, source-aligned data
                                  |
                  Silver: typed and conformed domains
                                  |
             +--------------------+--------------------+
             |                                         |
     Identity resolution                         Document processing
 golden member ID, scores,                    parsing, chunks, metadata
 survivorship, review queue                             |
             |                                   Delta metadata +
 Gold Delta facts/dimensions                   OpenSearch hybrid/vector
             |                                         index
     Serving publisher                                  |
             |                                         |
 PostgreSQL Member 360 serving schema                   |
             +--------------------+--------------------+
                                  |
                 FastAPI trust and query boundary
                                  |
                Member UI, assistant, and analytics

Cross-cutting: data quality, lineage, audit history, metrics, tests
```

Quality validation is not a single step after Gold. Failed records should be retained with reason codes in quarantine tables, and quality results should be queryable by dataset, rule, run, and member.

## Core data model

Prefer conformed Gold facts and dimensions over one permanently flattened table:

- `dim_member` with durable `member_id` and slowly changing history.
- `member_identifier_xref` mapping source identifiers to the golden ID.
- `identity_match_decision` containing rule/score, confidence, evidence, and review state.
- `dim_plan`, `dim_provider`, `dim_date`, and relevant reference dimensions.
- `fact_coverage`, `fact_claim`, `fact_claim_line`, `fact_payment`, and `fact_interaction`.
- `dq_result`, `quarantine_record`, and pipeline audit models.
- A denormalized `member_360` serving projection optimized for API reads, analytics, and retrieval filtering.
- A `serving_publish_audit` recording which Gold version was published and whether reconciliation succeeded.

Important temporal questions must be answerable “as of” a date. Coverage, profile changes, identity mappings, and plan attributes therefore need explicit effective dates rather than destructive updates.

Canonical records should retain source-system identifiers, source codes, normalized concepts, mapping version, effective timestamps, ingestion timestamps, and lineage keys. The project may borrow person-centric and source-code-preservation conventions from OMOP, but it should not adopt the entire research-oriented OMOP model for a payer-service use case.

## Identity-resolution approach

Start with explainable matching rather than an opaque ML model:

1. Normalize names, addresses, phone numbers, emails, and dates.
2. Block candidate pairs using stable or partially stable attributes.
3. Apply deterministic rules for high-confidence matches.
4. Add probabilistic matching with [Splink](https://github.com/moj-analytical-services/splink) for ambiguous records, using DuckDB locally first and Spark only when scale justifies it.
5. Assign confidence bands: auto-match, manual review, or no match.
6. Apply field-level survivorship rules to build the golden profile.
7. Evaluate precision and recall against the generator's known duplicate ground truth.

Do not silently merge uncertain records. Store decisions so a merge can be explained and, if needed, reversed.

## Data-quality scenarios

Intentionally generate:

- Duplicate or near-duplicate members.
- Missing, malformed, or conflicting contact information.
- Inconsistent names and addresses across sources.
- Orphan claims or payments.
- Invalid or overlapping coverage dates.
- Claim totals that do not reconcile with claim lines.
- Payments that do not reconcile with member responsibility.
- Unexpected schema changes.
- Duplicate, late, missing, and out-of-order source files.

For each rule, define severity, owner, action, and repair policy. Safe deterministic corrections may be automated; ambiguous changes must be quarantined or sent to review. Never overwrite the raw value.

Organize checks into conformance, completeness, plausibility, uniqueness/integrity, reconciliation, and timeliness categories. Store thresholds and results as data so quality trends and release gates can be evaluated consistently.

## Technology stack

Use only the components required by the current delivery phase.

| Capability | Initial choice | Notes |
|---|---|---|
| Operational source | PostgreSQL | Source simulation and application metadata |
| File sources | CSV, JSON, FHIR, CPCDS, PDF/HTML | Keep source-specific adapters isolated |
| Processing | Apache Spark | Batch and incremental transformations |
| Lakehouse | Delta Lake | Bronze, Silver, Gold, schema enforcement, time travel |
| Local storage | Docker volumes/local filesystem | Add S3-compatible storage only if it proves useful |
| Data quality | Great Expectations plus SQL/PySpark tests | Contracts, business rules, and stored results |
| Entity resolution | Splink plus explicit deterministic rules | Inspectable scores, clusters, thresholds, and evaluation |
| Serving store | PostgreSQL | Rebuildable Member 360 projection for low-latency API reads |
| Vector/search store | OpenSearch | Versioned document chunks, embeddings, BM25, vector search, and metadata filters |
| Embeddings and LLM | Ollama | Local inference; model names must be configurable |
| Backend | FastAPI | Member, quality, search, and assistant endpoints |
| Demo UI | Streamlit | Member timeline, provenance, DQ, and assistant views |
| Containers | Docker Compose | Profiles keep optional services from burdening the MVP |
| Tests and CI | Pytest and GitHub Actions | Unit, contract, integration, and end-to-end tests |

Add later, after the vertical slice works:

- Apache Airflow for scheduling, backfills, and operational orchestration.
- Prometheus and Grafana for runtime/service metrics.
- Apache Superset for curated analytics dashboards.
- Kafka and Debezium for a clearly demonstrated CDC use case.
- OpenMetadata for catalog, lineage, ownership, and glossary exploration.

The code should not depend directly on Airflow so that local scripts and tests can invoke the same pipeline functions.

Delta Gold is the analytical system of record. PostgreSQL serving tables and OpenSearch indexes are rebuildable projections; neither should contain the only copy of a trusted fact or document manifest.

## Trust and access model

Even with synthetic data, demonstrate access control at the application boundary with at least two personas:

- A member-service analyst who can view the operational Member 360 fields needed to resolve an inquiry.
- An analytics user who sees de-identified or masked data and cannot use the assistant to retrieve direct identifiers.

FastAPI is the only supported query boundary for the UI and assistant. It should enforce field/row policies, validate member scope before retrieval, rate-limit expensive assistant requests, and emit audit events without logging sensitive prompt content. OpenSearch metadata filters are defence in depth, not the sole authorization mechanism.

## Delivery phases and exit criteria

### Phase 0 — Contracts and executable skeleton

- Define the demo questions, source-to-target mappings, canonical IDs, and data dictionary.
- Pin the Synthea version, seed, exporter configuration, and synthetic scenario manifest.
- Create Docker Compose, configuration conventions, test fixtures, and a one-command developer workflow.
- Exit when a clean clone can start PostgreSQL and run a smoke test.

### Phase 1 — Thin end-to-end Member 360 slice

- Ingest a small Synthea/CMS subset into Bronze.
- Conform member, coverage, and claim data in Silver.
- Produce Gold models and a minimal Member 360 API/UI.
- Exit when one synthetic member can be traced from source to serving response.

### Phase 2 — Identity resolution and data quality

- Generate labelled duplicates and data defects.
- Implement matching, survivorship, quarantine, remediation, and quality history.
- Exit when match and DQ results are explainable and measured against known ground truth.

### Phase 3 — Grounded member-service assistant

- Ingest and version public reference documents.
- Build a rebuildable, versioned OpenSearch hybrid/vector index with metadata filters, index aliases, and citations.
- Add tool/API access to structured member facts.
- Exit when the evaluation suite verifies retrieval, citations, abstention, and isolation between members.

### Phase 4 — Incremental operation and observability

- Process daily changes idempotently and support replay/backfill.
- Add orchestration and pipeline/service metrics where they add demonstrable value.
- Exit when failed and late runs can be diagnosed and safely recovered.

### Phase 5 — Portfolio hardening

- Add analytics, architecture decisions, security/threat notes, CI, screenshots, and a short demo.
- Exit when a new user can reproduce the demo from the README without undocumented steps.

## Evaluation and success measures

Report measurements produced by repeatable project tests, including dataset size and hardware context where relevant:

- Source-record counts and Bronze-to-Gold reconciliation.
- Full and incremental pipeline duration, throughput, and rerun idempotency.
- Data-quality pass rate by severity and number of quarantined/repaired records.
- Identity-resolution precision, recall, review rate, and false-merge count.
- Member 360 API p50/p95 latency and freshness.
- Retrieval recall/precision on a versioned question set.
- Citation correctness, grounded-answer rate, abstention accuracy, and cross-member leakage count.
- Automated test coverage plus contract/integration/end-to-end test results.

Avoid vague claims such as “query improvement” unless a baseline, workload, and calculation are defined.

## Repository deliverables

- Clear README and one-command quick start.
- Architecture diagram and architecture decision records.
- Reproducible, versioned data download/generation scripts.
- Source contracts, source-to-target mappings, and data dictionary.
- Bronze/Silver/Gold pipeline code and incremental-processing design.
- Identity-resolution rules, decision history, evaluation, and review workflow.
- Data-quality rules, quarantine/remediation flow, and quality history.
- Member 360 API/UI and model documentation.
- Search/RAG implementation, prompt-injection defenses, citations, and evaluation dataset.
- Automated tests and CI.
- Dashboard/UI screenshots and example assistant questions.
- Short demo video plus source, licence, and model acknowledgements.
- Limitations, privacy/security assumptions, and a clear statement that all member data is synthetic.

## GitHub projects reviewed

The solution deliberately adopts selected patterns rather than reproducing any one repository:

- [Synthea](https://github.com/synthetichealth/synthea): reproducible seeded generation and multiple healthcare export formats, including FHIR and CPCDS.
- [Healthcare Claims and EHR Lakehouse](https://github.com/ZWazir/healthcare-claims-ehr-lakehouse): a linked synthetic track for the end-to-end demo and separate handling for public datasets that cannot honestly be joined at patient level.
- [Splink](https://github.com/moj-analytical-services/splink): explainable probabilistic entity resolution, scalable from DuckDB to Spark.
- [OHDSI Common Data Model](https://github.com/OHDSI/CommonDataModel): person-centric events, standardized concepts, and preservation of original source codes; used as modelling guidance rather than adopted wholesale.
- [AWS Semantic Lakehouse sample](https://github.com/aws-samples/sample-semantic-lakehouse): semantic serving and persona-based PII filtering; adapted locally without its AWS-specific infrastructure or graph database.
- [Customer360 Platform](https://github.com/pbolla1311/customer360-platform): a versioned API boundary, idempotency, audit trails, retries, and explicit operational failure handling.
- [OpenSearch Neural Search](https://github.com/opensearch-project/neural-search): combined lexical/vector retrieval and filtered document indexes.
- [Da Vinci Burden Reduction Payer](https://github.com/HL7-DaVinci/br-payer): payer-side FHIR interoperability patterns; a future integration boundary, not an MVP dependency.

## Non-goals for the MVP

- Real protected health information or production HIPAA certification.
- Medical diagnosis, treatment advice, or automated claim adjudication.
- Real-time streaming merely for technology demonstration.
- A universal ontology covering every insurance line of business.
- Kubernetes, multi-cloud deployment, or production-scale high availability.
- Fully autonomous data repair or identity merging without auditability.

## Portfolio outcome

The finished project should demonstrate senior-level data-platform judgment: disciplined scope, reproducibility, temporal modelling, identity resolution, data contracts, quality controls, lineage, measurable AI grounding, and an honest path from a local demo toward production architecture.
