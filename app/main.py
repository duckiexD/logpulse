from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis
from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.parser import ParseError, parse_line
from app.redis_client import (
    STREAM_KEY, ensure_group, get_redis, publish_event, read_stats, top_slow,
)
from app.schemas import (
    EventItem, HealthResponse, IngestError, IngestRequest,
    IngestResponse, StatsResponse,
)

log = logging.getLogger("logpulse.api")
router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_group(get_redis())
    except redis.RedisError:
        log.warning("Redis not ready at startup")
    yield


app = FastAPI(title="LogPulse", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(Exception)
async def unified_error_handler(request: Request, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "unexpected server error"},
    )


@router.get("/health", response_model=HealthResponse)
def health(r: redis.Redis = Depends(get_redis)):
    try:
        r.ping()
        return {"status": "ok", "redis": "ok"}
    except redis.RedisError:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "redis": "unavailable"},
        )


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, r: redis.Redis = Depends(get_redis)):
    accepted = 0
    errors: list[IngestError] = []

    for idx, line in enumerate(payload.lines, start=1):
        try:
            event = parse_line(line)
        except ParseError as exc:
            errors.append(IngestError(line_number=idx, reason=exc.reason))
            continue
        try:
            publish_event(r, event)
            accepted += 1
        except redis.RedisError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "redis_unavailable",
                    "detail": "cannot enqueue events",
                    "accepted": accepted,
                    "rejected": len(payload.lines) - accepted,
                },
            )

    return IngestResponse(
        accepted=accepted,
        rejected=len(payload.lines) - accepted,
        errors=errors,
    )


@router.get("/stats", response_model=StatsResponse)
def stats(r: redis.Redis = Depends(get_redis)):
    try:
        raw = read_stats(r)
        slow = top_slow(r, 5)
        processed = sum(int(v) for v in raw["by_level"].values())
        return StatsResponse(
            processed=processed,
            by_level={k: int(v) for k, v in raw["by_level"].items()},
            by_service={k: int(v) for k, v in raw["by_service"].items()},
            by_status={k: int(v) for k, v in raw["by_status"].items()},
            top_slow=slow,
        )
    except redis.RedisError:
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})


@router.get("/events", response_model=list[EventItem])
def events(
    limit: int = Query(10, ge=1, le=50),
    r: redis.Redis = Depends(get_redis),
):
    try:
        raw = r.xrevrange(STREAM_KEY, count=limit)
    except redis.RedisError:
        return JSONResponse(status_code=503, content={"error": "redis_unavailable"})
    return [EventItem(id=mid, fields=fields) for mid, fields in raw]