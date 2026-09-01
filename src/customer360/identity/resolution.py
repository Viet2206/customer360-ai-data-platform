"""Deterministic and weighted member matching for the local vertical slice."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True)
class IdentityResult:
    members: list[dict[str, Any]]
    xref: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    source_to_member: dict[str, str]


def evaluate_identity(
    xref: list[dict[str, Any]], truth_rows: list[dict[str, Any]]
) -> dict[str, int | float]:
    """Measure predicted duplicate pairs against generated ground truth."""

    truth = {
        frozenset((row["duplicate_source_member_id"], row["canonical_source_member_id"]))
        for row in truth_rows
    }
    clusters: dict[str, list[str]] = defaultdict(list)
    for row in xref:
        clusters[str(row["member_id"])].append(str(row["source_member_id"]))
    predicted = {
        frozenset(pair) for source_ids in clusters.values() for pair in combinations(source_ids, 2)
    }
    true_positive = len(predicted & truth)
    false_positive = len(predicted - truth)
    false_negative = len(truth - predicted)
    precision = true_positive / len(predicted) if predicted else float(not truth)
    recall = true_positive / len(truth) if truth else 1.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
    }


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _score(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, dict[str, float]]:
    name_left = _normalize(f"{left['first_name']} {left['last_name']}")
    name_right = _normalize(f"{right['first_name']} {right['last_name']}")
    evidence = {
        "name_similarity": SequenceMatcher(None, name_left, name_right).ratio(),
        "date_of_birth_exact": float(left["date_of_birth"] == right["date_of_birth"]),
        "email_exact": float(_normalize(left["email"]) == _normalize(right["email"])),
        "phone_exact": float(_normalize(left["phone"]) == _normalize(right["phone"])),
    }
    score = (
        evidence["name_similarity"] * 0.4
        + evidence["date_of_birth_exact"] * 0.3
        + evidence["email_exact"] * 0.2
        + evidence["phone_exact"] * 0.1
    )
    return round(score, 6), evidence


def resolve_members(rows: list[dict[str, Any]], *, match_threshold: float = 0.75) -> IdentityResult:
    """Cluster source members and retain fully inspectable pair decisions."""

    if not rows:
        raise ValueError("Cannot resolve an empty member dataset")
    ordered = sorted(rows, key=lambda row: row["source_member_id"])
    clusters: list[list[dict[str, Any]]] = []
    decisions: list[dict[str, Any]] = []
    for candidate in ordered:
        best_cluster: list[dict[str, Any]] | None = None
        best_score = 0.0
        best_evidence: dict[str, float] = {}
        best_source_id: str | None = None
        for cluster in clusters:
            representative = cluster[0]
            score, evidence = _score(candidate, representative)
            if score > best_score:
                best_cluster = cluster
                best_score = score
                best_evidence = evidence
                best_source_id = str(representative["source_member_id"])
        matched = best_cluster is not None and best_score >= match_threshold
        if matched and best_cluster is not None:
            best_cluster.append(candidate)
        else:
            clusters.append([candidate])
        if best_source_id is not None:
            decisions.append(
                {
                    "left_source_member_id": best_source_id,
                    "right_source_member_id": candidate["source_member_id"],
                    "match_score": best_score,
                    "decision": "match" if matched else "no_match",
                    **best_evidence,
                }
            )

    canonical_members: list[dict[str, Any]] = []
    xref: list[dict[str, Any]] = []
    source_to_member: dict[str, str] = {}
    for cluster in clusters:
        source_ids = sorted(str(row["source_member_id"]) for row in cluster)
        member_id = str(uuid5(NAMESPACE_URL, f"customer360:cluster:{'|'.join(source_ids)}"))
        survivor = max(cluster, key=lambda row: (row["source_updated_at"], row["source_member_id"]))
        canonical_members.append({"member_id": member_id, **survivor})
        for source_id in source_ids:
            source_to_member[source_id] = member_id
            xref.append(
                {
                    "member_id": member_id,
                    "source_member_id": source_id,
                    "cluster_size": len(source_ids),
                    "is_survivor": source_id == survivor["source_member_id"],
                }
            )
    return IdentityResult(canonical_members, xref, decisions, source_to_member)
