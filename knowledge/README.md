# Customer 360 knowledge corpus

This directory is the searchable evidence corpus for the local portfolio application. It is deliberately separate from project documentation so retrieval favors insurance and operating knowledge instead of repository setup notes.

## Evidence classes

Member guides summarize public US health-insurance concepts from HealthCare.gov and the Centers for Medicare & Medicaid Services. They are educational summaries, not legal, medical, or plan-specific advice. Source links and review dates appear in every guide.

Synthetic plan guides describe the fictional Community Silver 2500 and Community Gold 1000 plans used by the generated demo data. These documents are test fixtures for product behavior and are not real insurance contracts.

Platform guides document how this project handles identity, data quality, lineage, retrieval, privacy, and serving projections. They explain implementation behavior, not regulatory compliance.

## Search behavior

Markdown headings define retrievable sections. Each section is split into bounded chunks with stable identifiers, embedded locally for the demo, indexed in OpenSearch, and ranked with reciprocal-rank fusion across BM25 and vector candidates. Every returned result preserves its source path, section, version, and chunk identifier.

## Source register

Primary public sources include the HealthCare.gov glossary, coverage and appeals guidance, and CMS material on medical-bill rights and interoperability. Public-source summaries were reviewed on September 1, 2026. Users should consult their current plan documents, denial notice, insurer, regulator, or qualified professional for a real case.

