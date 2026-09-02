# Visual architecture guide

These diagrams describe implemented boundaries. They do not imply services or controls that are not present in the repository.

## Platform architecture

![Member 360 AI Data Platform architecture](../assets/diagrams/platform-architecture.svg)

The diagram separates three runtime zones and one cross-cutting control plane:

- **Source systems:** contract-versioned payer releases, labelled identity data, knowledge documents, and runtime configuration.
- **Delta data plane:** checksum validation, Bronze lineage, the quality admission gate, Silver conformance, quarantine, identity resolution, canonical Gold models, and pipeline audit state.
- **Serving and access plane:** atomic PostgreSQL projections, content-addressed OpenSearch indexes, the FastAPI trust boundary, operational endpoints, and the Streamlit workspace.
- **Control plane:** CLI workflows, Compose services, automated quality gates, GitHub Actions, and the current demo security boundary.

Solid arrows carry data. Dashed arrows carry configuration, lineage, evaluation labels, quality relationships, and operational telemetry. Delta Gold owns canonical analytical truth; PostgreSQL and OpenSearch remain rebuildable projections.

## Governed Member 360 data product

![Insurance Member 360 data product model](../assets/diagrams/member-360-data-model.svg)

The `member_360` projection is derived from canonical member identity, plan, coverage, and claim facts. Source crosswalks, match evidence, quality results, and run identifiers make the projection explainable and reproducible.

## Grounded hybrid retrieval

<p align="center">
  <img src="../assets/diagrams/hybrid-retrieval-flow.svg" width="760" alt="Grounded hybrid retrieval flow" />
</p>

The indexing flow creates stable, versioned chunks and stores both lexical text and embedding vectors in OpenSearch. At query time, BM25 and k-NN results are combined with reciprocal-rank fusion. Returned evidence retains its source metadata; insufficient evidence produces an explicit abstention.
