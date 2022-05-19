#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging.config
import os

from flask_log_request_id import RequestIDLogFilter
from . import filters

from app.setting import settings

LOGGING = {
    # 版本信息
    'version': 1,

    #
    'disable_existing_loggers': False,

    # 过滤器Filters,  我们使用RequestIDLogFilter来实现web请求的request_id追踪
    'filters': {
        'request_id_filter': {
            '()': RequestIDLogFilter
        },
        'host_ip_filter': {
            '()': filters.HostIpLogFilter
        }
    },

    # 格式化器 Formatters, 这个主要是用来格式化输出日志文件信息的, 各Hanlder 自己配置所需Format即可
    'formatters': {
        'with_request_id': {
            'format': "%(asctime)s|%(levelname)s|%(host_ip)s|%(process)d|" + \
                      "%(filename)s.%(funcName)s:%(lineno)s - request_id=%(request_id)s - %(message)s",
            # 'style': '{'
            'datefmt': '%Y-%m-%d %H:%M:%S.000'
        }
    },

    # Handler 的主要作用是将适当的日志消息（基于日志消息的严重性）分派到处理程序的指定目标
    'handlers': {
        # 控制台输出Handler, 将日志信息输出到console , 调试的时候，把日志中的的Logger 改为这个，日志信息就直接输出到控制台了
        'info': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 20,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/info.log',
            # 最小输出的日志等级
            'level': 'INFO',
            # 日志的格式化形式
            'formatter': 'with_request_id',
            # 日志的过滤形式, 由于是web请求需要request_id, 所以我们这里使用 request_id_filter
            'filters': ['request_id_filter', 'host_ip_filter'],
            # 日志的编码格式
            'encoding': 'utf8',
        },

        'error': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 2,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/error.log',
            # 最小输出的日志等级
            'level': 'ERROR',
            # 日志的格式化形式
            'formatter': 'with_request_id',
            # 日志的过滤形式, 由于是web请求需要request_id, 所以我们这里使用 request_id_filter
            'filters': ['request_id_filter', 'host_ip_filter'],
            # 日志的编码格式
            'encoding': 'utf8',
        }
    },

    # Logger对象可以添加0个或者更多个handler对象来实现几个日志需求
    'loggers': {
        # Logger 信息
        'standard': {
            # 最小输出的日志等级
            'level': 'INFO',
            # 需要的Handler, 一个是web的handler , 一个是发送到公司的日志收集器上面的
            'handlers': ['info', 'error'],
        }
    },

    # 为脚本 里面的提供地址
    # 'root': {
    #     'level': 'INFO',
    #     'handlers': ['warehouse-web']
    # }

}


def load_log():
    """
    初始化日志配置
    :return:
    """
    if 'handlers' in LOGGING:
        for key, value in LOGGING['handlers'].items():
            if not value.get('filename', ''):
                continue
            log_path = os.path.join(settings.K8S_ROOT_PATH, value['filename'])
            if not os.path.isdir(os.path.dirname(log_path)):
                try:
                    os.makedirs(os.path.dirname(log_path))
                except:
                    pass
            LOGGING['handlers'][key]['filename'] = log_path
    logging.config.dictConfig(LOGGING)


logger = logging.getLogger('standard')
