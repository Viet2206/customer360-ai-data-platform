from customer360.identity.resolution import evaluate_identity, resolve_members


def _member(source_id: str, first: str, email: str, dob: str = "1980-01-01") -> dict[str, str]:
    return {
        "source_member_id": source_id,
        "first_name": first,
        "last_name": "Nguyen",
        "full_name": f"{first} Nguyen",
        "date_of_birth": dob,
        "email": email,
        "phone": "+1-202-555-1000",
        "address_line_1": "1 Main St",
        "city": "Springfield",
        "state": "VA",
        "postal_code": "22150",
        "source_updated_at": "2025-01-01",
    }


def test_resolves_explainable_duplicate_cluster() -> None:
    result = resolve_members(
        [_member("A", "Amelia", "a@example.test"), _member("B", "Amela", "alias@example.test")]
    )

    assert len(result.members) == 1
    assert len(result.xref) == 2
    assert result.decisions[0]["decision"] == "match"
    assert result.decisions[0]["match_score"] >= 0.75
    assert result.decisions[0]["confidence_band"] == "auto_match"
    assert result.decisions[0]["decision_model_version"] == "weighted-rules-v1"

    metrics = evaluate_identity(
        result.xref,
        [{"duplicate_source_member_id": "B", "canonical_source_member_id": "A"}],
    )
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
