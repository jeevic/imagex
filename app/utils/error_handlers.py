# -*- encoding: utf-8 -*-
"""
@File    : http_error_handlers.py
@Time    : 2021/6/22 7:01 下午
@Author  : 付夕童
@Email   : fuxitong@163.com
@Software: PyCharm
"""
from traceback import format_exc
from werkzeug.exceptions import HTTPException
from werkzeug.http import HTTP_STATUS_CODES
from flask.wrappers import Response
from pydantic import ValidationError
from app.libs import logger
from .custom_status import CResponse
from .custom_status import Status


# = ===========  系统级别 ============
def http_error_handler(exc: HTTPException) -> [Response, int]:
    """
    http 通用请求错误
    """
    message = HTTP_STATUS_CODES.get(exc.code)
    if exc.code < 500:
        logger.warning(f"err_type: ServerException, err_message:{exc.description}, tb:{format_exc()}")
        return CResponse.error(code=Status.ERROR, message=message)
    logger.error(f"err_type: HTTPException, err_msg:{exc.description}, tb:{format_exc()}")
    return CResponse.error(code=Status.ERROR, message=message)


def validator_error_handler(exc: ValidationError) -> [Response, int]:
    """
    Pydantic 校验错误
    """
    cur_err = exc.errors()[-1]
    loc = cur_err.get("loc")[0]
    msg = cur_err.get("msg")
    logger.warning(f"err_type:pydantic.ValidationError, err_message:{loc}: {msg}, tb:{format_exc()}")
    return CResponse.error(code=Status.ERROR, message=f"{loc}: {msg}")


def get_error_html() -> str:
    """
      获取失败html代码
    :return:
    """
    return """
    <!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ title }}</title></head>
<body></body>
</html>
"""
