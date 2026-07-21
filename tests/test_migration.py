"""Unit + artifact tests for the uv-migration deliverables (configs, logger, HEIF/AVIF, JSON, files)."""
import os
import tomllib


# --- migration artifacts ---

def test_requirements_txt_deleted():
    assert not os.path.exists("requirements.txt")


def test_pyproject_runtime_deps():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    expected = [
        "Flask>=3.1",
        "gunicorn>=23",
        "pydantic-settings>=2.5",
        "Pillow>=11",
        "pillow-heif>=0.16",
        "piexif>=1.1.3",
        "flask-log-request-id>=0.10.1",
        "concurrent-log-handler>=0.9.25",
    ]
    for d in expected:
        assert d in deps, f"missing runtime dep: {d}"


def test_python_version_pinned_to_312():
    with open(".python-version") as f:
        assert f.read().strip() == "3.12"


def test_gitignore_has_venv_and_pidfile():
    with open(".gitignore") as f:
        content = f.read()
    assert ".venv" in content
    assert "gunicorn.pid" in content


def test_gunicorn_pidfile_is_local():
    with open("gunicorn.conf.py") as f:
        content = f.read()
    assert "pidfile = 'gunicorn.pid'" in content
    assert "/var/run/gunicorn" not in content


def test_run_sh_uses_uv_run():
    with open("run.sh") as f:
        content = f.read()
    assert "uv run gunicorn -c gunicorn.conf.py main:app" in content
    assert "MODE=prod" in content


# --- configs.py pydantic v1 -> v2 ---

def test_configs_uses_pydantic_v2_basesettings():
    from pydantic_settings import BaseSettings
    from app.setting.configs import BaseConfigs

    assert issubclass(BaseConfigs, BaseSettings)
    assert hasattr(BaseConfigs, "model_config")  # v2 model_config, not v1 nested class Config


def test_settings_load_from_env():
    from app.setting import settings

    assert settings.PROJECT_NAME == "imagex service"
    assert settings.X_REQUEST_ID == "X-Request-Id"


# --- logger handler class ---

def test_logger_handlers_use_concurrent_log_handler():
    from app.libs.logger import LOGGING

    for name in ("info", "error"):
        assert LOGGING["handlers"][name]["class"] == "concurrent_log_handler.ConcurrentRotatingFileHandler"


def test_load_log_runs_without_error():
    from app.libs.logger import load_log

    load_log()  # must not raise


# --- HEIF / AVIF ---

def test_pillow_has_builtin_avif():
    from PIL import features

    assert features.check("avif")


def test_heif_save_and_read_works(app):
    """register_heif_opener() ran in init_app -> HEIF save/open works."""
    buf = __import__("io").BytesIO()
    Image = __import__("PIL.Image", fromlist=["Image"])
    Image.new("RGB", (50, 50), (1, 2, 3)).save(buf, format="HEIF")
    buf.seek(0)
    im = Image.open(buf)
    assert im.format == "HEIF"


# --- Flask 3 JSON ascii ---

def test_app_json_ensure_ascii_false(app):
    assert app.json.ensure_ascii is False


def test_json_as_ascii_removed_from_basic():
    from app.setting import basic

    assert not hasattr(basic, "JSON_AS_ASCII")


def test_jsonify_outputs_non_ascii(app):
    from flask import jsonify

    with app.test_request_context():
        resp = jsonify({"msg": "中文"})
        data = resp.get_data(as_text=True)
        assert "中文" in data  # ensure_ascii=False -> not \u-escaped
