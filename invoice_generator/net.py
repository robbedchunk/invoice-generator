"""Network-related helpers."""

from __future__ import annotations

import errno

DISCONNECT_ERRNOS = {
    errno.EPIPE,
    errno.ECONNRESET,
    errno.ETIMEDOUT,
}
if hasattr(errno, "WSAECONNRESET"):
    DISCONNECT_ERRNOS.add(errno.WSAECONNRESET)  # pragma: no cover


def is_client_disconnect(exc: BaseException) -> bool:
    if isinstance(exc, (BrokenPipeError, ConnectionResetError, TimeoutError)):
        return True
    return isinstance(exc, OSError) and exc.errno in DISCONNECT_ERRNOS
