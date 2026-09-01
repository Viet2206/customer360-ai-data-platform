from customer360.quality.validation import validate_domains


def test_quarantines_invalid_and_orphan_records() -> None:
    domains = {
        "members": [{"source_member_id": "M1", "email": "invalid"}],
        "plans": [],
        "coverage": [
            {
                "coverage_id": "C1",
                "source_member_id": "M1",
                "coverage_start": "2025-12-31",
                "coverage_end": "2025-01-01",
            }
        ],
        "claims": [
            {
                "claim_id": "CL1",
                "source_member_id": "MISSING",
                "allowed_amount": 100.0,
                "plan_paid_amount": 80.0,
                "member_responsibility": 20.0,
            }
        ],
    }

    result = validate_domains(domains, "run-1")

    assert not result.valid["members"]
    assert not result.valid["coverage"]
    assert not result.valid["claims"]
    assert {issue["rule_id"] for issue in result.issues} == {
        "member.email_format",
        "coverage.member_exists",
        "claim.member_exists",
    }
