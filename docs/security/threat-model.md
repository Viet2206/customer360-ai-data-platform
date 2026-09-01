# Security and privacy assumptions

This project uses synthetic data and does not claim HIPAA compliance.

Controls demonstrated:

- Analyst and masked analytics personas at the FastAPI boundary.
- No direct UI access to Delta, PostgreSQL, or OpenSearch.
- Generated secrets are local defaults and must be replaced outside development.
- Source values, match evidence, quarantine reasons, and publish lineage remain auditable.
- Assistant responses abstain without evidence and return document/version citations.

Known limitations:

- Development role selection uses a request header and is not authentication.
- Local OpenSearch security is disabled; it must never be exposed publicly.
- Prompt-injection classification and production identity-provider integration remain deployment concerns.

