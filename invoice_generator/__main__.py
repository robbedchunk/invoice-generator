"""Module entrypoint for running the invoice API server."""

from __future__ import annotations

import os
import sys

from .server import DependencyError, run


def main() -> None:
    host = os.getenv("INVOICE_HOST", "0.0.0.0")
    port = int(os.getenv("INVOICE_PORT", "8080"))
    try:
        run(host, port)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
