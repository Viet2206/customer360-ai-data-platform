# Data quality, quarantine, and lineage

Quality controls establish which records are admitted to trusted layers and make every rejection inspectable.

## Bronze reconciliation

Bronze is source aligned and append only. Each release records expected files, row counts, checksums, ingestion time, dataset identifier, and pipeline run. Reconciliation detects missing, unexpected, truncated, duplicated, or changed inputs before conformance. Replaying the same dataset identifier is idempotent unless an operator explicitly forces a controlled rerun.

## Silver admission

Silver applies data types, normalization, required-field checks, domain rules, and referential validation. Valid records enter conformed domain tables. Invalid records do not disappear and are not silently coerced into plausible values. Admission rules are versioned so a later run can explain why the same source record received a different outcome.

## Quarantine record

A quarantine entry preserves the source domain, source identifier, raw or safely referenced payload, rule identifier, field, rejected value, reason, severity, observed timestamp, and pipeline run. The operator can group failures by rule and source, correct an upstream problem, and replay the affected release. Quarantine is evidence, not a trash folder.

## Gold publication

Gold contains canonical analytical facts, resolved member identities, source crosswalks, match decisions, and lineage. A publication run creates a consistent Member 360 snapshot. PostgreSQL is refreshed from that snapshot for low-latency reads. The serving database can be destroyed and rebuilt because it is not the sole owner of analytical truth.

## Observability and quality gates

Pipeline audit records track status, counts, duration, dataset version, code or configuration version, and failure details. Gates can require reconciliation success, valid schemas, acceptable quarantine rates, referential integrity, identity precision, and aggregate financial checks. A failed gate stops publication while leaving evidence for diagnosis.

## Trace a member record

Start with the golden member ID and Gold run ID from the Member 360 projection. Follow the crosswalk to source member identifiers, inspect match evidence and survivorship provenance, then locate the corresponding Silver and Bronze records by run metadata. Claims and coverage facts retain their source keys so member aggregates can be reconciled to individual facts.

