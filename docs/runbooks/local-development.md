# Local development runbook

1. Copy `.env.example` to `.env`.
2. Run `make install && make up`.
3. Run `uv run customer360 generate-data --members 100 --duplicates 10 --inject-defects`.
4. Run `uv run customer360 run-pipeline --force` and `uv run customer360 publish-serving`.
5. Run `make up-search && make index-search` for the hybrid knowledge index.
6. Run `make up-apps` for the API and Streamlit workspace.
7. Verify `curl --fail http://localhost:8000/ready`, `make smoke`, and `make evaluate-search`.
8. Run `make up-ai` only when the optional Ollama runtime is required.

Generated data is ignored by Git. Pipeline reruns with the same dataset ID return the successful prior manifest unless `--force` is supplied.

The API container can rebuild and promote a content-addressed knowledge index on startup. The explicit `make index-search` step remains recommended because it verifies chunk reconciliation before the application is started.
