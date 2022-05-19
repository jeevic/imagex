# -*- encoding: utf-8 -*-

from typing import Dict
from typing import List
from typing import Union
from flask import request
from werkzeug.datastructures import EnvironHeaders
from app.utils.custom_status import CResponse


class Controller:

    @classmethod
    def headers(cls) -> EnvironHeaders:
        return request.headers

    @classmethod
    def cookies(cls) -> Dict:
        return request.cookies

    @classmethod
    def params(cls) -> Dict:
        return {key: value for key, value in request.args.items()}

    @classmethod
    def form(cls) -> Dict:
        return request.form.to_dict()

    @classmethod
    def body(cls) -> bytes:
        return request.data

    @classmethod
    def json(cls) -> Dict:
        return request.get_json()

    @classmethod
    def files(cls):
        return request.files

    @classmethod
    def render(cls, data: Union[Dict, List, None]):
        return CResponse.success(data=data)
