from flask import Blueprint
from .common import Controller
import datetime
from app.setting import basic, settings
from app.libs.logger import logger
from flask import render_template_string, Response
from app.logic.process.info import Info
from app.utils.custom_status import CResponse
from app.utils.error_handlers import get_error_html
from app.logic.process.process import Process

process_router = Blueprint(name="process", import_name=__name__)


@process_router.route("/")
@process_router.route("/index")
@process_router.route("/index.html")
def index():
    # logger.info("this is visit index")
    return "hello world image plus time:%s!\n" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@process_router.route("/healthcheck")
def health_check():
    return "ok"


@process_router.route("/v1/image/process", methods=["POST"])
def process():
    """
    图片处理接口
    :return:
    """
    request_id = Controller.headers().get(settings.X_REQUEST_ID, "", type=str)

    process_str = Controller.params().get("x-image-process")
    if process_str is None or len(process_str) == 0:
        process_str = Controller.form().get("x-image-process")

    # 校验处理字符
    if len(process_str) == 0:
        logger.warning("[process] no image process str")
        return render_template_string(get_error_html(), title="[process] no image  process str"), 400

    # 校验 文件
    file = Controller.files()["file"]
    if file is None:
        logger.warning("[process] upload no image file")
        return render_template_string(get_error_html(), title="[process] upload no image file"), 400

    result = None
    try:
        p = Process(process_str)
        # 解析
        p.parse()
        # 处理
        result = p.handing(file)

        if result.is_output_image_info is True:
            data = result.image_info.dumps_dict()
            return CResponse.success(data=data, request_id=request_id)
        else:
            # 文件输出
            if len(result.raw) > 0:
                resp = Response(result.raw, mimetype=result.content_type)
                return resp
            else:
                return render_template_string(get_error_html(), title="[process] process image error no result"), 400
    except Exception as e:
        logger.warning("[process] process exception:%s" % str(e))
        return render_template_string(get_error_html(), title="[process] process exception:%s" % str(e)), 400
    finally:
        if file is not None:
            file.close()
        if result is not None and result.raw is not None:
            result.raw = b""


@process_router.route("/v1/image/info", methods=["POST"])
def info():
    request_id = Controller.headers().get(settings.X_REQUEST_ID, "", type=str)
    try:
        fp = Controller.files()["file"]
        if fp is None:
            raise Exception("upload no image file")

        info = Info.get_info(fp)
        if info is None:
            raise Exception("upload no image info")
        data = info.dumps_dict()
        return CResponse.success(data=data, request_id=request_id)
    except Exception as e:
        logger.warning("[info] get image info err:%s" % str(e))
        return CResponse.error(request_id=request_id, message=str(e))
