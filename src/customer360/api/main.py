"""Member 360 HTTP API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException, Query, Request
from prometheus_client import make_asgi_app
from sqlalchemy.engine import Engine

from customer360 import __version__
from customer360.api.schemas import (
    AssistantRequest,
    AssistantResponse,
    ClaimResponse,
    DocumentSearchResponse,
    HealthResponse,
    IdentityResponse,
    MemberResponse,
    QualityIssueResponse,
)
from customer360.assistant.service import GroundedAssistant, SearchStore
from customer360.common.config import Settings, get_settings
from customer360.retrieval.core import HashEmbedder, OpenSearchVectorStore, load_markdown_chunks
from customer360.serving.member360 import (
    build_engine,
    get_member,
    get_member_identity,
    list_member_claims,
    list_member_quality_issues,
    list_members,
)

logger = structlog.get_logger(__name__)


def _authorize_role(x_role: str = Header(default="analyst")) -> str:
    if x_role not in {"analyst", "analytics"}:
        raise HTTPException(status_code=403, detail="Unsupported role")
    return x_role


def _project_member(member: dict[str, Any], role: str) -> dict[str, Any]:
    if role == "analyst":
        return member
    masked = dict(member)
    for field in ("full_name", "date_of_birth", "email", "phone", "policy_number"):
        masked[field] = "***"
    return masked


def _project_claim(claim: dict[str, Any], role: str) -> dict[str, Any]:
    if role == "analyst":
        return claim
    masked = dict(claim)
    masked["source_member_id"] = "***"
    masked["policy_number"] = "***"
    return masked


def create_app(
    settings: Settings | None = None,
    assistant: GroundedAssistant | None = None,
    document_store: SearchStore | None = None,
) -> FastAPI:
    """Create an application with an isolated database engine lifecycle."""

    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(app_settings.database_url)
        app.state.engine = engine
        app.state.document_store = document_store
        app.state.assistant = assistant
        app.state.knowledge_error = None
        if app.state.document_store is not None and app.state.assistant is None:
            app.state.assistant = GroundedAssistant(
                app.state.document_store,
                minimum_score=app_settings.knowledge_minimum_score,
            )
        elif app_settings.knowledge_search_enabled and app.state.document_store is None:
            try:
                embedder = HashEmbedder(app_settings.knowledge_embedding_dimension)
                store = OpenSearchVectorStore(
                    app_settings.opensearch_url,
                    app_settings.knowledge_index_name,
                    embedder,
                )
                build_result = None
                if app_settings.knowledge_auto_rebuild:
                    chunks = load_markdown_chunks(app_settings.knowledge_documents_path)
                    build_result = store.rebuild(chunks)
                elif not store.is_ready():
                    raise RuntimeError(
                        f"Knowledge index alias does not exist: {app_settings.knowledge_index_name}"
                    )
                app.state.document_store = store
                app.state.assistant = app.state.assistant or GroundedAssistant(
                    store,
                    minimum_score=app_settings.knowledge_minimum_score,
                )
                logger.info(
                    "knowledge_index_ready",
                    index=app_settings.knowledge_index_name,
                    physical_index=build_result.index_name if build_result else None,
                    chunks=build_result.document_count if build_result else None,
                    changed=build_result.changed if build_result else False,
                )
            except Exception as exc:  # keep the trusted member API available
                app.state.knowledge_error = str(exc)
                logger.warning("knowledge_index_unavailable", error=str(exc))
        yield
        engine.dispose()

    app = FastAPI(
        title="Customer 360 API",
        version=__version__,
        lifespan=lifespan,
        description="Trusted API boundary over the rebuildable Member 360 serving projection.",
    )
    app.mount("/metrics", make_asgi_app())

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health(request: Request) -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "document_search": (
                "ready" if request.app.state.document_store is not None else "unavailable"
            ),
        }

    @app.get("/api/v1/members", response_model=list[MemberResponse], tags=["members"])
    def members(
        request: Request,
        limit: int = Query(100, ge=1, le=500),
        x_role: str = Header(default="analyst"),
    ) -> list[dict[str, Any]]:
        role = _authorize_role(x_role)
        engine: Engine = request.app.state.engine
        return [_project_member(row, role) for row in list_members(engine, limit=limit)]

    @app.get("/api/v1/members/{member_id}", response_model=MemberResponse, tags=["members"])
    def member(
        request: Request, member_id: str, x_role: str = Header(default="analyst")
    ) -> dict[str, Any]:
        role = _authorize_role(x_role)
        engine: Engine = request.app.state.engine
        result = get_member(engine, member_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return _project_member(result, role)

    @app.get(
        "/api/v1/members/{member_id}/claims",
        response_model=list[ClaimResponse],
        tags=["members"],
    )
    def member_claims(
        request: Request,
        member_id: str,
        x_role: str = Header(default="analyst"),
    ) -> list[dict[str, Any]]:
        role = _authorize_role(x_role)
        engine: Engine = request.app.state.engine
        if get_member(engine, member_id) is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return [_project_claim(row, role) for row in list_member_claims(engine, member_id)]

    @app.get(
        "/api/v1/members/{member_id}/identity",
        response_model=IdentityResponse,
        tags=["governance"],
    )
    def member_identity(
        request: Request,
        member_id: str,
        x_role: str = Header(default="analyst"),
    ) -> dict[str, list[dict[str, Any]]]:
        role = _authorize_role(x_role)
        if role != "analyst":
            raise HTTPException(status_code=403, detail="Identity evidence requires analyst role")
        engine: Engine = request.app.state.engine
        if get_member(engine, member_id) is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return get_member_identity(engine, member_id)

    @app.get(
        "/api/v1/members/{member_id}/quality-issues",
        response_model=list[QualityIssueResponse],
        tags=["governance"],
    )
    def member_quality_issues(
        request: Request,
        member_id: str,
        x_role: str = Header(default="analyst"),
    ) -> list[dict[str, Any]]:
        _authorize_role(x_role)
        engine: Engine = request.app.state.engine
        if get_member(engine, member_id) is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return list_member_quality_issues(engine, member_id)

    @app.post(
        "/api/v1/assistant",
        response_model=AssistantResponse,
        tags=["knowledge"],
    )
    def assistant_answer(request: Request, payload: AssistantRequest) -> dict[str, Any]:
        runtime_assistant: GroundedAssistant | None = request.app.state.assistant
        if runtime_assistant is None:
            raise HTTPException(status_code=503, detail="Knowledge index is not configured")
        return asdict(runtime_assistant.answer(payload.question))

    @app.get(
        "/api/v1/documents/search",
        response_model=list[DocumentSearchResponse],
        tags=["knowledge"],
    )
    def search_documents(
        request: Request,
        q: str = Query(min_length=3, max_length=500),
        limit: int = Query(5, ge=1, le=10),
    ) -> list[dict[str, Any]]:
        store: SearchStore | None = request.app.state.document_store
        if store is None:
            raise HTTPException(status_code=503, detail="Document search index is not configured")
        return [
            {
                "chunk_id": hit.chunk.chunk_id,
                "document_id": hit.chunk.document_id,
                "title": hit.chunk.title,
                "section": hit.chunk.section,
                "excerpt": hit.chunk.text,
                "source": hit.chunk.source,
                "version": hit.chunk.version,
                "score": hit.score,
            }
            for hit in store.search(q, limit=limit)
        ]

    return app


app = create_app()
