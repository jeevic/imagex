import os
import socket


def get_host_ip() ->str:
    """
    获取本机的host ip 支持容器获取 优先从环境变量获取 其次从udp获取
    :return:
    """
    # 优先环境变量获取
    ip = os.getenv('YIDIAN_LOCAL_IP')
    if ip is not None and len(ip) > 0:
        yd_local_ip = ip
    else:
        yd_local_ip = _get_host_ip_by_udp()
    return yd_local_ip


def _get_host_ip_by_udp() ->str:
    """
    基于 udp获取本机ip 并不发送 只是生成一个地址
    :return:
    """

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    return ip
