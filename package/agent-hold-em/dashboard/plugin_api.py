"""Thin FastAPI router for the Agent Hold 'Em plugin backend (docs/ARCHITECTURE.md §5).

Loaded by `hermes_cli/web_server_dashboard.py::_mount_plugin_api_routes` via
`spec_from_file_location` WITHOUT this directory being added to `sys.path` — so we
add it (and `_vendor/`) ourselves, exactly the pattern other dashboard plugins use
(ARCHITECTURE.md §2).

Startup here is cheap and makes no model calls: `get_service()` only restores
persisted state (a table load + local runner construction), never talks to a
provider until an actual decision is scheduled.
"""
from __future__ import annotations

import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (_DIR, os.path.join(_DIR, "_vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_hold_em.service import ServiceError, get_service

router = APIRouter()

_MAX_STR = 200


class OpponentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=_MAX_STR)
    profile_id: Optional[str] = Field(default=None, max_length=64)
    avatar: Optional[str] = Field(default=None, max_length=8)
    personality: Optional[str] = None
    model_id: Optional[str] = Field(default=None, max_length=_MAX_STR)
    kind: Optional[str] = None


class CreateTableIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opponents: list[OpponentIn]
    decision_timeout_s: Optional[float] = Field(default=None, gt=0, le=120)

    @field_validator("opponents")
    @classmethod
    def _exactly_three(cls, v: list[OpponentIn]) -> list[OpponentIn]:
        if len(v) != 3:
            raise ValueError("exactly 3 opponents are required")
        return v


class ActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1, max_length=_MAX_STR)
    expected_version: int = Field(ge=0)
    client_action_id: str = Field(min_length=1, max_length=_MAX_STR)
    kind: str = Field(min_length=1, max_length=20)
    to: Optional[int] = Field(default=None, ge=0)


class ResetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = True


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=160)


def _error_response(e: ServiceError) -> JSONResponse:
    """Top-level `{code, message, ...}` JSON body (ARCHITECTURE.md §5) — NOT wrapped in FastAPI's
    default `{"detail": ...}` envelope, since `ctx.rest` (docs/CONTRACT.md) only exposes the raw
    body via a best-effort JSON-substring scrape of the thrown Error's message, and the frontend's
    `normalizeError()` looks for `code`/`message`/`legal` at the top level.
    """
    return JSONResponse(status_code=e.status_code, content={"code": e.code, "message": e.message, **e.extra})


@router.get("/health")
def health():
    return get_service().health()


@router.get("/models")
def models(profile: Optional[str] = Query(default=None, max_length=64)):
    try:
        return get_service().models(profile_name=profile)
    except ServiceError as e:
        return _error_response(e)


@router.get("/profiles")
def profiles():
    return get_service().profiles()


@router.get("/state")
def state():
    return get_service().human_view()


@router.post("/table")
def create_table(body: CreateTableIn):
    try:
        return get_service().configure(
            [o.model_dump() for o in body.opponents], decision_timeout_s=body.decision_timeout_s,
        )
    except ServiceError as e:
        return _error_response(e)


@router.post("/action")
def act(body: ActionIn):
    try:
        return get_service().act(
            turn_id=body.turn_id, expected_version=body.expected_version,
            client_action_id=body.client_action_id, kind=body.kind, to=body.to,
        )
    except ServiceError as e:
        return _error_response(e)


@router.post("/chat")
def chat(body: ChatIn):
    try:
        return get_service().send_chat(body.text)
    except ServiceError as e:
        return _error_response(e)


@router.post("/pause")
def pause():
    return get_service().pause()


@router.post("/resume")
def resume():
    return get_service().resume()


@router.post("/next-hand")
def next_hand():
    return get_service().next_hand()


@router.post("/reset")
def reset(body: ResetIn):
    if not body.confirm:
        return JSONResponse(status_code=422, content={"code": "confirm_required", "message": "confirm must be true"})
    return get_service().reset()


@router.get("/history")
def history(limit: int = Query(default=20, ge=1, le=200)):
    return get_service().history(limit=limit)
