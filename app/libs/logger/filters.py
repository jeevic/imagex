import logging
from app.setting import settings


class HostIpLogFilter(logging.Filter):
    """
    Log filter to inject the current ip of the request under `log_record.ip`
    """
    def filter(self, log_record):
        log_record.host_ip = settings.HOST_IP
        return log_record
