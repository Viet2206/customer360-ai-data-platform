# Visual architecture guide

These diagrams describe implemented boundaries. They do not imply services or controls that are not present in the repository.

## Platform architecture

![Member 360 AI Data Platform architecture](../assets/diagrams/platform-architecture.svg)

The source release is reconciled into Bronze before conformance. Quality failures are quarantined before Silver admission. Identity decisions and their evaluation remain inspectable, while Delta Gold owns canonical analytical truth. PostgreSQL and OpenSearch are rebuildable projections behind FastAPI.

## Governed Member 360 data product

![Insurance Member 360 data product model](../assets/diagrams/member-360-data-model.svg)

The `member_360` projection is derived from canonical member identity, plan, coverage, and claim facts. Source crosswalks, match evidence, quality results, and run identifiers make the projection explainable and reproducible.

## Grounded hybrid retrieval

<p align="center">
  <img src="../assets/diagrams/hybrid-retrieval-flow.svg" width="760" alt="Grounded hybrid retrieval flow" />
</p>

The indexing flow creates stable, versioned chunks and stores both lexical text and embedding vectors in OpenSearch. At query time, BM25 and k-NN results are combined with reciprocal-rank fusion. Returned evidence retains its source metadata; insufficient evidence produces an explicit abstention.
