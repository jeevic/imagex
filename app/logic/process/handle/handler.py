from app.logic.process.payload import Payload, ImageInfo
from app.logic.process.define import const
from app.libs.logger import logger
from app.logic.process.exception.handler_exception import HandlerException
from PIL import Image, ExifTags
import pillow_avif
import HeifImagePlugin
import time
from typing import Tuple


# 图片处理程序
class Handler:
    """
     图片处理基类
    """

    def process(self, payload: Payload):
        pass

    @classmethod
    def instance(cls):
        return cls()


class AutoOrient(Handler):
    """
    自动旋转识别处理
    """
    def __init__(self):
        pass

    def process(self, payload: Payload):
        t1 = time.time()
        exp = payload.exp
        if exp is None:
            raise HandlerException("no auto orient express!")

        is_transposed = False
        exif = {}
        try:
            exif = payload.im.getexif()
        except Exception:
            pass

        orientation = exif.get(0x0112)
        method = {
            2: Image.FLIP_LEFT_RIGHT,
            3: Image.ROTATE_180,
            4: Image.FLIP_TOP_BOTTOM,
            5: Image.TRANSPOSE,
            6: Image.ROTATE_270,
            7: Image.TRANSVERSE,
            8: Image.ROTATE_90,
        }.get(orientation)
        if method is not None:
            transposed_image = payload.im.transpose(method)
            del exif[0x0112]
            transposed_image.info["exif"] = exif.tobytes()
            payload.im = transposed_image
            is_transposed = True

        if is_transposed:
            # payload.is_need_reinfo = True
            # payload.image_info.length = 0
            pass

        t2 = time.time()
        logger.info("[handle] auto orient bool:{}, cost:{:.2f}ms".format(is_transposed, (t2 - t1) * 1000))


class Crop(Handler):
    """
     图片裁剪处理
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        """
         裁剪处理 从动图抽取一帧 或 图裁剪
        :param payload:
        :return:
        """

        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no crop express")

        number_images = payload.image_info.number_images
        # 动图判断
        if number_images > 1:
            t = time.time()
            # 如果是MPO格式 取首帧
            if payload.image_info.format == const.IMAGE_FORMAT_MPO:
                exp.first = True
            self._extract_animated_image_frame(payload.im, number_images, exp.first)

            logger.info("[handle] crop image animate image images:%d first sign:%d cost:%dms" % (number_images, exp.first, (time.time() * 1000 - t * 1000)))
            payload.is_need_reinfo = True
            # 标志改为1张
            payload.image_info.number_images = 1
            # 动图标志重置
            payload.image_info.animated = 0

        # 图片宽高获取
        ow = payload.im.width
        oh = payload.im.height

        x, y, w, h = self.crop_position(ow, oh, exp)
        logger.info("[handle] crop image params m:%s x:%d, y:%d w:%d h:%d" % (exp.m, x, y, w, h))

        # 宽高相等 不用裁剪
        if ow == w and oh == h and x == 0 and y == 0:
            return None
        # 裁剪
        payload.im = payload.im.crop((x, y, x+w, y+h))
        # 图片宽高设置
        payload.is_need_reinfo = True
        payload.image_info.set_length(0)
        payload.image_info.set_width(w)
        payload.image_info.set_height(h)

        return None

    @classmethod
    def _extract_animated_image_frame(cls, im, number_images, first):
        """
         序列图片中选取一帧
        :param im:
        :param number_images:
        :param first:
        :return:
        """
        try:
            if first == const.IMAGE_CROP_FIRST_FRAME:
                index = 0
            else:
                index = number_images // 2
            im.seek(index)
        except EOFError:
            im.seek(0)

        return None

    @classmethod
    def crop_position(cls, ow: int, oh: int, exp) -> Tuple:
        """
        裁剪位置计算
        :param ow:
        :param oh:
        :param exp:
        :return:
        """
        x, y, h, w = 0, 0, 0, 0

        # 判断 裁剪宽高
        if exp.w > ow or exp.w == 0:
            exp.w = ow

        if exp.h > oh or exp.h == 0:
            exp.h = oh

        # 处理
        if exp.x + exp.w > ow:
            exp.w = ow - exp.x

        if exp.y + exp.h > oh:
            exp.h = oh - exp.y

        mode = exp.m

        if mode == const.IMAGE_CROP_MODE_AUTO:
            # 自动裁剪
            x = exp.x
            y = exp.y
            w = exp.w
            h = exp.h

        elif mode == const.IMAGE_CROP_MODE_LEFT:
            # 左侧裁剪
            x = 0
            y = (oh - exp.h) // 2
            w = exp.w
            h = exp.h

        elif mode == const.IMAGE_CROP_MODE_RIGHT:
            # 右侧裁剪
            x = ow - exp.w
            y = (oh - exp.h) // 2
            w = exp.w
            h = exp.h

        elif mode == const.IMAGE_CROP_MODE_CENTER:
            # 居中裁剪
            x = (ow - exp.w) // 2
            y = (oh - exp.h) // 2
            w = exp.w
            h = exp.h
        elif mode == const.IMAGE_CROP_MODE_TOP:
            # 顶部裁剪
            x = (ow - exp.w) // 2
            y = 0
            w = exp.w
            h = exp.h
        elif mode == const.IMAGE_CROP_MODE_BOTTOM:
            # 底部裁剪
            x = (ow - exp.w) // 2
            y = oh - exp.h
            w = exp.w
            h = exp.h
        else:
            # 居中裁剪
            x = (ow - exp.w) // 2
            y = (oh - exp.h) // 2
            w = exp.w
            h = exp.h
        return x, y, w, h


class Resize(Handler):
    """
    图片缩放
    """
    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no resize express")

        is_animated = False
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            is_animated = True

        m = getattr(exp, "m", "auto")
        w = getattr(exp, "w", 0)
        h = getattr(exp, "h", 0)
        ow = payload.image_info.width
        oh = payload.image_info.height

        if m == const.IMAGE_RESIZE_MODE_FIXED:
            # 强制缩放
            w = w
            h = h
        elif m == const.IMAGE_RESIZE_MODE_LFIT:
            # 等比缩放图片，缩放到能放到以w、h为宽高的矩形内的最大缩放图片
            # 判断原图大小是否小于resize大小
            if w * oh > ow * h:
                w = ow * h // oh
            else:
                h = oh * w // ow
        elif m == const.IMAGE_RESIZE_MODE_MFIT:
            # 等比缩放图片，缩放到能包含住以w、h为宽高的矩形的最小缩放图片
            if w * oh > ow * h:
                h = oh * w // ow
            else:
                w = ow * h // oh

        if is_animated:
            # 跳到首帧 动图处理
            # 动图只先支持裁首帧
            payload.im.seek(0)
            im1 = payload.im.resize(size=(w, h), resample=Image.LANCZOS, reducing_gap=2.0)
            payload.im.close()
            payload.im = im1

            payload.is_need_reinfo = True
            payload.image_info.animated = False
            payload.image_info.number_images = 1
            payload.image_info.length = 0
            payload.image_info.width = w
            payload.image_info.height = h

        else:
            im1 = payload.im.resize(size=(w, h), resample=Image.LANCZOS, reducing_gap=2.0)
            payload.im.close()
            payload.im = im1
            payload.is_need_reinfo = True
            payload.image_info.length = 0
            payload.image_info.width = w
            payload.image_info.height = h

        logger.info("[handle] image resize  params m:{} ow:{} oh:{} animated:{},resize w:{} h:{}".format(
            m, ow, oh, is_animated, w, h))
        return None

    def animated_image_resize(self, im, w: int, h:int):
        pass


# ------------------------------- 椭圆处理 ------------------------

class Ellipse(Handler):
    """
     椭圆输出处理
       以图片中心为椭圆圆心 裁剪宽高为椭圆轴进行裁剪。
      png、webp默认背景为透明，jpg默认背景为白色
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no ellipse express")

        # 动图不转
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            logger.warn("[handle] ellipse can not animated image")
            return None

        # 是否需透明度标志
        is_transparency = False
        w = payload.image_info.width
        h = payload.image_info.height

        if payload.image_info.format in const.IMAGE_TRANSPARENCY_SUPPORT_FORMATS:
            is_transparency = True
            payload.im = payload.im.convert(mode="RGBA")

        if payload.im.mode not in ("RGB", "RGBA"):
            if "A" in payload.im.getbands():
                is_transparency = True
                im1 = payload.im.convert(mode="RGBA")
                payload.im.close()
                payload.im = im1
            else:
                im1 = payload.im.convert(mode="RGB")
                payload.im.close()
                payload.im = im1

        self.draw_ellipse(payload.im, w, h, is_transparency)

        payload.is_need_reinfo = True

        return True

    @classmethod
    def draw_ellipse(cls, im: Image, w: int, h: int, is_transparency: bool = False):
        """
         椭圆计算处理
         另一种处理办法 @see: https://note.nkmk.me/en/python-pillow-putalpha/
        :param self:
        :param im:
        :param w:
        :param h:
        :param is_transparency:
        :return:
        """

        color = const.IMAGE_WHITE_COLOR
        if is_transparency is True:
            color = const.IMAGE_TRANSPARENCY_WHITE_COLOR

        pixels = im.load()

        # 圆心坐标
        x0, y0 = w/2, h/2

        a2 = w/2 * w/2
        b2 = h/2 * h/2

        for i in range(w):
            for j in range(h):
                # 判断点是否在椭圆外公式 (x - x0)^2/a^2 + (y - y0)^2/b^2 > 1
                if (i - x0) * (i - x0) * b2 + (j - y0) * (j - y0) * a2 > a2 * b2:
                    pixels[i, j] = color


class Circle(Handler):
    """
     圆形裁剪
     以图片中心为圆心，从图片取出的半径为r的圆形区域，r如果超过最小边大小的一半，默认取原圆的最大内切圆。
     png、webp默认背景为透明，jpg默认背景为白色
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no circle express")

        # 动图不转
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            logger.warn("[handle] circle can not animated image")
            return None

        # 是否需透明度标志
        is_transparency = False
        w = payload.image_info.width
        h = payload.image_info.height

        if payload.image_info.format in const.IMAGE_TRANSPARENCY_SUPPORT_FORMATS:
            is_transparency = True
            payload.im = payload.im.convert(mode="RGBA")

        if payload.im.mode not in ("RGB", "RGBA"):
            if "A" in payload.im.getbands():
                is_transparency = True
                im1 = payload.im.convert(mode="RGBA")
                payload.im.close()
                payload.im = im1
            else:
                im1 = payload.im.convert(mode="RGB")
                payload.im.close()
                payload.im = im1

        # 半径
        r = exp.r
        width = payload.image_info.width
        height = payload.image_info.height

        rd = 0
        if r == 0:
            rd = min(width, height)
        else:
            rd = min(r * 2, width, height)

        r = rd // 2

        self.draw_circle(payload.im, width, height, r, is_transparency)

        logger.info("[handle] circle img f:{}, w:{}, h:{} params: r:{},  isTransparency:{}".format(
            payload.image_info.format, width, height, r, is_transparency))

        payload.is_need_reinfo = True

        return None

    @classmethod
    def draw_circle(cls, im: Image, w: int, h: int, r: int, is_transparency: bool = False):
        """
         椭圆计算处理
         另一种处理办法 @see: https://note.nkmk.me/en/python-pillow-putalpha/
        :param self:
        :param im:
        :param w:
        :param h:
        :param r:
        :param is_transparency:
        :return:
        """

        color = const.IMAGE_WHITE_COLOR
        if is_transparency is True:
            color = const.IMAGE_TRANSPARENCY_WHITE_COLOR

        pixels = im.load()

        # 圆心坐标
        x0, y0 = w / 2, h / 2

        r2 = r * r

        for i in range(w):
            for j in range(h):
                # 判断点是否在椭圆外公式 (x - x0)^2/a^2 + (y - y0)^2/b^2 > 1
                if (i - x0) * (i - x0) + (j - y0) * (j - y0) > r2:
                    pixels[i, j] = color


class RoundCorners(Handler):
    """
     四个圆角设置
    """
    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no round-corners express")

        # 动图不处理
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            logger.warn("[handle] round-corners can not animated image")
            return None

        ow = payload.image_info.width
        oh = payload.image_info.height

        is_transparency = False

        if payload.image_info.format in const.IMAGE_TRANSPARENCY_SUPPORT_FORMATS:
            is_transparency = True
            payload.im = payload.im.convert(mode="RGBA")

        if payload.im.mode not in ("RGB", "RGBA"):
            if "A" in payload.im.getbands():
                is_transparency = True
                im1 = payload.im.convert(mode="RGBA")
                payload.im.close()
                payload.im = im1
            else:
                im1 = payload.im.convert(mode="RGB")
                payload.im.close()
                payload.im = im1

        r = getattr(exp, "r", 0)

        if r == 0:
            r = min(ow//2, oh//2)
        else:
            r = min(r, ow//2, oh//2)

        self.draw_round_corners(payload.im, ow, oh, r, is_transparency)

        logger.info("[handle]image rounded corners  params: r:%d f:%s ow:%d oh:%d",
                     r, payload.image_info.format, ow, oh)

    @classmethod
    def draw_round_corners(cls, im: Image, w: int, h: int, r: int, is_transparency: bool = False):
        """
          画圆角
        :param cls:
        :param im:
        :param w:
        :param h:
        :param r:
        :param is_transparency:
        :return:
        """
        color = const.IMAGE_WHITE_COLOR
        if is_transparency is True:
            color = const.IMAGE_TRANSPARENCY_WHITE_COLOR

        # 圆心位置
        cx, cy = 0, 0
        r2 = r * r

        pixels = im.load()

        # 左上角 top-left
        cx, cy = r, r
        for i in range(cx):
            for j in range(cy):
                if (i - cx) * (i - cx) + (j - cy) * (j - cy) > r2:
                    pixels[i, j] = color

        # 右上角 top-right
        cx, cy = w - r, r
        for i in range(w - r, w):
            for j in range(cy):
                if (i - cx) * (i - cx) + (j - cy) * (j - cy) > r2:
                    pixels[i, j] = color

        # 左下角 bottom-left
        cx, cy = r, h - r
        for i in range(r):
            for j in range(cy, h):
                if (i - cx) * (i - cx) + (j - cy) * (j - cy) > r2:
                    pixels[i, j] = color
        # 右下角
        cx, cy = w - r, h - r
        for i in range(cx, w):
            for j in range(cy, h):
                if (i - cx) * (i - cx) + (j - cy) * (j - cy) > r2:
                    pixels[i, j] = color


class Gray(Handler):
    """
    图片置灰需最后操作

    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no gray express")

        # 动图不转
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            logger.warn("[handle] gray can not animated image")
            return None

        is_transparency = False
        if payload.image_info.format in const.IMAGE_TRANSPARENCY_SUPPORT_FORMATS:
            is_transparency = True

        else:
            if "A" in payload.im.getbands():
                is_transparency = True

        mode = "L"
        if is_transparency:
            mode = "LA"

        im1 = payload.im.convert(mode)
        payload.im.close()
        payload.im = im1

        # 设置后
        # 图片长度改变
        payload.is_need_reinfo = True
        payload.image_info.set_length(0)

        logger.info("[handle] gray image")


class Format(Handler):

    """
      图片转换格式
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no format express")

        f = exp.f

        if f == "":
            f = payload.image_info.format

        # pillow 识别jpg 为 jpeg
        if f == const.IMAGE_FORMAT_JPG:
            f = const.IMAGE_FORMAT_JPEG

        # 处理MPO 多图形式
        if payload.image_info.format == const.IMAGE_FORMAT_MPO and payload.image_info.animated == const.IMAGE_ANIMATED:
            im1 = payload.im.copy()
            payload.im.close()
            payload.im = im1
            payload.image_info.set_animated(0)
            payload.image_info.set_number_images(1)

        # JPEG CMYK 模式处理
        if payload.im.mode == "CMYK" and f != const.IMAGE_FORMAT_JPEG:
            payload.im = payload.im.convert("RGB")

        # 设置格式
        payload.covert_format.format = f
        payload.image_info.format = f

        payload.is_need_reinfo = True
        payload.image_info.set_length(0)

        if payload.image_info.animated == const.IMAGE_ANIMATED:
            # 判断是否是转成非动画图
            if f not in const.IMAGE_ANIMATED_SUPPORT_FORMATS:
                payload.image_info.set_animated(0)
                payload.image_info.set_number_images(1)

            # 大多数浏览器兼容不了 apng 直接设置静图显示
            if payload.im.format == const.IMAGE_FORMAT_PNG:
                payload.image_info.set_animated(0)
                payload.image_info.set_number_images(1)

            logger.info("[handle] format transform animated to none")

        logger.info("[handle] format image f:%s " % f)


class Limit(Handler):

    """
     设置体积限制
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no limit express")

        l = getattr(exp, "l", const.IMAGE_LENGTH_UNLIMITED)
        decr = getattr(exp, "decr", 10)
        min = getattr(exp, "min", 20)

        payload.covert_format.limit = l
        payload.covert_format.decr = decr
        payload.covert_format.min = min

        logger.info("[handler] image limit set l:{} decr:{}, min:{}".format(l, decr, min))


class Quality(Handler):
    """
      设置图片质量
    """

    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no quality express")

        q = getattr(exp, "q", -1)

        payload.covert_format.quality = q

        logger.info("[handler] image quality set q:{}".format(q))


class Rotate(Handler):
    """
    旋转操作
    """
    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no rotate express")

        # 动图不旋转
        if payload.image_info.animated == const.IMAGE_ANIMATED:
            logger.warn("[handle] rotate image is animated ignore rotate process")
            return

        # 旋转角度
        angle = getattr(exp, "a", 0)
        if angle == 0:
            return None
        # 进行旋转
        im1 = payload.im.transpose(angle)
        payload.im.close()
        payload.im = im1
        logger.info("[handle] image rotate  params degree:%.2f" % angle)
        return None


class Strip(Handler):
    """
      清理信息
    """
    def __init__(self):
        pass

    def process(self, payload: Payload):
        exp = payload.exp
        if exp is None:
            raise HandlerException("[handle] no strip express")

        pass


# 处理 map
handler_map = {
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


def get_image_info(im=None):
    """
    获取图片信息
    :param im:
    :return:
    """
    info = ImageInfo()

    if im is None:
        return None

    # 设置格式
    info.set_format(im.format)
    # 动画设置
    if getattr(im, "is_animated", False) is True:
        info.set_animated(1)
    else:
        info.set_animated(0)

    # 动画帧数设置
    info.set_number_images(getattr(im, "n_frames", 1))

    # exif 信息设置
    exif = get_image_exif(im)
    info.set_exif(exif)

    # 判断 长宽
    width = im.width
    height = im.height

    if "Orientation" in exif:
        value = exif["Orientation"]
        # ORIENTATION_RIGHT_TOP 6
        # ORIENTATION_RIGHT_BOTTOM 7
        # ORIENTATION_LEFT_BOTTOM 8
        if value in [6, 7, 8]:
            width, height = height, width

    # 设置宽
    info.set_width(width)
    # 设置高
    info.set_height(height)

    # 图片长度获取

    return info


def get_image_exif(im=None):
    """
     获取图片 exif 特征
    :param im:
    :return:
    """
    m = {}
    try:
        if im is None:
            return m
        for k, v in im.getexif().items():
            if k in ExifTags.TAGS:
                m[ExifTags.TAGS[k]] = v
            if k in ExifTags.GPSTAGS:
                m[ExifTags.GPSTAGS[k]] = v
    except Exception:
        pass

    return m


if __name__ == '__main__':
    pass
