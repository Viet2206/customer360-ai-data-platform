# ADR 0001: Separate analytical truth from serving projections

Status: accepted

Delta Gold is the analytical system of record. PostgreSQL provides low-latency Member 360 reads and OpenSearch provides hybrid document retrieval. Both are published artifacts with lineage and may be destroyed and rebuilt. This prevents an application index from silently becoming the only copy of a business fact.

