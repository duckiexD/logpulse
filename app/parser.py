"""LogPulse — парсер логов на регулярных выражениях."""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone

# ---- Основная маска: полное совпадение строки, именованные группы ----
LOG_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+"
    r"(?P<level>INFO|WARN|ERROR)\s+"
    r"(?P<service>auth|orders|payment)\s+"
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+"
    r"(?P<method>GET|POST|PUT|DELETE)\s+"
    r"(?P<path>/\S*)\s+"
    r"(?P<status>\d{3})\s+"
    r"(?P<duration_ms>\d+)\s+"
    r"rid=(?P<rid>[0-9a-f]{16})$"
)

# ---- Три отдельных регулярных выражения: валидация/очистка полей ----
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RID_RE = re.compile(r"^[0-9a-f]{16}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9_\-/]*$")

ALLOWED_LEVELS = {"INFO", "WARN", "ERROR"}
ALLOWED_SERVICES = {"auth", "orders", "payment"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE"}


class ParseError(ValueError):
    """Ошибка разбора с указанием причины."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _parse_timestamp(value: str) -> datetime:
    if not TS_RE.fullmatch(value):
        raise ParseError("invalid timestamp format")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        raise ParseError("invalid timestamp value")


def parse_line(line: str) -> dict:
    """Разбирает одну строку лога.

    Возвращает нормализованный словарь или выбрасывает ParseError.
    """
    match = LOG_RE.fullmatch(line)
    if not match:
        raise ParseError("line does not match log format")

    data = match.groupdict()

    _parse_timestamp(data["timestamp"])

    try:
        ipaddress.IPv4Address(data["ip"])
    except ValueError:
        raise ParseError("invalid IPv4 address")

    status = int(data["status"])
    if not 100 <= status <= 599:
        raise ParseError("HTTP status out of range (100-599)")

    duration = int(data["duration_ms"])
    if not 0 <= duration <= 600000:
        raise ParseError("duration_ms out of range (0-600000)")

    if data["level"] not in ALLOWED_LEVELS:
        raise ParseError("unsupported level")
    if data["service"] not in ALLOWED_SERVICES:
        raise ParseError("unsupported service")
    if data["method"] not in ALLOWED_METHODS:
        raise ParseError("unsupported HTTP method")

    if not PATH_RE.fullmatch(data["path"]):
        raise ParseError("invalid path")
    if not RID_RE.fullmatch(data["rid"]):
        raise ParseError("invalid rid")

    return {
        "timestamp": data["timestamp"],
        "level": data["level"],
        "service": data["service"],
        "ip": data["ip"],
        "method": data["method"],
        "path": data["path"],
        "status": status,
        "duration_ms": duration,
        "rid": data["rid"],
    }