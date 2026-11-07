from __future__ import annotations

import logging
import os
import time

import redis

from app.redis_client import (
    GROUP, STREAM_KEY, ensure_group, get_redis, update_stats,
)

CONSUMER = os.getenv("CONSUMER_NAME", "worker-1")
BLOCK_MS = 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("logpulse.worker")


def run() -> None:
    r = get_redis()
    while True:
        try:
            r.ping()
            break
        except redis.RedisError:
            log.warning("Redis unavailable, retry in 2s")
            time.sleep(2)

    ensure_group(r)
    log.info("worker started, group=%s consumer=%s", GROUP, CONSUMER)

    while True:
        try:
            resp = r.xreadgroup(
                GROUP, CONSUMER, {STREAM_KEY: ">"}, count=10, block=BLOCK_MS
            )
        except redis.RedisError as exc:
            log.warning("Redis read error: %s", exc)
            time.sleep(2)
            continue

        if not resp:
            continue

        for _stream, messages in resp:
            for msg_id, fields in messages:
                try:
                    update_stats(r, fields)
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    log.info("processed %s", msg_id)
                except Exception as exc:  # noqa: BLE001
                    log.exception("failed to process %s: %s", msg_id, exc)


if __name__ == "__main__":
    run()