# 每个服务都有各自的 gunicorn.conf
# 这个配置文件里面表明了服务启动的各种配置项

# 并行的工作进程数 cpu * 2 + 1
workers = 3

# 指定每个工作者的线程数
threads = 1

# 监听端口
bind = ':8090'

# 设置守护进程,将进程交给supervisor管理 true
daemon = 'false'

# 工作模式协程
#worker_class = 'gevent'

# 设置最大并发量
worker_connections = 1500

# worker重启之前处理的最大requests数 防止内存泄露
max_requests = 150000

# 抖动参数，防止worker全部同时重启
max_requests_jitter = 80000

# 超过这么多秒后工作将被杀掉，并重新启动。一般设定为30秒
timeout = 100


# 设置进程文件目录
pidfile = '/var/run/gunicorn.pid'

# 设置访问日志和错误信息日志路径
accesslog = '-'
errorlog = '-'

# 设置日志记录水平
loglevel = 'warning'

# 访问日志
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)s "%(f)s" "%(a)s"'