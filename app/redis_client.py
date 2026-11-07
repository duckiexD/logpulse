from __future__ import annotations

import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

STREAM_KEY = "logpulse:events"
GROUP = "logpulse-workers"
STATS_LEVEL = "logpulse:stats:level"
STATS_SERVICE = "logpulse:stats:service"
STATS_STATUS = "logpulse:stats:status"
SLOW_KEY = "logpulse:slow"
SLOW_THRESHOLD = 500

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            REDIS_URL, decode_responses=True, socket_timeout=3
        )
    return _client


def set_redis(client: redis.Redis) -> None:
    global _client
    _client = client


def ensure_group(r: redis.Redis) -> None:
    try:
        r.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def publish_event(r: redis.Redis, event: dict) -> str:
    return r.xadd(STREAM_KEY, {k: str(v) for k, v in event.items()})


def update_stats(r: redis.Redis, event: dict) -> None:
    pipe = r.pipeline()
    pipe.hincrby(STATS_LEVEL, event["level"], 1)
    pipe.hincrby(STATS_SERVICE, event["service"], 1)
    pipe.hincrby(STATS_STATUS, str(event["status"]), 1)
    if int(event["duration_ms"]) >= SLOW_THRESHOLD:
        pipe.zadd(SLOW_KEY, {event["rid"]: int(event["duration_ms"])})
    pipe.execute()


def read_stats(r: redis.Redis) -> dict:
    return {
        "by_level": r.hgetall(STATS_LEVEL),
        "by_service": r.hgetall(STATS_SERVICE),
        "by_status": r.hgetall(STATS_STATUS),
    }


def top_slow(r: redis.Redis, n: int = 5) -> list[dict]:
    rows = r.zrevrange(SLOW_KEY, 0, n - 1, withscores=True)
    return [{"rid": rid, "duration_ms": int(score)} for rid, score in rows]