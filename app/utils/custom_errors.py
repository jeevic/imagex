# -*- encoding: utf-8 -*-
"""
@File    : custom_errors.py
@Time    : 2021/6/22 3:21 下午
@Author  : 付夕童
@Email   : fuxitong@163.com
@Software: PyCharm
"""
from .custom_status import Status


class ExceptionServiceError(Exception):
    """
    项目基础错误
    """
    status_code = 200
    err = Status.SERVICE_ERROR

    def __init__(self, exc_detail):
        super(ExceptionServiceError, self).__init__()
        self.exc_detail = exc_detail







