# Local development runbook

1. Copy `.env.example` to `.env`.
2. Run `make install && make up`.
3. Run `customer360 generate-data --duplicates 2`.
4. Run `customer360 run-pipeline` and `customer360 publish-serving`.
5. Run `make up-apps` for the API and Streamlit interface.
6. Run `make up-ai` only when OpenSearch and Ollama are required.

Generated data is ignored by Git. Pipeline reruns with the same dataset ID return the successful prior manifest unless `--force` is supplied.

