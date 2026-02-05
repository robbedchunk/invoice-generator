"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os


def env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


DEFAULT_MAX_CONCURRENT_RENDERS = max(4, min(32, os.cpu_count() or 4))
MAX_CONCURRENT_RENDERS = env_int(
    "INVOICE_MAX_CONCURRENT_RENDERS",
    DEFAULT_MAX_CONCURRENT_RENDERS,
    minimum=1,
)
MAX_INFLIGHT_RENDERS = env_int(
    "INVOICE_MAX_INFLIGHT_RENDERS",
    max(100, MAX_CONCURRENT_RENDERS * 4),
    minimum=1,
)
RENDER_QUEUE_TIMEOUT_MS = env_int("INVOICE_RENDER_QUEUE_TIMEOUT_MS", 120000, minimum=0)
RENDER_TIMEOUT_MS = env_int("INVOICE_RENDER_TIMEOUT_MS", 300000, minimum=1000)

MAX_BODY_BYTES = env_int("INVOICE_MAX_BODY_BYTES", 256 * 1024 * 1024, minimum=1024)
MAX_PAGES = env_int("INVOICE_MAX_PAGES", 10000, minimum=1)
LISTEN_BACKLOG = env_int("INVOICE_LISTEN_BACKLOG", 512, minimum=1)
