"""Typed API contracts for the trusted application boundary."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    document_search: str


class ReadinessResponse(BaseModel):
    status: str
    version: str
    database: str
    document_search: str


class MemberResponse(BaseModel):
    member_id: str
    source_member_id: str
    full_name: str
    date_of_birth: str
    email: str
    phone: str
    policy_number: str
    coverage_status: str
    coverage_start: str
    coverage_end: str
    plan_id: str
    plan_name: str
    annual_deductible: float
    claim_count: int
    total_allowed_amount: float
    total_member_responsibility: float
    latest_claim_status: str
    identity_source_count: int
    identity_confidence: str
    quality_issue_count: int
    gold_run_id: str


class ClaimResponse(BaseModel):
    claim_id: str
    member_id: str
    source_member_id: str
    policy_number: str
    service_date: str
    claim_status: str
    claim_status_reason: str
    service_category: str
    provider_name: str
    allowed_amount: float
    plan_paid_amount: float
    member_responsibility: float


class IdentitySourceResponse(BaseModel):
    member_id: str
    source_member_id: str
    cluster_size: int
    is_survivor: bool
    run_id: str


class IdentityDecisionResponse(BaseModel):
    decision_id: str
    member_id: str
    left_source_member_id: str
    right_source_member_id: str
    match_score: float
    match_threshold: float
    decision: str
    confidence_band: str
    decision_model_version: str
    run_id: str


class IdentityResponse(BaseModel):
    sources: list[IdentitySourceResponse]
    decisions: list[IdentityDecisionResponse]


class QualityIssueResponse(BaseModel):
    issue_id: str
    member_id: str | None
    dataset: str
    rule_id: str
    severity: str
    action: str
    record_key: str
    message: str
    owner: str
    observed_at: str
    run_id: str


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class CitationResponse(BaseModel):
    chunk_id: str
    title: str
    section: str
    source: str
    version: str


class AssistantResponse(BaseModel):
    text: str
    grounded: bool
    citations: list[CitationResponse]


class DocumentSearchResponse(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    section: str
    excerpt: str
    source: str
    version: str
    score: float
