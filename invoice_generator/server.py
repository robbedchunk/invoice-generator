"""HTTP server entrypoints for invoice rendering."""

from __future__ import annotations

import atexit
import json
import multiprocessing as mp
import sys
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from concurrent.futures.process import BrokenProcessPool
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from .config import (
    LISTEN_BACKLOG,
    MAX_BODY_BYTES as MAX_BODY_BYTES_CONFIG,
    MAX_CONCURRENT_RENDERS,
    MAX_INFLIGHT_RENDERS,
    MAX_PAGES as MAX_PAGES_CONFIG,
    RENDER_QUEUE_TIMEOUT_MS,
    RENDER_TIMEOUT_MS,
)
from .net import is_client_disconnect
from .pagination import estimate_page_count, max_items_for_pages

RENDER_INFLIGHT_SEMAPHORE = threading.BoundedSemaphore(MAX_INFLIGHT_RENDERS)
RENDER_EXECUTOR_LOCK = threading.Lock()
RENDER_EXECUTOR: Optional[ProcessPoolExecutor] = None
ValidationError = Tuple[int, Dict[str, Any]]


class DependencyError(RuntimeError):
    """Raised when a required runtime dependency is missing."""


def load_render_invoice():
    try:
        from .rendering import render_invoice
    except ModuleNotFoundError as exc:
        if exc.name == "fpdf":
            raise DependencyError(
                "Missing dependency 'fpdf'. Install project dependencies with "
                "'pip install -r requirements.txt'."
            ) from exc
        raise
    return render_invoice


def create_render_executor() -> ProcessPoolExecutor:
    return ProcessPoolExecutor(
        max_workers=MAX_CONCURRENT_RENDERS,
        mp_context=mp.get_context("spawn"),
    )


def get_render_executor() -> ProcessPoolExecutor:
    global RENDER_EXECUTOR
    with RENDER_EXECUTOR_LOCK:
        if RENDER_EXECUTOR is None:
            RENDER_EXECUTOR = create_render_executor()
        return RENDER_EXECUTOR


def restart_render_executor(previous: ProcessPoolExecutor) -> ProcessPoolExecutor:
    global RENDER_EXECUTOR
    with RENDER_EXECUTOR_LOCK:
        if RENDER_EXECUTOR is previous:
            try:
                previous.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            RENDER_EXECUTOR = create_render_executor()
        if RENDER_EXECUTOR is None:
            RENDER_EXECUTOR = create_render_executor()
        return RENDER_EXECUTOR


def submit_render_job(payload: Dict[str, Any]):
    render_invoice = load_render_invoice()
    executor = get_render_executor()
    try:
        return executor.submit(render_invoice, payload)
    except BrokenProcessPool:
        return restart_render_executor(executor).submit(render_invoice, payload)


def shutdown_render_executor() -> None:
    global RENDER_EXECUTOR
    with RENDER_EXECUTOR_LOCK:
        executor = RENDER_EXECUTOR
        RENDER_EXECUTOR = None
    if executor is not None:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


atexit.register(shutdown_render_executor)


def validate_invoice_payload(
    body: bytes,
    max_pages: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[ValidationError]]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except UnicodeDecodeError:
        return None, (
            400,
            {"error": "invalid_encoding", "detail": "Body must be UTF-8 encoded JSON."},
        )
    except json.JSONDecodeError as exc:
        return None, (
            400,
            {
                "error": "invalid_json",
                "detail": f"{exc.msg} (line {exc.lineno}, column {exc.colno})",
            },
        )

    if not isinstance(payload, dict):
        return None, (
            400,
            {"error": "invalid_payload", "detail": "JSON root must be an object."},
        )

    items = payload.get("items", [])
    if items is None:
        items = []
    if not isinstance(items, list):
        return None, (
            400,
            {"error": "invalid_payload", "detail": "'items' must be an array."},
        )

    estimated_pages = estimate_page_count(len(items))
    if estimated_pages > max_pages:
        return None, (
            413,
            {
                "error": "invoice_too_large",
                "detail": f"Invoice would render {estimated_pages} pages; maximum is {max_pages}.",
                "max_items": max_items_for_pages(max_pages),
            },
        )

    return payload, None


class InvoiceHandler(BaseHTTPRequestHandler):
    MAX_BODY_BYTES = MAX_BODY_BYTES_CONFIG
    MAX_PAGES = MAX_PAGES_CONFIG

    def _write_response(self, status: int, content_type: str, body: bytes) -> bool:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True
        except Exception as exc:
            if is_client_disconnect(exc):
                return False
            raise

    def _send_json(self, status: int, payload: Dict[str, Any]) -> bool:
        body = json.dumps(payload).encode("utf-8")
        return self._write_response(status, "application/json", body)

    def _read_body(self) -> Optional[bytes]:
        header = self.headers.get("Content-Length")
        if header is None:
            self._send_json(
                411,
                {
                    "error": "missing_content_length",
                    "detail": "Content-Length header is required.",
                },
            )
            return None

        try:
            content_length = int(header)
        except ValueError:
            self._send_json(
                400,
                {
                    "error": "invalid_content_length",
                    "detail": "Content-Length must be an integer.",
                },
            )
            return None

        if content_length <= 0:
            self._send_json(400, {"error": "empty_body", "detail": "Request body cannot be empty."})
            return None

        if content_length > self.MAX_BODY_BYTES:
            self._send_json(
                413,
                {
                    "error": "payload_too_large",
                    "detail": f"Body exceeds {self.MAX_BODY_BYTES} bytes.",
                },
            )
            return None

        try:
            return self.rfile.read(content_length)
        except Exception as exc:
            if is_client_disconnect(exc):
                return None
            raise

    def do_POST(self) -> None:
        if self.path not in ("/", "/invoice", "/generate"):
            self._send_json(404, {"error": "not_found", "detail": "Unsupported endpoint."})
            return

        body = self._read_body()
        if body is None:
            return

        payload, validation_error = validate_invoice_payload(body, self.MAX_PAGES)
        if validation_error is not None:
            status, payload_body = validation_error
            self._send_json(status, payload_body)
            return

        acquired = RENDER_INFLIGHT_SEMAPHORE.acquire(timeout=RENDER_QUEUE_TIMEOUT_MS / 1000.0)
        if not acquired:
            retry_after_seconds = max(1, (RENDER_QUEUE_TIMEOUT_MS + 999) // 1000)
            self._send_json(
                503,
                {
                    "error": "server_busy",
                    "detail": "Render queue is full; retry shortly.",
                    "retry_after_ms": RENDER_QUEUE_TIMEOUT_MS,
                    "retry_after_seconds": retry_after_seconds,
                    "max_concurrent_renders": MAX_CONCURRENT_RENDERS,
                    "max_inflight_renders": MAX_INFLIGHT_RENDERS,
                },
            )
            return

        future = None
        try:
            future = submit_render_job(payload)
            pdf_bytes = future.result(timeout=RENDER_TIMEOUT_MS / 1000.0)
        except FutureTimeoutError:
            if future is not None:
                future.cancel()
            self._send_json(
                504,
                {
                    "error": "render_timeout",
                    "detail": f"Render exceeded timeout of {RENDER_TIMEOUT_MS} ms.",
                },
            )
            return
        except BrokenProcessPool:
            restart_render_executor(get_render_executor())
            self._send_json(
                503,
                {
                    "error": "render_pool_restarting",
                    "detail": "Render worker pool restarted; retry shortly.",
                },
            )
            return
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            self._send_json(500, {"error": "render_failed", "detail": str(exc)})
            return
        finally:
            RENDER_INFLIGHT_SEMAPHORE.release()

        self._write_response(200, "application/pdf", pdf_bytes)

    def do_GET(self) -> None:
        if self.path in ("/", "/health", "/healthz", "/ready"):
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not_found", "detail": "Unsupported endpoint."})

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except Exception as exc:
            if is_client_disconnect(exc):
                return
            raise

    def log_message(self, format: str, *args: Any) -> None:
        return


class InvoiceHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = LISTEN_BACKLOG


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    load_render_invoice()
    get_render_executor()
    server = InvoiceHTTPServer((host, port), InvoiceHandler)
    print(f"Invoice API server listening on http://{host}:{port}")
    server.serve_forever()
