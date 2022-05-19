#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List
from app.logic.process.express.express import InInfo, express_map
from app.logic.process.define import const
from app.libs.logger import logger
from app.logic.process.exception.express_exception import ExpressParseException
from app.logic.process.exception.handler_exception import HandlerException
from PIL import Image
import pillow_avif
import HeifImagePlugin
from app.logic.process.payload import Payload, ImageInfo
from app.logic.process.handle import handler
import time
from io import BytesIO


class Result:
    # 图片二进制
    raw: bytes
    # 图片大小
    length: int
    # 图片格式
    format: str
    # 输出格式
    content_type: str
    # 输出图片信息
    is_output_image_info: bool = False
    # 图片信息
    image_info: ImageInfo

    def __init__(self):
        pass

    def clear(self):
        if isinstance(self.raw, bytes):
            self.raw = None

        if isinstance(self.image_info, ImageInfo):
            self.image_info = None


class Process:

    # 指令字段
    p_str: str
    # 指令列表
    exp_list: List

    # 总指令条数
    exp_count: int

    # 当前指令条数
    cur_exp: int

    # 处理状态  1 - 处理完成 2 - 解析完成 3 - 处理中 4 - 处理错误
    state: int

    # 入参数
    in_info: InInfo

    def __init__(self,  p_str: str):
        self.clear()
        self.p_str = p_str
        pass

    def parse(self):
        """
         解析指令
        :return:
        """

        try:
            # 存储解析实例
            exp_obj_list = []

            # 分割参数指令
            ins_list = self.p_str.split(const.INSTRUCTION_DELIMITER)

            # 遍历指令解析
            for exp_str in ins_list:
                exp_str = exp_str.strip()
                if len(exp_str) == 0 or exp_str == "":
                    # 为空 继续遍历
                    continue

                # 解析单个指令
                exp_list = exp_str.split(const.INSTRUCTION_ARG_DELIMITER)
                exp_name = exp_list[0]

                # 参数解析
                args_map = {}
                if len(exp_list) > 1:
                    args_list = exp_list[1:]
                    for arg in args_list:
                        arg_k_v = arg.split(const.INSTRUCTION_ARG_SPLIT)
                        if len(arg_k_v) > 1:
                            args_map[arg_k_v[0]] = arg_k_v[1]

                # 指令实例化
                if exp_name in express_map:
                    try:
                        exp_obj = express_map[exp_name]()
                        # 表达式内参数赋值
                        exp_obj.parse(args_map)

                        if exp_name == const.INSTRUCTION_ININFO:
                            self.in_info = exp_obj
                        else:
                            exp_obj_list.append(exp_obj)

                    except ExpressParseException as e:
                        logger.warn("[process] exp:%s parse err:%s" % (exp_name, e))
                else:
                    # 指令不存在 继续
                    continue

            if len(exp_obj_list) < 1:
                logger.warn("[process] no parse express pst:%s" % self.p_str)

            if len(exp_obj_list) == 1 and exp_obj_list[0].get_name() == const.INSTRUCTION_INFO:
                pass
            else:
                # 自旋转适应
                if len(exp_obj_list) > 0 and exp_obj_list[0].get_name() not in \
                        (const.INSTRUCTION_INFO, const.INSTRUCTION_AUTO_ORIENT):
                    exp_obj_list.insert(0, express_map[const.INSTRUCTION_AUTO_ORIENT]())

            self.exp_list = exp_obj_list
            self.exp_count = len(exp_obj_list)
            self.cur_exp = 0
            # 解析完成
            self.state = 2

            logger.info("[process] parse express p_str:{} cnt:{}".format(self.p_str, self.exp_count))
        except Exception as e:
            logger.warn("[process] process parse err:%s" % str(e))

        return None

    def handing(self, fp=None) -> Result:

        result = Result()
        # 图片大小限制 2^30次方像素  so it would require roughly 4.3 GB of RAM
        # @see  https://stackoverflow.com/questions/56174099/how-to-load-images-larger-than-max-image-pixels-with-pil
        Image.MAX_IMAGE_PIXELS = int(1024 * 1024 * 1024)
        try:
            payload = Payload()

            t1 = time.time()

            # 获取图片长度
            fp.seek(0, 2)
            length = fp.tell()
            fp.seek(0)

            self.state = 3
            # 初始化 im
            with Image.open(fp) as im:
                logger.info("[process] read image cost:%.2fms" % (time.time() * 1000 - t1 * 1000))
                # 图像句柄
                payload.im = im
                # 图片信息
                payload.image_info = handler.get_image_info(im)
                payload.image_info.set_length(length)

                logger.info("[process]origin image f:%s w:%d h:%d len:%d animated:%d", payload.image_info.format,
                            payload.image_info.width, payload.image_info.height,
                            payload.image_info.length, payload.image_info.animated)

                # 判断格式是否支持
                if payload.image_info.format not in const.IMAGE_FORMATS:
                    raise HandlerException("image format: %s not support" % payload.image_info.format)

                # 进行处理
                payload.is_need_reinfo = False
                payload.is_output_image_info = False

                # 循环处理
                for exp_obj in self.exp_list:
                    t2 = time.time()

                    self.cur_exp = self.cur_exp + 1
                    payload.set_exp(exp_obj)

                    exp_name = exp_obj.get_name()

                    if exp_name not in handler.handler_map:
                        raise HandlerException("process:%s not found" % exp_name)

                    # 调用进行处理
                    handler.handler_map[exp_name]().process(payload)

                    logger.info("[process] process:%s cur:%d cnt:%d cost:%.2fms",
                                exp_name, self.cur_exp, self.exp_count, (time.time() * 1000 - t2 * 1000))

                self.state = 1

                if payload.is_output_image_info:
                    result.is_output_image_info = True
                    result.image_info = payload.image_info
                    logger.info("[process] finish image output info cost:%.2fms", (time.time() * 1000 - t1 * 1000))
                else:
                    result.format = getattr(payload.covert_format, "format", payload.image_info.format)

                    # MPO 格式特殊处理 转为jpeg
                    if result.format == const.IMAGE_FORMAT_MPO:
                        if payload.image_info.animated == const.IMAGE_ANIMATED:
                            im1 = payload.im.copy()
                            payload.im.close()
                            payload.im = im1
                            payload.image_info.set_animated(0)
                            payload.image_info.set_number_images(1)
                        result.format = const.IMAGE_FORMAT_JPEG

                    # 判断输出是否支持
                    if result.format not in const.IMAGE_OUTPUT_FORMATS:
                        raise HandlerException("image output format: %s not support" % result.format)

                    save_all = False
                    if payload.image_info.animated == const.IMAGE_ANIMATED:
                        save_all = True

                    # 输出 type
                    content_type = const.IMAGE_FORMAT_CONTENT_TYPES[result.format]

                    # 透明度处理 或 模式处理
                    if result.format not in const.IMAGE_TRANSPARENCY_SUPPORT_FORMATS:
                        t4 = time.time()
                        bands = list(payload.im.getbands())
                        mode = payload.im.mode
                        # jpeg 不支持 P 模式
                        if result.format == const.IMAGE_FORMAT_JPEG:
                            if "A" in bands:
                                bands.remove("A")
                                mode = "".join(bands)
                            if mode not in ("L", "RGB", "CMYK"):
                                mode = "RGB"
                            im1 = payload.im.convert(mode)
                            payload.im.close()
                            payload.im = im1
                        elif "A" in bands:
                            bands.remove("A")
                            mode = "".join(bands)
                            im1 = payload.im.convert(mode)
                            payload.im.close()
                            payload.im = im1
                        logger.info("[process] image convert mode:%s cost:%dms",
                                    mode, (time.time() * 1000 - t4 * 1000))

                    # 处理转换 webP background 识别错误问题
                    if result.format == const.IMAGE_FORMAT_WEBP:
                        background = payload.im.info.get("background", None)
                        if isinstance(background, int) and payload.im.getpalette() is None:
                            if 0 <= background <= 255:
                                payload.im.info["background"] = (background, background, background, 255)
                        duration = payload.im.info.get("duration", None)
                        if isinstance(duration, float):
                            payload.im.info["duration"] = int(duration)

                    # 设置输出头
                    result.content_type = content_type

                    t3 = time.time()
                    # 无损格式处理
                    if result.format in const.IMAGE_LOSSLESS_FORMATS:
                        try:
                            bts = BytesIO()
                            payload.im.save(bts, result.format, save_all=save_all, optimize=True)
                            result.raw = bts.getvalue()
                            result.length = len(result.raw)
                        finally:
                            bts.close()
                    else:
                        # 有损格式处理
                        limit = getattr(payload.covert_format, "limit", -1)
                        quality = getattr(payload.covert_format, "quality", 90)
                        decr = getattr(payload.covert_format, "decr", 10)
                        min = getattr(payload.covert_format, "min", 20)

                        length = 0
                        raw = b""
                        # 最多五次循环
                        for i in range(5):
                            try:
                                bts = BytesIO()
                                # @see  https://github.com/python-pillow/Pillow/issues/6139 我提交的issue
                                # 随后新版本可以删除此行代码
                                if result.format == const.IMAGE_FORMAT_WEBP and save_all is True and \
                                        im.info.get("duration") is None:
                                    payload.im.save(bts, result.format, save_all=save_all, duration=0, quality=quality,
                                                    optimize=True)
                                else:
                                    payload.im.save(bts, result.format, save_all=save_all, quality=quality, optimize=True)
                                raw = bts.getvalue()
                                length = len(raw)
                            finally:
                                bts.close()

                            if (limit == 0 or limit == const.IMAGE_LENGTH_UNLIMITED or length <= limit) \
                                    or quality <= min:
                                logger.info("[handle] image limit set limit:%d  quality:%d len:%d loop:%d",
                                            limit, quality, length, i)
                                break

                            rate = length / limit
                            if rate >= 1.2:
                                quality = round(quality / rate) + 5
                            else:
                                quality = quality - decr

                        result.raw = raw
                        result.length = length

                    logger.info("[process] finish image output raw len:%d, format:%s get raw cost:%dms  all cost:%dms" %
                                (result.length, result.format, time.time() * 1000 - t3 * 1000, time.time() * 1000 - t1 * 1000))

        except HandlerException as e:
            logger.error("[process] process handler exception err:%s" % str(e))
            raise e
        except Exception as e:
            logger.error("[process] process exception:%s" % str(e))
            raise e
        finally:
            self.clear()
            if payload is not None:
                payload.clear()

        return result

    def clear(self):
        self.p_str = ""
        self.exp_list = []
        self.exp_count = 0
        self.cur_exp = 0
        self.state = 0
        self.in_info = None

