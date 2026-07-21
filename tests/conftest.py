"""Shared fixtures for the imagex uv-migration test suite."""
import io
import os

# Ensure deterministic env-file selection before the app/settings import chain runs.
os.environ.setdefault("MODE", "local")

import pytest
from PIL import Image

from app import init_app


@pytest.fixture(scope="session")
def app():
    """The Flask app, built once per session (init_app centralizes HEIF, logger, request_id)."""
    return init_app()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture
def jpeg_bytes():
    """A fresh 320x240 JPEG for each test (function-scoped so the BytesIO isn't drained across tests)."""
    buf = io.BytesIO()
    Image.new("RGB", (320, 240), (10, 20, 30)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


@pytest.fixture
def heic_bytes(app):
    """A fresh 100x100 HEIC. Depends on `app` so register_heif_opener() has run (HEIF save registered)."""
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), (40, 50, 60)).save(buf, format="HEIF")
    buf.seek(0)
    return buf
