"""Tests for the Flask 3 compatibility shim on flask-log-request-id (commit bcff2ce).

flask-log-request-id 0.10.1 lazily imports flask._app_ctx_stack (removed in Flask 2.3+)
inside flask_ctx_get_request_id(), so every logging request used to 500. The shim in
app/__init__.py replaces current_request_id.ctx_fetchers with a Flask 3 fetcher that reads
the request_id from g via current_app. These tests verify that contract.
"""
import logging

from flask import g
from flask_log_request_id import RequestIDLogFilter


def test_broken_fetcher_replaced():
    from app import current_request_id

    names = [getattr(f, "__name__", repr(f)) for f in current_request_id.ctx_fetchers]
    assert "_flask3_request_id_fetcher" in names
    assert "flask_ctx_get_request_id" not in names  # the broken one must be gone


def test_fetcher_returns_id_inside_request_context(app):
    from app import current_request_id

    with app.test_request_context("/v1/image/info", method="POST"):
        g.log_request_id = "unit-test-id"
        assert current_request_id() == "unit-test-id"


def test_fetcher_returns_none_outside_context():
    # No app/request context -> current_app raises RuntimeError -> shim raises
    # ExecutedOutsideContext -> MultiContextRequestIdFetcher swallows it -> None.
    from app import current_request_id

    assert current_request_id() is None


def test_logging_request_does_not_500(client, jpeg_bytes):
    """The core fix: a request that logs must not crash with ImportError/500."""
    resp = client.post("/v1/image/info", data={"file": (jpeg_bytes, "t.jpg")})
    assert resp.status_code == 200


def test_request_id_header_propagates_to_log_records(app, client, jpeg_bytes):
    """End-to-end: X-Request-Id header -> g -> fetcher -> RequestIDLogFilter -> log record.

    This is the gap the final reviewer flagged (smoke test only checked 200, not that the
    id actually reaches logs). A silent-None regression would fail this assertion.
    """
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    cap = Capture()
    cap.addFilter(RequestIDLogFilter())  # so record.request_id is populated like the real handlers
    log = logging.getLogger("standard")
    log.addHandler(cap)
    try:
        resp = client.post(
            "/v1/image/info",
            data={"file": (jpeg_bytes, "t.jpg")},
            headers={"X-Request-Id": "abc-123"},
        )
        assert resp.status_code == 200
        ids = [getattr(r, "request_id", None) for r in records]
        assert "abc-123" in ids, f"request_id not propagated; got ids={ids}"
    finally:
        log.removeHandler(cap)
