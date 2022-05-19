# -*- encoding: utf-8 -*-
"""
@File    : custom_status.py
@Time    : 2021/6/22 2:59 下午
@Author  : 付夕童
@Email   : fuxitong@163.com
@Software: PyCharm
"""
from enum import Enum
from typing import Union
from typing import Dict
from typing import List
from typing import Optional
from werkzeug.http import HTTP_STATUS_CODES
from flask import jsonify
from flask.wrappers import Response


class Status(Enum):
    """
    自定义状态码
    """

    # 系统级别
    SUCCESS = (0, "success")
    ERROR = (-1, "error")

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]


class CResponse:
    """
    自定义返回

    """
    @classmethod
    def success(
            cls,
            data: Union[Dict, List, None],
            status_code: int = 200,
            request_id: str = "",
            code: Status = Status.SUCCESS
    ) -> [Response, int]:
        """
        成功返回

        :param data: 自定义响应内容
        :param status_code: http 标准状态码
        :param request_id: 请求request_id状态码
        :param code: 自第定义状态码
        :return: jsonify，status code
        """
        default_data = [] if isinstance(data, List) else {}
        return jsonify(
            code=code.code,
            data=data if data else default_data,
            msg=code.message,
            reqeust_id=request_id
        ), status_code if status_code else 200

    @classmethod
    def error(
            cls,
            data: Union[Dict, List, None] = None,
            status_code: HTTP_STATUS_CODES = None,
            request_id: str = "",
            code: Status = Status.ERROR,
            message: Optional[str] = None
    ) -> [Response, int]:
        """
        失败返回message是可以自定义的

        :param data: 自定义响应内容 通常情况下是没有的，但是不排除特殊情况
        :param status_code: http 标准状态码
        :param request_id: 请求request_id状态码
        :param code: 自定义状态码
        :param message: 错误信息
        :return: jsonify
        """
        default_data = [] if isinstance(data, List) else {}
        return jsonify(
            code=code.code if code else 1,
            data=data if data else default_data,
            msg=message if message else code.message,
            reqeust_id=request_id
        ), status_code if status_code else 200
