# Member identity resolution operations

Identity resolution links source records that refer to the same real-world member while keeping every decision explainable and reversible.

## Source-aligned identity

Bronze retains the source record, source member identifier, source file, ingestion timestamp, checksum, and pipeline run. Source identifiers are not overwritten by a golden identifier. A crosswalk records the relationship between each source identity and the surviving member identity so the platform can trace and rebuild the result.

## Candidate generation

Candidate generation narrows comparisons without declaring a match. Blocking keys may use normalized email, phone, date of birth, name fragments, or other approved attributes. Multiple passes reduce the risk that one missing field prevents comparison. Blocking rules and their versions must be recorded because they shape which pairs can ever be evaluated.

## Match evidence and scoring

Exact normalized email or phone can provide strong evidence, while name and date-of-birth similarity contribute weighted evidence. Conflicts, missing values, shared household contacts, and impossible combinations can reduce confidence or trigger review. The stored decision includes pair identifiers, feature-level evidence, score, threshold version, decision, and run identifier.

## Clustering and survivorship

Accepted pairs form clusters from which a stable golden member identifier is derived. Survivorship selects a canonical value using explicit source priority, completeness, recency, and validity rules. It does not erase alternatives. Attribute-level provenance should identify which source won and why, while crosswalks preserve every linked source record.

## False merge controls

Shared address, policy, household phone, or surname is insufficient by itself. Members of one family must remain distinct unless person-level evidence supports linkage. High-impact conflicts should block automatic merging or route the pair for review. Threshold changes require labelled evaluation because a false merge can expose one person's data to another.

## Evaluation and rollback

The synthetic generator emits labelled duplicate truth so precision, recall, false positives, and false negatives can be measured. A production-like release should set minimum precision and review uncertain pairs. Because decisions are versioned and source records remain immutable, a bad matcher release can be recomputed and republished without editing history in place.

