"""Member 360 HTTP API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from customer360 import __version__
from customer360.assistant.service import GroundedAssistant
from customer360.common.config import Settings, get_settings
from customer360.serving.member360 import build_engine, get_member, list_members


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


def create_app(
    settings: Settings | None = None, assistant: GroundedAssistant | None = None
) -> FastAPI:
    """Create an application with an isolated database engine lifecycle."""

    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(app_settings.database_url)
        app.state.engine = engine
        yield
        engine.dispose()

    app = FastAPI(
        title="Customer 360 API",
        version=__version__,
        lifespan=lifespan,
        description="Trusted API boundary over the rebuildable Member 360 serving projection.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/v1/members")
    def members(request: Request, limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
        engine: Engine = request.app.state.engine
        return list_members(engine, limit=limit)

    @app.get("/api/v1/members/{member_id}")
    def member(request: Request, member_id: str) -> dict[str, Any]:
        engine: Engine = request.app.state.engine
        result = get_member(engine, member_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return result

    @app.post("/api/v1/assistant")
    def assistant_answer(payload: AssistantRequest) -> dict[str, Any]:
        if assistant is None:
            raise HTTPException(status_code=503, detail="Knowledge index is not configured")
        return asdict(assistant.answer(payload.question))

    return app


app = create_app()
