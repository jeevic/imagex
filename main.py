#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app import init_app
from flask import Flask


app: Flask = init_app()


if __name__ == "__main__":
    """
    dev 环境服务启动方式    
    """
    app.run(host="0.0.0.0", port=8090, debug=False)
