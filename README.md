# Customer 360 AI Data Platform

A reproducible US health-insurance Member 360 platform for learning and demonstrating lakehouse engineering, identity resolution, data quality, governed serving, and grounded AI.

The project uses synthetic data only. It is not a production system, does not process real protected health information, and does not claim HIPAA compliance.

## Current status

The repository is being delivered in verified vertical slices. See [intent.md](intent.md) for scope, architecture, exit criteria, and non-goals.

## Prerequisites

- Docker Desktop with Docker Compose
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)

## Quick start

```bash
cp .env.example .env
make install
make test
make up
make smoke
```

Stop local services with:

```bash
make down
```

## Developer commands

```bash
make format       # Format Python code
make lint         # Static checks
make test         # Unit and contract tests
make test-all     # All local test suites
make compose-check
```

## Architecture boundary

- Delta Gold is the analytical system of record.
- PostgreSQL contains rebuildable operational and Member 360 serving projections.
- OpenSearch contains rebuildable lexical/vector indexes.
- FastAPI is the supported trust and query boundary for applications and AI tools.

