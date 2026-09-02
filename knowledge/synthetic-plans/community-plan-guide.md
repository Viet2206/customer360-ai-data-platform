# Synthetic Community plan guide

The Community plans are fictional products created only for this portfolio. They are not offered by an insurer and are not summaries of benefits and coverage.

## Community Silver 2500

Plan ID PLAN-SILVER-01 is the synthetic silver product for the 2025 demo year. Its generated individual annual deductible is $2,500. The deductible resets with the synthetic plan year. The current data model does not define copayments, coinsurance, out-of-pocket maximums, networks, formularies, exclusions, authorization lists, or family accumulators. The application must not invent those missing benefits.

## Community Gold 1000

Plan ID PLAN-GOLD-01 is the synthetic gold product for the 2025 demo year. Its generated individual annual deductible is $1,000. The same modeling limitation applies: only the fields published in the plan dimension are authoritative for this demo. Metal level alone must not be used to infer a copayment, coinsurance, network, or covered service.

## Claim financial fields

Synthetic claims contain billed amount, allowed amount, member responsibility, status, and service information. The Member 360 projection aggregates claim count, total allowed amount, total member responsibility, and latest claim status. Estimated plan share in the interface is allowed amount minus member responsibility; it is a display derivation and not a claim-payment ledger.

## Safe answer policy

The assistant may answer the named plan, plan identifier, metal level, deductible, coverage dates, and published claim aggregates when evidence exists. It must abstain when asked for an undefined benefit such as an emergency-room copayment or pharmacy tier. Public educational guidance may explain the concept but must not be presented as a Community plan term.

## Synthetic-data notice

Names, dates, policy numbers, claims, providers, and financial values in the local environment are generated. They do not represent real people or protected health information. The synthetic plan guide exists to test grounding, provenance, and explicit handling of missing evidence.

