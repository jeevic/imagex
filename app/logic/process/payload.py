#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PIL import Image
from app.logic.process.express.express import Express


class ImageInfo:
    """
    图片信息类
    """
    # 图片宽
    width: int
    # 图片高
    height: int
    # 图片格式
    format: str
    # 图片长度  暂且不设置
    length: int
    # 动图标志 0 非  1是
    animated: int
    # 动图帧数设置
    number_images: int
    # 图片 id
    id: str
    # exif 信息
    exif: dict

    def __init__(self):
        pass

    def set_width(self, width):
        self.width = width

    def set_height(self, height):
        self.height = height

    def set_format(self, f: str):
        self.format = f

    def set_length(self, length):
        self.length = length

    def set_animated(self, a: int):
        self.animated = a

    def set_number_images(self, n: int):
        self.number_images = n

    def set_id(self, id: str):
        self.id = id

    def set_exif(self, exif):
        self.exif = exif

    def dumps_dict(self):
        # 输出 info 信息到 dict
        d = {}
        keys = ["width", "height", "format", "length", "animated", "number_images", "id"]
        for k in keys:
            if hasattr(self, k):
                d[k] = getattr(self, k)
        exif_map = {}
        if hasattr(self, "exif"):
            for k1, v1 in self.exif.items():
                if isinstance(v1, int):
                    exif_map[k1] = int(v1)
                elif isinstance(v1, float):
                    exif_map[k1] = float(v1)
                elif isinstance(v1, str):
                    exif_map[k1] = str(v1)
                elif isinstance(v1, bool):
                    exif_map[k1] = bool(v1)
            d['exif'] = exif_map
        return d


class ConvertFormat:
    """
    格式转换相关参数
    """
    # 转换格式
    format: str

    # 设置质量
    quality: int

    # 步长
    decr: int

    # 最小
    min: int

    # 限制大小
    limit: int


class Payload:
    """
     图片处理流
    """

    # 文件打开句柄
    im: Image

    # 表达式
    exp: Express

    # 图片信息
    image_info: ImageInfo

    # 是否需要重获取图片信息
    is_need_reinfo: bool

    # 是否需要输出图片信息
    is_output_image_info: bool

    # 转换的图片格式
    covert_format: ConvertFormat

    # 请求 id
    request_id: str

    def __init__(self):
        self.covert_format = ConvertFormat()
        pass

    # 图片句柄
    def set_im(self, im):
        self.im = im

    def get_im(self):
        return self.im

    def set_exp(self, exp):
        self.exp = exp

    def get_exp(self):
        return self.exp

    def set_image_info(self, image_info):
        self.image_info = image_info

    def get_image_info(self):
        return self.image_info

    def clear(self):
        if self.im is not None:
            self.im.close()
        self.im = None
        self.exp = None
        self.image_info = None
        self.is_output_image_info = False
        self.is_output_image_info = False
        self.covert_format = None
        self.request_id = ""











