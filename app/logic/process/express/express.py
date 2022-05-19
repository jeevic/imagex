#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Dict
from typing import Union
from app.logic.process.exception.express_exception import ExpressParseException
from app.logic.process.define import const


class Express:
    """
     处理表达式基类
    """

    # 表达式名字
    name: str

    def __str__(self):
        return self.string()

    # 获取表达式名称
    def get_name(self) -> str:

        """
            获取表达式名称
        """
        return self.name

    def parse(self, exp: Union[Dict, None] = None) -> ExpressParseException:
        """
        解析表达式
        :param exp:
        :return:
        """
        pass

    def string(self) -> str:
        """
        返回表达式的格式
        :return:
        """
        pass

    @classmethod
    def _check_number(cls, num: int, **kwargs) -> bool:
        """
         检测数字
        :param num:
        :param kwargs:
        :return:
        """
        if "min" in kwargs:
            if num < kwargs["min"]:
                return False

        if "max" in kwargs:
            if num > kwargs["max"]:
                return False

        return True

    @classmethod
    def instance(cls):
        return cls()


class AutoOrient(Express):
    """
     自动旋转
    """
    # 指令名称
    name = const.INSTRUCTION_AUTO_ORIENT
    # 旋转 0：按原图默认方向，不自动旋转；1：自适应旋转。
    o: int

    def __init__(self):
        self.name = const.INSTRUCTION_AUTO_ORIENT

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        self.o = 1
        return None

    # 获取指令
    def string(self) -> str:
        return self.get_name()


class Info(Express):
    """
     图像信息获取
    """
    # 指令名称
    name = const.INSTRUCTION_INFO

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:

        return None

    # 获取指令
    def string(self) -> str:
        return self.get_name()


class Circle(Express):
    """
     圆指令参数
    """
    # 指令名称
    name = const.INSTRUCTION_CIRCLE
    # 圆半径
    r: int = 0

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        if "r" in exp:
            try:
                r = int(exp["r"])
            except ValueError:
                raise ExpressParseException("auto orient param r is not number")
            self._check(r)
            self.r = r

        return None

    # 检测参数
    @classmethod
    def _check(cls, r: int) -> Union[ExpressParseException, None]:
        if r < 0:
            raise ExpressParseException("auto orient r:{} lt 0".format(r))
        return None

    # 获取指令
    def string(self) -> str:
        if hasattr(self, "r") and self.r > 0:
            return "%s,%s_%d" % (self.get_name(), "r", self.r)
        return self.get_name()


class Crop(Express):
    """
     裁剪参数指令
    """
    # 指令名称
    name = const.INSTRUCTION_CROP
    # 裁剪模式
    # auto, center, top, bottom, left, right
    m: str = ""

    # 裁剪起始位置X坐标
    x: int = 0

    # 裁剪起始位置Y坐标
    y: int = 0

    # 裁剪宽度
    w: int = 0

    # 裁剪高度
    h: int = 0

    # 动图是否裁剪首帧
    first: int = 0

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:

        try:

            # 解析裁剪模式
            if "m" in exp:
                m = exp["m"]
                if m not in const.IMAGE_CROP_MODES:
                    raise ExpressParseException("crop param m:{} not in modes" % m)
                self.m = m

            # 解析宽
            if "w" in exp:
                w = int(exp["w"])
                if self._check_number(w, min=1) is not True:
                    raise ExpressParseException("crop param w:{} not valid" % w)
                self.w = w

            # 解析高
            if "h" in exp:
                h = int(exp["h"])
                if self._check_number(h, min=1) is not True:
                    raise ExpressParseException("crop param h:{} not valid".format(exp["h"]))
                self.h = h

            # 解析x 坐标
            if "x" in exp:
                x = int(exp["x"])
                if self._check_number(x, min=0) is not True:
                    raise ExpressParseException("crop param x:{} not valid".format(exp["x"]))
                self.x = x

            # 解析y 坐标
            if "y" in exp:
                y = int(exp["y"])
                if self._check_number(y, min=0) is not True:
                    raise ExpressParseException("crop param y:{} not valid".format(exp["y"]))
                self.y = y

            # 解析动图首帧标志
            if "first" in exp:
                first = int(exp["first"])
                if first not in (0, const.IMAGE_CROP_FIRST_FRAME):
                    raise ExpressParseException("crop param first:{} not valid".format(exp["first"]))
                self.first = first

        except ValueError as e:
            raise ExpressParseException("crop exp parse err:{}".format(str(e)))

        return None

    # 获取指令
    def string(self) -> str:
        exp_list = [self.get_name()]

        if hasattr(self, "m") and len(self.m) > 0:
            exp_list.append("%s_%s" % ("m", self.m))

        if hasattr(self, "w") and self.w > 0:
            exp_list.append("%s_%d" % ("w", self.w))

        if hasattr(self, "h") and self.h > 0:
            exp_list.append("%s_%d" % ("h", self.h))

        if hasattr(self, "x") and self.x > 0:
            exp_list.append("%s_%d" % ("x", self.x))

        if hasattr(self, "y") and self.y > 0:
            exp_list.append("%s_%d" % ("y", self.y))

        if hasattr(self, "first") and self.first > 0:
            exp_list.append("%s_%d" % ("first", self.first))

        return ",".join(exp_list).rstrip(",")


class Ellipse(Express):
    """
     椭圆裁剪
    """
    # 指令名称
    name = const.INSTRUCTION_ELLIPSE

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        return None

    # 获取指令
    def string(self) -> str:
        return self.get_name()


class Format(Express):
    """
     格式转换
    """
    # 指令名称
    name = const.INSTRUCTION_FORMAT

    # 转换格式
    f: str = ""

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        try:
            # 解析转换格式
            if "f" in exp:
                f = exp["f"].upper()
                if f not in const.IMAGE_FORMATS:
                    raise ExpressParseException("format param f:{} not in formats" % f)
                self.f = f
        except ValueError as e:
            raise ExpressParseException("format exp parse err:{}".format(str(e)))

        return None

    # 获取指令
    def string(self) -> str:
        return "%s,%s_%s" % (self.get_name(), "f", self.f)


class Gray(Express):
    """
     图像置灰
    """
    # 指令名称
    name = const.INSTRUCTION_GRAY

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:

        return None

    # 获取指令
    def string(self) -> str:
        return self.get_name()


class InInfo(Express):
    """
     入图片信息
    """

    name = const.INSTRUCTION_ININFO
    # 长度
    len: int
    # 宽
    w: int
    # 高
    h: int
    # 缩略图宽
    resize_w: int
    # 缩略图高
    resize_h: int
    # 图片格式
    f: str
    # 动图标志 1 代表动图
    animated: int
    # 图片 id
    id: str

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        try:
            # 图片长度
            if "len" in exp:
                self.len = int(exp["len"])

            # 解析宽
            if "w" in exp:
                self.w = int(exp["w"])

            # 解析高
            if "h" in exp:
                self.h = int(exp["h"])

            # 解析resize_w 坐标
            if "rw" in exp:
                self.resize_w = int(exp["rw"])

            # 解析resize_h 坐标
            if "rh" in exp:
                self.resize_h = int(exp["rh"])

            # 解析格式
            if "f" in exp:
                self.f = exp["f"].upper()

            # 解析动图标志
            if "animated" in exp:
                self.animated = int(exp["animated"])

            # 图片 id
            if "id" in exp:
                self.id = exp["id"]

        except ValueError as e:
            raise ExpressParseException("ininfo exp parse err:{}".format(str(e)))

        return None

    def string(self):
        exp_list = [self.get_name()]

        if hasattr(self, "w") and self.w > 0:
            exp_list.append("%s_%d" % ("w", self.w))

        if hasattr(self, "h") and self.h > 0:
            exp_list.append("%s_%d" % ("h", self.h))

        if hasattr(self, "len") and self.len > 0:
            exp_list.append("%s_%d" % ("h", self.len))

        if hasattr(self, "f") and len(self.f) > 0:
            exp_list.append("%s_%s" % ("f", self.f))

        if hasattr(self, "animated") and self.animated > 0:
            exp_list.append("%s_%d" % ("animated", self.animated))

        if hasattr(self, "id") and len(self.id) > 0:
            exp_list.append("%s_%s" % ("id", self.id))

        return ",".join(exp_list).rstrip(",")


class Limit(Express):
    """
     图片限制体积
    """
    name: str = const.INSTRUCTION_LIMIT

    # 限制长度
    l: int = 0
    # 每次减少
    decr: int = 10
    # 最低大小
    min: int = 20

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        try:
            # 图片长度
            if "l" in exp:
                length = int(exp["l"])
                if self._check_number(length, min=0) is not True:
                    raise ExpressParseException("limit param l:{} not valid".format(exp["l"]))
                self.l = length

            # 每次降低
            if "decr" in exp:
                decr = int(exp["decr"])
                if self._check_number(decr, min=1, max=100) is not True:
                    raise ExpressParseException("limit param decr:{} not valid".format(exp["decr"]))
                self.decr = decr

            # 解析高
            if "min" in exp:
                m = int(exp["min"])
                if self._check_number(m, min=1, max=100) is not True:
                    raise ExpressParseException("limit param min:{} not valid".format(exp["min"]))
                self.min = m

        except ValueError as e:
            raise ExpressParseException("limit exp parse err:{}".format(str(e)))

        return None

    def string(self):
        exp_list = [self.get_name()]

        if hasattr(self, "l") and self.l > 0:
            exp_list.append("%s_%d" % ("l", self.l))

        if hasattr(self, "decr") and self.decr > 0:
            exp_list.append("%s_%d" % ("decr", self.decr))

        if hasattr(self, "min") and self.min > 0:
            exp_list.append("%s_%d" % ("min", self.min))

        return ",".join(exp_list).rstrip(",")


class Quality(Express):
    """
    图片质量设置
    """
    name = const.INSTRUCTION_QUALITY

    # 图片质量
    q: int = 90

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        try:
            # 图片质量
            if "q" in exp:
                q = int(exp["q"])
                if self._check_number(q, min=0, max=100) is not True:
                    raise ExpressParseException("quality param q:{} not valid".format(exp["q"]))
                self.q = q

        except ValueError as e:
            raise ExpressParseException("quality exp parse err:{}".format(str(e)))

        return None

    def string(self):
        exp_list = [self.get_name()]

        if hasattr(self, "q") and self.q >= 0:
            exp_list.append("%s_%d" % ("q", self.l))

        return ",".join(exp_list).rstrip(",")


class Resize(Express):
    """
     缩放参数指令
    """
    # 指令名称
    name = const.INSTRUCTION_RESIZE
    # 缩放模式
    # fixed - 强制缩放
    # lfit - 等比缩放
    # 缩放图限制为指定w与h的矩形内的最大图片
    # mfit：等比缩放，缩放图为延伸出指定w与h的矩形框外的最小图片
    m: str = ""

    # 缩放宽度
    w: int = 0

    # 缩放高度
    h: int = 0

    # 解析
    def parse(self, exp: Union[Dict, None] = None ) -> Union[ExpressParseException, None]:

        try:
            # 解析缩放模式
            if "m" in exp:
                m = exp["m"]
                if m not in const.IMAGE_RESIZE_MODES:
                    raise ExpressParseException("resize param m:{} not in modes" % m)
                self.m = m

            # 解析宽
            if "w" in exp:
                w = int(exp["w"])
                if self._check_number(w, min=0) is not True:
                    raise ExpressParseException("resize param w:{} not valid" % w)
                self.w = w

            # 解析高
            if "h" in exp:
                h = int(exp["h"])
                if self._check_number(h, min=0) is not True:
                    raise ExpressParseException("resize param h:{} not valid".format(exp["h"]))
                self.h = h

        except ValueError as e:
            raise ExpressParseException("resize exp parse err:{}".format(str(e)))

        return None

    # 获取指令
    def string(self) -> str:
        exp_list = [self.get_name()]

        if hasattr(self, "m") and len(self.m) > 0:
            exp_list.append("%s_%s" % ("m", self.m))

        if hasattr(self, "w") and self.w > 0:
            exp_list.append("%s_%d" % ("w", self.w))

        if hasattr(self, "h") and self.h > 0:
            exp_list.append("%s_%d" % ("h", self.h))

        return ",".join(exp_list).rstrip(",")


class Rotate(Express):
    """
     旋转参数指令
    """
    # 指令名称
    name = const.INSTRUCTION_ROTATE

    # 旋转角度 - 360 - 360
    a: int = 0

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:

        try:
            # 解析角度
            if "a" in exp:
                a = int(exp["a"])
                if self._check_number(a, min=-360, max=360) is not True:
                    raise ExpressParseException("rotate param a:{} not valid".format(exp["a"]))
                self.a = a

        except ValueError as e:
            raise ExpressParseException("rotate exp parse err:{}".format(str(e)))

        return None

    # 获取指令
    def string(self) -> str:
        exp_list = [self.get_name()]

        if hasattr(self, "a"):
            exp_list.append("%s_%s" % ("a", self.a))

        return ",".join(exp_list).rstrip(",")


class RoundCorners(Express):
    """
     圆角设置
    """
    name: str = const.INSTRUCTION_ROUNDED_CORNERS

    r: int = 0

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:

        try:
            # 解析角度
            if "r" in exp:
                r = int(exp["r"])
                if self._check_number(r, min=1) is not True:
                    raise ExpressParseException("round corner param a:{} not valid".format(exp["r"]))
                self.r = r

        except ValueError as e:
            raise ExpressParseException("rotate exp parse err:{}".format(str(e)))

        return None

    # 获取指令
    def string(self) -> str:
        exp_list = [self.get_name()]

        if hasattr(self, "r"):
            exp_list.append("%s_%s" % ("r", self.r))

        return ",".join(exp_list).rstrip(",")


class Strip(Express):
    """
     去掉图片的所有配置和设置  如 exif
    """
    name: str = const.INSTRUCTION_STRIP

    # 解析
    def parse(self, exp: Union[Dict, None] = None) -> Union[ExpressParseException, None]:
        pass

    # 获取指令
    def string(self) -> str:
        return self.get_name()


# 处理 map
express_map = {
    # 旋转自适应
    const.INSTRUCTION_AUTO_ORIENT: AutoOrient.instance,
    # 裁剪
    const.INSTRUCTION_CROP: Crop.instance,
    # resize 等比放
    const.INSTRUCTION_RESIZE: Resize.instance,
    # Ellipse 椭圆
    const.INSTRUCTION_ELLIPSE: Ellipse.instance,
    # Circle 圆形
    const.INSTRUCTION_CIRCLE: Circle.instance,
    # 圆角
    const.INSTRUCTION_ROUNDED_CORNERS: RoundCorners.instance,
    # 置灰
    const.INSTRUCTION_GRAY: Gray.instance,
    # 格式转换
    const.INSTRUCTION_FORMAT: Format.instance,
    # limit 限制
    const.INSTRUCTION_LIMIT: Limit.instance,
    # Quality
    const.INSTRUCTION_QUALITY: Quality.instance,
    # Rotate
    const.INSTRUCTION_ROTATE: Rotate.instance,
    # Strip
    const.INSTRUCTION_STRIP: Strip.instance,
}


if __name__ == '__main__':
    in_info = InInfo()
    in_info.parse({"wss": 2, "h": 1, "rw": 1, "rh": 2, "f": "png", "len": 111, "animated": 1, id: "111111"})
    print(in_info.string())

    limit = Limit.instance()
    limit.parse({"l": 2, "decr": 12, "min": 1})
    print(limit.string())
    limit2 = Limit.instance()
    print(limit2.string())
