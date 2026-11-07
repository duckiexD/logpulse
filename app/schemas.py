from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    lines: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("lines")
    @classmethod
    def _check_line_lengths(cls, v: list[str]) -> list[str]:
        for s in v:
            if not 1 <= len(s) <= 500:
                raise ValueError("each line must be 1..500 chars")
        return v


class IngestError(BaseModel):
    line_number: int
    reason: str


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[IngestError]


class StatsResponse(BaseModel):
    processed: int
    by_level: dict[str, int]
    by_service: dict[str, int]
    by_status: dict[str, int]
    top_slow: list[dict]


class HealthResponse(BaseModel):
    status: str
    redis: str


class EventItem(BaseModel):
    id: str
    fields: dict