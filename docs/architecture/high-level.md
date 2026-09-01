# High-level architecture

The platform separates systems of record from rebuildable serving projections.

![Member 360 AI Data Platform architecture](../assets/diagrams/platform-architecture.svg)

```text
Generated/public sources
        |
 Bronze Delta -> Silver Delta + quarantine -> identity resolution -> Gold Delta
                                                            |             |
                                                PostgreSQL serving    document manifest
                                                            |             |
                                                            +-- FastAPI --+-- OpenSearch
                                                                    |
                                                          Streamlit and assistant
```

## Trust boundaries

- Bronze is immutable and source aligned.
- Silver admits typed records only after boundary validation.
- Gold owns canonical analytics facts, golden member IDs, match decisions, and lineage.
- PostgreSQL and OpenSearch can be rebuilt; they never contain the only trusted copy.
- FastAPI applies persona projection before returning member data.

See the [visual architecture guide](visual-guide.md) for the governed data-product and hybrid-retrieval views.
