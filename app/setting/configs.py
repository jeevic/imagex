#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os.path import dirname
from os.path import abspath
from functools import lru_cache
from pydantic import BaseSettings
from app.utils.host_ip import get_host_ip


class BaseConfigs(BaseSettings):
    # 项目路径配置
    APP_PATH: str = abspath(dirname(dirname(__file__)))
    ROOT_PATH: str = abspath(dirname(APP_PATH))
    K8S_ROOT_PATH: str = abspath(dirname(ROOT_PATH))
    CONF_PATH: str = f"{ROOT_PATH}/conf"
    ENV_PATH: str = f"{ROOT_PATH}/env"
    LOG_PATH: str = f"{K8S_ROOT_PATH}/logs"
    TMP_PATH: str = f"{ROOT_PATH}/tmp"
    HOST_IP: str = get_host_ip() or "127.0.0.1"

    # 应用配置
    PROJECT_NAME: str
    # 请求 request_id
    X_REQUEST_ID: str

    class Config:
        mode = os.getenv("MODE", "local")
        env_path: str = f"{abspath(dirname(abspath(dirname(dirname(__file__)))))}/env"
        if mode == "local":
            env_file = f'{env_path}/local.env'
        elif mode == "develop":
            env_file = f'{env_path}/develop.env'
        elif mode == "test":
            env_file = f'{env_path}/test.env'
        elif mode == "perf":
            env_file = f'{env_path}/perf.env'
        elif mode == "prod":
            env_file = f"{env_path}/prod.env"
        env_file_encoding = 'utf-8'

        print(f"> WARNING !!! 启动方式为: {mode}, 配置文件为 {env_file}")


@lru_cache()
def get_configs():
    return BaseConfigs()
