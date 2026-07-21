#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os.path import dirname, abspath
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.host_ip import get_host_ip

_MODE = os.getenv("MODE", "local")
_ENV_PATH = f"{abspath(dirname(abspath(dirname(dirname(__file__)))))}/env"
_ENV_FILE_MAP = {
    "local": "local.env",
    "develop": "develop.env",
    "test": "test.env",
    "perf": "perf.env",
    "prod": "prod.env",
}
_ENV_FILE = f"{_ENV_PATH}/{_ENV_FILE_MAP.get(_MODE, 'local.env')}"
print(f"> WARNING !!! 启动方式为: {_MODE}, 配置文件为 {_ENV_FILE}")


class BaseConfigs(BaseSettings):
    APP_PATH: str = abspath(dirname(dirname(__file__)))
    ROOT_PATH: str = abspath(dirname(APP_PATH))
    K8S_ROOT_PATH: str = abspath(dirname(ROOT_PATH))
    CONF_PATH: str = f"{ROOT_PATH}/conf"
    ENV_PATH: str = f"{ROOT_PATH}/env"
    LOG_PATH: str = f"{K8S_ROOT_PATH}/logs"
    TMP_PATH: str = f"{ROOT_PATH}/tmp"
    HOST_IP: str = get_host_ip() or "127.0.0.1"

    PROJECT_NAME: str
    X_REQUEST_ID: str

    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")


@lru_cache()
def get_configs():
    return BaseConfigs()