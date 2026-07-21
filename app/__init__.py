#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, g, current_app
from flask_log_request_id import RequestID, current_request_id
from flask_log_request_id import parser
from flask_log_request_id.ctx_fetcher import ExecutedOutsideContext
from app.controller.process import process_router
from app.libs.logger import load_log
from app.setting import settings
from pillow_heif import register_heif_opener


# flask-log-request-id 0.10.1 的 flask_ctx_get_request_id 引用了 Flask 2.3 起已移除的
# _app_ctx_stack,运行时(每个带日志的请求)会抛 ImportError 导致 500。request_id 已由
# RequestID 扩展的 before_request 存到 g 上,这里把 fetcher 替换为 Flask 3 兼容版本。
def _flask3_request_id_fetcher():
    try:
        _attr = current_app.config["LOG_REQUEST_ID_G_OBJECT_ATTRIBUTE"]
    except RuntimeError:
        # 无应用上下文(非请求期间),交给 MultiContextRequestIdFetcher 返回 None
        raise ExecutedOutsideContext()
    return g.get(_attr, None)


current_request_id.ctx_fetchers = [_flask3_request_id_fetcher]


def init_app() -> Flask:
    """
    初始化核心应用
    """
    app: Flask = Flask(__name__)

    init_config(app)

    init_logger()

    init_request_id(app)

    # HEIC/HEIF 解码集中注册一次(替代各文件 import HeifImagePlugin)
    register_heif_opener()

    register_blueprints(app)

    return app


def init_logger() -> None:
    """
    初始化日志文件
    """
    load_log()


def init_request_id(app: Flask) -> None:
    """
    注册request_id
    """
    RequestID(app, request_id_parser=x_request_id)


def init_config(app: Flask) -> None:
    """
    flask 配置初始化
    """
    app.config.from_pyfile(f"{settings.APP_PATH}/setting/basic.py")
    # Flask 3 不再读 JSON_AS_ASCII,等价于原 basic.py 的 JSON_AS_ASCII = False
    app.json.ensure_ascii = False


def register_blueprints(app: Flask) -> None:
    """
    注册路由
    """
    app.register_blueprint(blueprint=process_router)


def x_request_id():
    """
     x-request-id 关联
    :return:
    """
    return parser.generic_http_header_parser_for(settings.X_REQUEST_ID or "X-Request-Id")()
