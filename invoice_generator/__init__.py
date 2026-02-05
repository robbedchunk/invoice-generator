"""Public package API for invoice generation."""

from __future__ import annotations

from typing import Any, Dict


def render_invoice(data: Dict[str, Any]) -> bytes:
    from .rendering import render_invoice as _render_invoice

    return _render_invoice(data)


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    from .server import run as _run

    _run(host, port)


__all__ = ["render_invoice", "run"]
