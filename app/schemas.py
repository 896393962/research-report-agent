from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    max_workers: int = Field(default=3, ge=1, le=5)


class Citation(BaseModel):
    index: int
    title: str
    source: str
    credibility: str
    snippet: str


class ReportResponse(BaseModel):
    report: str
    citations: list[Citation]
    trace: list[dict[str, Any]]
    quality_score: int
