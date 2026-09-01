# High-level architecture

The platform separates systems of record from rebuildable serving projections.

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

