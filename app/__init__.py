#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask_log_request_id import RequestID
from flask_log_request_id import parser
from app.controller.process import process_router
from app.libs.logger import load_log
from app.setting import settings


def init_app() -> Flask:
    """
    初始化核心应用
    """
    app: Flask = Flask(__name__)

    init_config(app)

    init_logger()

    init_request_id(app)
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
