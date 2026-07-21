# imagex 迁移到 uv + Python 3.12 设计

**日期:** 2026-07-20
**范围:** 包管理切换到 uv;Python 升级到 3.12(支持 3.10+);依赖更新到最新兼容版本;程序能本地跑起来。
**语言:** 中文(与现有 spec 一致)。

## 目标

- 将项目包管理从 `requirements.txt` + 手动 pin 切换到 **uv**(`pyproject.toml` + `uv.lock`)。
- Python 运行时升级到 **3.12**(在 `pyproject.toml` 声明 `>=3.10`,用 `.python-version` pin 到 3.12)。
- 依赖更新到最新兼容版本,移除废弃/失效依赖。
- 程序能通过 `uv run` 本地启动并正常处理图片。

## 非目标

- 不新增功能,不改接口、返回结构、处理行为。
- 不做与迁移无关的重构。
- 不改控制器、路由、处理逻辑、info 端点等业务代码。

## 现状与风险点(迁移前)

依赖均 pin 在 2021-2022 年版本(`requirements.txt`),关键风险:

1. **`Pillow-SIMD 8.4.0.post0`** -- 废弃分支,无法在 Python 3.10+ 构建。代码仅用 `from PIL import Image`,API 兼容,可换标准 Pillow,无需改业务代码。
2. **`pydantic 1.8.2`** -- `app/setting/configs.py` 用 v1 的 `BaseSettings` + 内部 `Config` 类(条件 `env_file`)。v2 需迁移到 `pydantic-settings` + `model_config`。`app/utils/error_handlers.py` 只用 `exc.errors()` 的 `loc`/`msg`,v1/v2 通用,无需改。
3. **`pyheif` + `heif-image-plugin`** -- 在 `requirements.txt` 但代码从不 import,HEIC/HEIF 解码未接入(输入会失败)。`const.py` 已声明 `HEIC`/`HEIF` 为输入格式(`IMAGE_FORMATS` 含二者,`IMAGE_OUTPUT_FORMATS` 不含),意图明确但未生效。
4. **`pillow-avif-plugin`** -- 3 个文件 `import pillow_avif` 注册 AVIF;Pillow 11 自带 AVIF,该插件可移除。
5. **`ConcurrentLogHandler 0.9.1`** -- 旧包名;日志配置用 `cloghandler.ConcurrentRotatingFileHandler` 别名(故 grep `ConcurrentLogHandler` 漏检)。维护版 `concurrent-log-handler` 保留 `cloghandler` 别名,换名无需改配置。
6. 其余 `Flask/Werkzeug/gunicorn/click/python-dotenv` 等可升到当前版本,对本应用风险低。

## 决策

- **Python 3.12**(`requires-python = ">=3.10"`,`.python-version = 3.12`)。
- **pydantic v2**:迁移 `configs.py`,加 `pydantic-settings` 依赖。
- **HEIC**:用 `pillow-heif`(维护中)替代废弃 `pyheif`/`heif-image-plugin`,启动时集中注册,恢复声明中的 HEIC/HEIF 输入解码。
- **迁移策略:全面现代化** -- 最新兼容依赖,`pyproject.toml`+`uv.lock`,弃 `requirements.txt`。

## uv 项目结构

- 新增 `pyproject.toml`:`[project]` 元数据 + `requires-python = ">=3.10"` + `[project.dependencies]`。
- 新增 `.python-version`:内容 `3.12`。
- 新增 `uv.lock`:锁定全部依赖(含传递依赖),纳入 git。
- **删除 `requirements.txt`**。
- `.gitignore` 增加 `.venv`、`gunicorn.pid`。

`pyproject.toml` 骨架:

```toml
[project]
name = "imagex"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "Flask>=3.1",
    "gunicorn>=23",
    "pydantic-settings>=2.5",
    "Pillow>=11",
    "pillow-heif>=0.16",
    "piexif>=1.1.3",
    "flask-log-request-id>=0.10.1",
    "concurrent-log-handler>=0.9.25",
]
```

## 依赖清单

直接依赖(传递依赖如 cffi/click/Jinja2/Werkzeug/typing-extensions/python-dotenv 由 uv 解析锁定,不再手 pin):

| 依赖 | 版本 | 说明 |
|--|--|--|
| Flask | >=3.1 | 2.0.2 -> 3.x |
| gunicorn | >=23 | 20.1.0 -> 23.x |
| pydantic-settings | >=2.5 | 拉入 pydantic v2,提供 BaseSettings |
| Pillow | >=11 | 替代 Pillow-SIMD;自带 AVIF |
| pillow-heif | >=0.16 | 替代 pyheif/heif-image-plugin,恢复 HEIC/HEIF 解码 |
| piexif | >=1.1.3 | exif 处理,纯 Python,保持 |
| flask-log-request-id | >=0.10.1 | request_id,保持(兼容性见风险) |
| concurrent-log-handler | >=0.9.25 | 替代旧包名,保留 cloghandler 别名 |

移除:`Pillow-SIMD`、`pyheif`、`heif-image-plugin`、`pillow-avif-plugin`、以及全部手 pin 的传递依赖。

## 代码改动(仅迁移必需)

### (a) `app/setting/configs.py` -- pydantic v1 -> v2

- `from pydantic import BaseSettings` -> `from pydantic_settings import BaseSettings, SettingsConfigDict`。
- 内部 `class Config`(含 `mode`/条件 `env_file`/`env_file_encoding`)改为模块级计算 `_ENV_FILE`,再 `model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")`。
- `PROJECT_NAME`/`X_REQUEST_ID` 仍为必填字段,从 env 文件加载;`print` 警告保留。行为不变。

改写后:

```python
import os
from os.path import dirname, abspath
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.host_ip import get_host_ip

_MODE = os.getenv("MODE", "local")
_ENV_PATH = f"{abspath(dirname(abspath(dirname(dirname(__file__)))))}/env"
_ENV_FILE_MAP = {
    "local": "local.env",
    "develop": "develop.env",
    "test": "test.env",
    "perf": "perf.env",
    "prod": "prod.env",
}
_ENV_FILE = f"{_ENV_PATH}/{_ENV_FILE_MAP.get(_MODE, 'local.env')}"
print(f"> WARNING !!! 启动方式为: {_MODE}, 配置文件为 {_ENV_FILE}")


class BaseConfigs(BaseSettings):
    APP_PATH: str = abspath(dirname(dirname(__file__)))
    ROOT_PATH: str = abspath(dirname(APP_PATH))
    K8S_ROOT_PATH: str = abspath(dirname(ROOT_PATH))
    CONF_PATH: str = f"{ROOT_PATH}/conf"
    ENV_PATH: str = f"{ROOT_PATH}/env"
    LOG_PATH: str = f"{K8S_ROOT_PATH}/logs"
    TMP_PATH: str = f"{ROOT_PATH}/tmp"
    HOST_IP: str = get_host_ip() or "127.0.0.1"

    PROJECT_NAME: str
    X_REQUEST_ID: str

    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8")


@lru_cache()
def get_configs():
    return BaseConfigs()
```

### (b) `app/__init__.py` -- 插件注册集中化 + Flask 3 JSON 兼容

- 在 `init_app` 内、`register_blueprints` 之前:`from pillow_heif import register_heif_opener; register_heif_opener()`(HEIC/HEIF 解码注册一次)。
- 新增 `app.json.ensure_ascii = False`(Flask 3 不再读 `JSON_AS_ASCII`,等价于原 `basic.py` 的 `JSON_AS_ASCII = False`)。

### (c) `app/setting/basic.py`

- 删除 `JSON_AS_ASCII = False`(已移到 `app.json.ensure_ascii`);保留 `MAX_CONTENT_LENGTH`(Flask 3 仍识别)。

### (d) `app/logic/process/info.py`、`process.py`、`handle/handler.py`

- 删除各自的 `import pillow_avif`(AVIF 改由 Pillow 11 内置;HEIF 在 app 启动时集中注册)。

### (e) `gunicorn.conf.py`

- `pidfile = '/var/run/gunicorn.pid'` -> `pidfile = 'gunicorn.pid'`(原路径需 root,macOS 本地跑不起来)。

### (f) `run.sh`

- `gunicorn -c gunicorn.conf.py main:app` -> `uv run gunicorn -c gunicorn.conf.py main:app`(`uv run` 自动 sync 依赖)。`MODE=prod` 保持不变(env 文件内容一致)。本地调试可用 `uv run python main.py`。

### (g) `.gitignore`

- 增加 `.venv`、`gunicorn.pid`。

控制器、路由、处理逻辑、info 端点等**不动**。

## 风险与回退

| 风险 | 回退 |
|--|--|
| flask-log-request-id 0.10.1 **运行时不兼容** Flask 3(`flask_ctx_get_request_id` 懒加载 Flask 2.3 起移除的 `_app_ctx_stack`,每个带日志请求 500;冒烟测试发现) | 不回退 Flask;在 `app/__init__.py` 用 Flask 3 fetcher shim 替换 `current_request_id.ctx_fetchers`(经 `g`/`current_app` 读取,commit bcff2ce)。仅在 fork/替换 flask-log-request-id 后方可移除 shim |
| Pillow 11 内置 AVIF 在某些 wheel 不可用 | 若 AVIF 保存失败,加回 pillow-avif-plugin |
| concurrent-log-handler 未保留 `cloghandler` 别名 | 把日志配置 `cloghandler.ConcurrentRotatingFileHandler` 改为 `concurrent_log_handler.ConcurrentRotatingFileHandler` |
| pydantic-settings env 加载差异 | 校验 env_file 绝对路径与字段大小写(默认大小写不敏感,与 v1 一致) |

## 验证(冒烟)

1. `uv sync` 成功,生成 `uv.lock`。
2. `uv run python -c "from app import init_app; init_app(); print('ok')"` -- app 构造无报错。
3. `uv run gunicorn -c gunicorn.conf.py main:app` 启动,监听 8090。
4. `curl -F "file=@test.jpg" http://127.0.0.1:8090/v1/image/info` 返回 JSON。
5. `curl -F "file=@test.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100/format,f_WEBP" http://127.0.0.1:8090/v1/image/process -o out.webp` 生成 out.webp。
6. (可选)HEIC 输入解码、`format,f_AVIF` 输出各测一次。

## 交付物

- **新增:** `pyproject.toml`、`.python-version`、`uv.lock`
- **删除:** `requirements.txt`
- **修改:** `configs.py`、`app/__init__.py`、`basic.py`、`info.py`、`process.py`、`handler.py`、`gunicorn.conf.py`、`run.sh`、`.gitignore`

## 不确定项

无。所有改动均基于现有代码行为,迁移不引入新功能或新约定;版本兼容性风险已在"风险与回退"列出并配套回退方案。
