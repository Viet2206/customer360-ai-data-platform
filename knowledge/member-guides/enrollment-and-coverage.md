# Enrollment, eligibility, and coverage dates

Enrollment activity and active coverage are related but different states. A submitted application, selected plan, premium payment, and effective coverage should be tracked separately.

## Coverage effective period

The effective start and end dates establish the period in which a member can be eligible under a plan. Claims compare the service date with this period. Retroactive changes, termination, reinstatement, grace periods, and reconciliation can alter eligibility after an earlier transaction, so downstream systems need effective-dated history rather than one mutable status field.

## Open and special enrollment

Marketplace open enrollment is a defined annual period. A special enrollment period may be available after qualifying life events or other qualifying circumstances. Documentation and selection deadlines apply. Current Marketplace guidance should be used because dates and eligibility rules can change.

## Dependents and policy relationships

A policy can include a subscriber and dependents with different member identifiers, coverage dates, or benefit accumulators. Family and individual deductibles may interact. Identity resolution must not merge family members merely because they share an address, phone, policy number, or subscriber relationship.

## Data matching issues

Eligibility systems may request documents when application information does not match trusted data sources. The case should preserve the disputed field, submitted value, source, deadline, requested evidence, and resolution. A data inconsistency is not proof of fraud and should not be converted into an identity match decision without evidence.

## Service workflow

For a coverage question, confirm the person, plan, service date, effective period, premium or enrollment status when relevant, and the source system timestamp. Avoid promising claim payment from eligibility alone. Document the answer and escalation because later retroactive changes can affect the record.

## Primary sources

- HealthCare.gov, Enrollment periods: https://www.healthcare.gov/coverage-outside-open-enrollment/special-enrollment-period/
- HealthCare.gov glossary: https://www.healthcare.gov/glossary/

Reviewed: September 1, 2026.

