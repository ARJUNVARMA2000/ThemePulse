"""Pydantic models for ThemePulse API."""

from pydantic import BaseModel, Field
from typing import Optional


class CreateSessionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class CreateSessionResponse(BaseModel):
    session_id: str
    admin_token: str
    student_url: str
    admin_url: str


class SessionInfoResponse(BaseModel):
    session_id: str
    question: str
    response_count: int


class SubmitResponseRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    answer: str = Field(..., min_length=1, max_length=5000)


class SubmitResponseResponse(BaseModel):
    message: str
    response_id: str


class Theme(BaseModel):
    title: str
    description: str
    student_names: list[str]


class SummaryPayload(BaseModel):
    themes: list[Theme]
    response_count: int
    model_used: Optional[str] = None
    timestamp: str
