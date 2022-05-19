#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.logic.process.handle import handler
from PIL import Image
import pillow_avif
import HeifImagePlugin
from app.libs.logger import logger
import time


class Info:
    """
      获取图片信息
    """
    @classmethod
    def get_info(cls, fp=None):
        try:
            t1 = time.time()
            with Image.open(fp) as im:
                # 获取图片长度
                fp.seek(0, 2)
                length = fp.tell()
                fp.seek(0)
                info = handler.get_image_info(im)
                if info is not None:
                    info.set_length(length)
            logger.info("[info] get image info cost:{}ms".format(time.time() * 1000 - t1 * 1000))
            return info
        except Exception as e:
            logger.error("[info] get image info error:%s" % str(e))
            raise e



