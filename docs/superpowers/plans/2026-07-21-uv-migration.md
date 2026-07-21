# imagex 迁移到 uv + Python 3.12 实施计划

> **给执行 agent:** 必需子技能:使用 superpowers:subagent-driven-development(推荐)或 superpowers:executing-plans 按任务逐个实施本计划。步骤使用复选框(`- [ ]`)语法跟踪。

**目标:** 将 imagex 从 `requirements.txt` + 手动 pin 的 2021–2022 依赖迁移到 uv(`pyproject.toml` + `uv.lock`),Python 升级到 3.12,依赖更新到最新兼容版本,使服务能通过 `uv run` 本地启动并照常处理图片。

**架构:** 一次依赖/运行时切换,只做迁移强制需要的最小代码改动。唯一真正的逻辑变更是 `app/setting/configs.py`(pydantic v1 `BaseSettings` -> `pydantic-settings` v2)。HEIC/HEIF 解码从各文件 `import HeifImagePlugin` 的副作用式注册,集中到 `app/__init__.py` 的一次 `pillow_heif.register_heif_opener()` 调用。AVIF 不再用 `pillow-avif-plugin`(Pillow ≥11 自带)。`cloghandler` 日志别名替换为真实的 `concurrent_log_handler` 模块。控制器、路由、处理逻辑、info 端点均不改。

**技术栈:** Python 3.12(`requires-python = ">=3.10"`),uv 0.11+,Flask 3.1,pydantic-settings 2.x(pydantic v2),Pillow 12(自带 AVIF),pillow-heif 1.x(HEIC/HEIF),gunicorn 26,concurrent-log-handler 0.9.x,flask-log-request-id 0.10.1,piexif 1.1.3。

## 全局约束

以下逐字取自 spec(`docs/superpowers/specs/2026-07-20-uv-migration-design.md`)并已对照代码确认。每个任务的需求隐含包含本节内容。

- **Python 运行时:** `pyproject.toml` 中 `requires-python = ">=3.10"`;`.python-version` 文件内容为 `3.12`。
- **运行时依赖(精确,写入 `[project.dependencies]`):** `Flask>=3.1`、`gunicorn>=23`、`pydantic-settings>=2.5`、`Pillow>=11`、`pillow-heif>=0.16`、`piexif>=1.1.3`、`flask-log-request-id>=0.10.1`、`concurrent-log-handler>=0.9.25`。传递依赖(cffi/click/Jinja2/Werkzeug/typing-extensions/python-dotenv 等)由 uv 解析锁定,绝不手 pin。
- **移除的依赖:** `Pillow-SIMD`、`pyheif`、`heif-image-plugin`、`pillow-avif-plugin`,以及旧 `requirements.txt` 中所有手 pin 的传递依赖。
- **新增文件(纳入 git):** `pyproject.toml`、`.python-version`、`uv.lock`。
- **删除文件:** `requirements.txt`。
- **`.gitignore` 新增:** `.venv`、`gunicorn.pid`。
- **不改行为:** 不改控制器、路由、处理逻辑、info 端点、返回结构、`const.py`。不新增功能。不做与迁移无关的重构。
- **pydantic v2:** `configs.py` 使用 `from pydantic_settings import BaseSettings, SettingsConfigDict` + `model_config = SettingsConfigDict(...)`。`PROJECT_NAME`/`X_REQUEST_ID` 仍为必填字段,从 env 文件加载;`print` 警告保留。
- **HEIC/HEIF:** 在 `init_app()` 内、`register_blueprints` 之前,通过 `from pillow_heif import register_heif_opener; register_heif_opener()` 集中注册一次。
- **AVIF:** 由 Pillow 自带 AVIF 提供(不用 `pillow-avif-plugin`)。
- **Flask 3 JSON:** `app.json.ensure_ascii = False`(在 `init_config` 中设置);`basic.py` 中的 `JSON_AS_ASCII = False` 删除。
- **gunicorn pidfile:** `pidfile = 'gunicorn.pid'`(项目相对路径,不用 `/var/run/...`)。
- **run.sh:** `uv run gunicorn -c gunicorn.conf.py main:app`;`MODE=prod` 不变。
- **语言:** 现有代码注释保持中文;本计划新增注释亦用中文,以保持一致。

### 规划期验证结论(开工前必读)

以下结论在规划阶段针对实际解析出的版本做了实证验证。它们修正了 spec 的两个假设 —— spec 的风险表把这两条都当成「有条件」回退方案,但实际它们是「必须」执行的:

1. **`cloghandler` 别名在 `concurrent-log-handler==0.9.29` 中不存在。** `import cloghandler` 会抛 `ModuleNotFoundError`。spec 风险行「维护版 concurrent-log-handler 保留 cloghandler 别名」对实际解析版本不成立。因此 `app/libs/logger/__init__.py` 必须把两处 handler class 字符串从 `cloghandler.ConcurrentRotatingFileHandler` 改为 `concurrent_log_handler.ConcurrentRotatingFileHandler`。这是 **任务 3**,不是回退方案。(正确的模块 `concurrent_log_handler` 及其 `ConcurrentRotatingFileHandler` 类已确认存在。)
2. **`info.py`、`process.py`、`handler.py` 中的 `import HeifImagePlugin` 也必须删除。** spec 的 (d) 节只写明删除 `import pillow_avif`,但这三个文件还都有 `import HeifImagePlugin`(对应 `heif-image-plugin` 包,在移除依赖清单中)。保留它会在启动时抛 `ModuleNotFoundError`。HEIF 注册在 **任务 4** 中通过 `register_heif_opener()` 集中化,因此两处 per-file import 在那里一并删除。

规划期另确认(无需动作,仅作背景):`uv sync` 用 spec 的纯 `[project]` 骨架(无 `[build-system]`)即可成功 —— uv 将其视为虚拟项目,不会构建/安装 `imagex` 自身;Pillow 12.3.0 的 `features.check('avif')` 为 `True`;`pillow_heif.register_heif_opener` 存在;`flask_log_request_id`(`RequestID`、`parser`)在 Flask 3.1.3 下可正常导入(**但运行时不兼容**,见 §风险与回退:`flask_ctx_get_request_id` 懒加载 Flask 2.3 起移除的 `_app_ctx_stack`,每个带日志请求 500;已用 `app/__init__.py` 的 Flask 3 fetcher shim 修复,commit bcff2ce);且 `from pydantic import BaseSettings` 在 pydantic 2.13 下抛 `PydanticImportError`(确认 configs 迁移是必须的,非可选)。

---

## 文件结构

- **新增** `pyproject.toml` —— 项目元数据 + `requires-python` + `[project.dependencies]`(依赖的唯一真相来源;取代 `requirements.txt`)。
- **新增** `.python-version` —— 单行 `3.12`;固定 uv 管理的解释器。
- **新增** `uv.lock` —— 由 `uv sync` 生成;锁定完整依赖图;纳入 git。
- **删除** `requirements.txt` —— 由 `pyproject.toml` + `uv.lock` 取代。
- **修改** `app/setting/configs.py` —— pydantic v1 `class Config` -> pydantic-settings v2 `model_config = SettingsConfigDict(...)`。
- **修改** `app/libs/logger/__init__.py` —— handler class `cloghandler.ConcurrentRotatingFileHandler` -> `concurrent_log_handler.ConcurrentRotatingFileHandler`(2 处)。
- **修改** `app/__init__.py` —— 新增集中化 `register_heif_opener()`;新增 `app.json.ensure_ascii = False`。
- **修改** `app/setting/basic.py` —— 删除 `JSON_AS_ASCII = False`。
- **修改** `app/logic/process/info.py` —— 删除 `import pillow_avif` 与 `import HeifImagePlugin`。
- **修改** `app/logic/process/process.py` —— 删除 `import pillow_avif` 与 `import HeifImagePlugin`。
- **修改** `app/logic/process/handle/handler.py` —— 删除 `import pillow_avif` 与 `import HeifImagePlugin`。
- **修改** `gunicorn.conf.py` —— `pidfile` 路径改为 `gunicorn.pid`。
- **修改** `run.sh` —— gunicorn 前加 `uv run`。
- **修改** `.gitignore` —— 新增 `.venv`、`gunicorn.pid`。
- **修改** `README.md` —— 快速开始:`pip install` -> `uv sync`,Python 3.8 -> 3.12。

### 任务依赖与顺序

迁移强制了严格顺序:安装 pydantic v2(任务 1)会立即破坏旧 `configs.py`,移除 `pillow-avif-plugin`/`heif-image-plugin`(任务 1 的依赖)会立即破坏 per-file import。中间态并非都能跑起来 —— 每个任务的门禁如实说明该阶段能通过什么:

1. 引导 uv(app 尚不能 import —— 预期如此)。
2. 修 `configs.py`(settings 可加载;app 仍被插件 import 阻塞)。
3. 修日志 handler class(`load_log()` 可独立跑通)。
4. 集中化插件 + 删除 per-file import(`init_app()` 终于端到端跑通)。
5. Flask 3 JSON ascii。
6. gunicorn 本地可运行(pidfile + run.sh)。
7. 删除 `requirements.txt`。
8. README 快速开始。
9. 最终集成冒烟测试(gunicorn 起服务 + curl)。

---

### 任务 1:引导 uv 项目

**文件:**
- 新增: `pyproject.toml`
- 新增: `.python-version`
- 修改: `.gitignore`(追加 `.venv`、`gunicorn.pid`)
- 生成(提交): `uv.lock`、`.venv/`(已忽略)

**接口:**
- 依赖: spec 的依赖表(§依赖清单)与 `pyproject.toml` 骨架(§uv 项目结构)。
- 产出: 一个基于 Python 3.12 的 uv 管理环境,8 个运行时依赖全部安装并锁定在 `uv.lock`。后续任务依赖 `uv run <cmd>` 可用,以及 pydantic v2 / Pillow 12 / pillow-heif / concurrent-log-handler 可导入。注意:本任务后 `uv run python -c "from app import init_app"` 仍会失败(旧 `configs.py` 用了 v2 已移除的 `from pydantic import BaseSettings`,且 per-file 的 `import pillow_avif`/`import HeifImagePlugin` 引用了已移除的包)—— 这是预期的,由任务 2–4 修复。

- [ ] **步骤 1:创建 `.python-version`**

文件内容(仅一行,无多余空行):

```
3.12
```

- [ ] **步骤 2:创建 `pyproject.toml`**

文件内容(逐字取自 spec 骨架 —— 无 `[build-system]`;uv 视其为虚拟项目,不会构建/安装 `imagex` 自身,规划期已确认):

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

- [ ] **步骤 3:向 `.gitignore` 追加 `.venv` 与 `gunicorn.pid`**

当前 `.gitignore` 以 `.claude/settings.local.json` 结尾(无末尾换行)。通过编辑最后一行追加两条新条目。

`old_string`:
```
.claude/settings.local.json
```
`new_string`:
```
.claude/settings.local.json
.venv
gunicorn.pid
```

(`.venv` 与已有的 `venv` 不同,两者都需要。`gunicorn.pid` 在任务 6 后由 gunicorn 写入。)

- [ ] **步骤 4:运行 `uv sync` 解析、安装并生成 `uv.lock`**

运行:
```bash
uv sync
```
预期: `uv sync` 解析约 25 个包,创建 `.venv/`,写入 `uv.lock`,退出码 0。规划期观察到的解析版本:Flask 3.1.3、gunicorn 26.0.0、pydantic 2.13.4、pydantic-settings 2.14.2、Pillow 12.3.0、pillow-heif 1.4.0、concurrent-log-handler 0.9.29、piexif 1.1.3、flask-log-request-id 0.10.1。

- [ ] **步骤 5:验证新依赖可导入且 Pillow 自带 AVIF**

运行:
```bash
uv run python -c "import flask, PIL, pydantic_settings, pillow_heif, piexif, flask_log_request_id, concurrent_log_handler; from PIL import features; assert features.check('avif'), 'AVIF not built into Pillow'; from pillow_heif import register_heif_opener; print('deps ok')"
```
预期: 打印 `deps ok`。(此处导入的是真实的 `concurrent_log_handler` 模块 —— `cloghandler` 别名不存在,由任务 3 修复。)

- [ ] **步骤 6:确认 app 尚不能 import(预期失败,任务 2–4 修复)**

运行:
```bash
uv run python -c "from app import init_app" 2>&1 | tail -3
```
预期: 失败。回溯末尾为 `pydantic.errors.PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package.`(因旧 `configs.py` 仍 `from pydantic import BaseSettings`)。这是任务 2 的预期起点。

- [ ] **步骤 7:提交**

```bash
git add pyproject.toml .python-version uv.lock .gitignore
git commit -m "Add: uv project bootstrap (pyproject.toml, .python-version, uv.lock, .gitignore)"
```

---

### 任务 2:`configs.py` 从 pydantic v1 迁移到 pydantic-settings v2

**文件:**
- 修改: `app/setting/configs.py`(整文件重写)

**接口:**
- 依赖: 任务 1 安装的 `pydantic-settings`(`BaseSettings`、`SettingsConfigDict`);`app/utils/host_ip.get_host_ip()`(不变);`env/` 下的 env 文件(不变;`env/local.env` 定义 `PROJECT_NAME=imagex service` 与 `X_REQUEST_ID=X-Request-Id`)。
- 产出: `get_configs() -> BaseConfigs`(名称/签名不变)与模块级 `settings` 单例(`app/setting/__init__.py` 仍调用一次 `get_configs()`)。字段 `PROJECT_NAME: str`、`X_REQUEST_ID: str` 仍必填,从按 `MODE` 选择的 env 文件加载。行为不变。

- [ ] **步骤 1:运行门禁,确认失败(即「失败测试」)**

运行:
```bash
uv run python -c "from app.setting import settings; assert settings.PROJECT_NAME == 'imagex service', settings.PROJECT_NAME; assert settings.X_REQUEST_ID == 'X-Request-Id', settings.X_REQUEST_ID; print('configs ok')" 2>&1 | tail -5
```
预期: 失败 —— `PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package.`(旧 `configs.py` 的 `from pydantic import BaseSettings` 在 pydantic v2 下非法)。

- [ ] **步骤 2:重写 `app/setting/configs.py`**

将 `app/setting/configs.py` 整文件内容替换为(保留原有 shebang/coding 头;正文逐字取自 spec §(a)):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

- [ ] **步骤 3:运行门禁,确认通过**

运行:
```bash
uv run python -c "from app.setting import settings; assert settings.PROJECT_NAME == 'imagex service', settings.PROJECT_NAME; assert settings.X_REQUEST_ID == 'X-Request-Id', settings.X_REQUEST_ID; print('configs ok')"
```
预期: 先打印 `> WARNING !!! 启动方式为: local, 配置文件为 .../env/local.env`,再打印 `configs ok`。

- [ ] **步骤 4:提交**

```bash
git add app/setting/configs.py
git commit -m "Update: migrate configs.py from pydantic v1 to pydantic-settings v2"
```

---

### 任务 3:修复日志 handler class(`cloghandler` -> `concurrent_log_handler`)

**文件:**
- 修改: `app/libs/logger/__init__.py`(第 43、62 行 —— 两处 `'class': 'cloghandler.ConcurrentRotatingFileHandler',` 字符串)

**接口:**
- 依赖: 任务 1 安装的 `concurrent-log-handler`,提供 `concurrent_log_handler` 模块与 `ConcurrentRotatingFileHandler` 类;`app/setting.settings`(任务 2 起可用)与 `flask_log_request_id.RequestIDLogFilter`(不变)。
- 产出: `load_log()` 能解析两个 handler 并成功执行 `logging.config.dictConfig(LOGGING)`。仅改 handler class 字符串;日志文件路径、formatter、filter 及注释中的 `cloghandler` 别名提及等其余不动。下游:`init_app()`(任务 4)会调用 `load_log()`,故本任务是 app 启动的前置。

- [ ] **步骤 1:运行门禁,确认失败**

运行:
```bash
uv run python -c "from app.libs.logger import load_log; load_log(); print('logger ok')" 2>&1 | tail -5
```
预期: 失败 —— 解析 handler class `cloghandler.ConcurrentRotatingFileHandler` 时报错,`No module named 'cloghandler'`(别名在 concurrent-log-handler 0.9.29 中不存在,规划期已确认)。`logging.config.dictConfig` 在配置 `info` handler 时抛错。

- [ ] **步骤 2:改第一处 handler class 字符串(`info` handler)**

`old_string`(`info` handler 块,因 `'filename': 'logs/info.log'` 唯一):
```
        'info': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 20,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/info.log',
```
`new_string`:
```
        'info': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 20,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/info.log',
```

- [ ] **步骤 3:改第二处 handler class 字符串(`error` handler)**

`old_string`(`error` handler 块,因 `'filename': 'logs/error.log'` 与 `'backupCount': 2` 唯一):
```
        'error': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 2,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/error.log',
```
`new_string`:
```
        'error': {
            # Handler 类, 这种Handler 会定时分割日志
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            # 日志分割大小
            'maxBytes': 1024 * 1024 * 1024,
            # 日志存储几份切割文件
            'backupCount': 2,
            # web日志文件路径, 一般填写在项目中的相对路径即可
            'filename': 'logs/error.log',
```

- [ ] **步骤 4:运行门禁,确认通过**

运行:
```bash
uv run python -c "from app.libs.logger import load_log; load_log(); print('logger ok')"
```
预期: 打印 `logger ok`。(`load_log()` 会实例化两个 `ConcurrentRotatingFileHandler`,在 `<项目根的上级>/logs/` 下创建/打开日志文件;代码已在 `try/except` 内 `os.makedirs` 该目录。若你的项目根上级不可写,手动创建 `<上级>/logs/` —— 这是既有行为,非迁移问题。)

- [ ] **步骤 5:提交**

```bash
git add app/libs/logger/__init__.py
git commit -m "Update: logger handler class cloghandler -> concurrent_log_handler"
```

---

### 任务 4:集中化 HEIF 插件注册并删除 per-file 插件 import

**文件:**
- 修改: `app/__init__.py`(新增 `register_heif_opener` import 与调用)
- 修改: `app/logic/process/info.py`(删除 `import pillow_avif`、`import HeifImagePlugin`)
- 修改: `app/logic/process/process.py`(删除 `import pillow_avif`、`import HeifImagePlugin`)
- 修改: `app/logic/process/handle/handler.py`(删除 `import pillow_avif`、`import HeifImagePlugin`)

**接口:**
- 依赖: 任务 1 安装的 `pillow-heif`(`register_heif_opener`);Pillow 12 自带 AVIF(取代 `pillow-avif-plugin`);`init_app()` 既有调用顺序(`init_config` -> `init_logger` -> `init_request_id` -> `register_blueprints`)。
- 产出: `init_app() -> Flask` 端到端构造成功,无 `ImportError`/`ModuleNotFoundError`。HEIC/HEIF 输入解码只注册一次(在蓝图注册前调用 `register_heif_opener()`)。AVIF 输出用 Pillow 自带编码器。三个 process 模块不再在 import 时做副作用式插件注册。本任务对应 spec 验证步骤 2。

- [ ] **步骤 1:运行门禁,确认失败**

运行:
```bash
uv run python -c "from app import init_app; init_app(); print('app ok')" 2>&1 | tail -5
```
预期: 失败 —— `ModuleNotFoundError: No module named 'pillow_avif'`(导入 `app.controller.process` -> `app.logic.process.info` 时触发,后者仍有 `import pillow_avif`)。(`from app import init_app` 会导入 `app/__init__.py`,而它在模块顶部 `from app.controller.process import process_router`。)

- [ ] **步骤 2:删除 `info.py` 的两行插件 import**

`old_string`:
```
from PIL import Image
import pillow_avif
import HeifImagePlugin
from app.libs.logger import logger
```
`new_string`:
```
from PIL import Image
from app.libs.logger import logger
```

- [ ] **步骤 3:删除 `process.py` 的两行插件 import**

`old_string`:
```
from PIL import Image
import pillow_avif
import HeifImagePlugin
from app.logic.process.payload import Payload, ImageInfo
```
`new_string`:
```
from PIL import Image
from app.logic.process.payload import Payload, ImageInfo
```

- [ ] **步骤 4:删除 `handler.py` 的两行插件 import**

`old_string`:
```
from PIL import Image, ExifTags
import pillow_avif
import HeifImagePlugin
import time
```
`new_string`:
```
from PIL import Image, ExifTags
import time
```

- [ ] **步骤 5:在 `app/__init__.py` 新增 `register_heif_opener` import**

`old_string`:
```
from app.libs.logger import load_log
from app.setting import settings


def init_app() -> Flask:
```
`new_string`:
```
from app.libs.logger import load_log
from app.setting import settings
from pillow_heif import register_heif_opener


def init_app() -> Flask:
```

- [ ] **步骤 6:在 `init_app()` 内、`register_blueprints` 之前调用 `register_heif_opener()`**

`old_string`:
```
    init_request_id(app)
    register_blueprints(app)

    return app
```
`new_string`:
```
    init_request_id(app)

    # HEIC/HEIF 解码集中注册一次(替代各文件 import HeifImagePlugin)
    register_heif_opener()

    register_blueprints(app)

    return app
```

- [ ] **步骤 7:运行门禁,确认通过**

运行:
```bash
uv run python -c "from app import init_app; init_app(); print('app ok')"
```
预期: 先打印 `> WARNING !!! ...`,再打印 `app ok`。即 spec 验证步骤 2。

- [ ] **步骤 8:提交**

```bash
git add app/__init__.py app/logic/process/info.py app/logic/process/process.py app/logic/process/handle/handler.py
git commit -m "Update: centralize HEIF plugin registration, remove per-file pillow_avif/HeifImagePlugin imports"
```

---

### 任务 5:Flask 3 JSON ascii(`app.json.ensure_ascii`)并删除 `JSON_AS_ASCII`

**文件:**
- 修改: `app/__init__.py`(`init_config` —— 新增 `app.json.ensure_ascii = False`)
- 修改: `app/setting/basic.py`(删除 `JSON_AS_ASCII = False` 及其注释)

**接口:**
- 依赖: Flask 3 的 `app.json`(`DefaultJSONProvider`),它忽略旧 `JSON_AS_ASCII` 配置键。`init_config(app)` 已通过 `app.config.from_pyfile` 加载 `basic.py`。
- 产出: `jsonify` 输出非 ASCII(UTF-8)—— 与旧 `JSON_AS_ASCII = False` 行为一致,改用 Flask 3 的方式表达。`MAX_CONTENT_LENGTH` 保留在 `basic.py`(Flask 3 仍识别)。

- [ ] **步骤 1:运行门禁,确认失败**

运行:
```bash
uv run python -c "from app import init_app; app = init_app(); assert app.json.ensure_ascii is False, app.json.ensure_ascii; print('json ascii ok')" 2>&1 | tail -3
```
预期: 失败 —— `AssertionError`,因为 `app.json.ensure_ascii` 默认为 `True`(`basic.py` 的 `JSON_AS_ASCII = False` 被 Flask 3 忽略,尚无任何代码将其置为 `False`)。

- [ ] **步骤 2:在 `init_config` 中设置 `app.json.ensure_ascii = False`**

`old_string`:
```
def init_config(app: Flask) -> None:
    """
    flask 配置初始化
    """
    app.config.from_pyfile(f"{settings.APP_PATH}/setting/basic.py")
```
`new_string`:
```
def init_config(app: Flask) -> None:
    """
    flask 配置初始化
    """
    app.config.from_pyfile(f"{settings.APP_PATH}/setting/basic.py")
    # Flask 3 不再读 JSON_AS_ASCII,等价于原 basic.py 的 JSON_AS_ASCII = False
    app.json.ensure_ascii = False
```

- [ ] **步骤 3:从 `basic.py` 删除 `JSON_AS_ASCII`**

`old_string`:
```
# -*- coding: utf-8 -*-

# 返回的结果不只用ascii编码
JSON_AS_ASCII = False

# 最长的请求长度
```
`new_string`:
```
# -*- coding: utf-8 -*-

# 最长的请求长度
```

- [ ] **步骤 4:运行门禁,确认通过**

运行:
```bash
uv run python -c "from app import init_app; app = init_app(); assert app.json.ensure_ascii is False, app.json.ensure_ascii; print('json ascii ok')"
```
预期: 打印 `json ascii ok`。

- [ ] **步骤 5:提交**

```bash
git add app/__init__.py app/setting/basic.py
git commit -m "Update: Flask 3 JSON ascii via app.json.ensure_ascii, drop JSON_AS_ASCII"
```

---

### 任务 6:让 gunicorn 本地可运行(pidfile 路径 + `uv run`)

**文件:**
- 修改: `gunicorn.conf.py`(`pidfile` 路径)
- 修改: `run.sh`(前缀 `uv run`)

**接口:**
- 依赖: 任务 1 的 uv 环境(`uv run` 自动 sync 依赖);gunicorn 26。
- 产出: gunicorn 无需 root 即可启动(把 `gunicorn.pid` 写到项目根而非 `/var/run/`)。`run.sh` 通过 `uv run gunicorn ...` 启动服务,`MODE=prod` 不变。pidfile 可写性在任务 9 端到端验证。

- [ ] **步骤 1:确认当前 pidfile 仍是 root-only 路径(失败门禁)**

运行:
```bash
grep -n "/var/run/gunicorn" gunicorn.conf.py && echo "FAIL: still root-only pidfile"
```
预期: 打印 `33:pidfile = '/var/run/gunicorn.pid'`,随后 `FAIL: still root-only pidfile`。

- [ ] **步骤 2:把 pidfile 改为项目相对路径**

`old_string`:
```
pidfile = '/var/run/gunicorn.pid'
```
`new_string`:
```
pidfile = 'gunicorn.pid'
```

- [ ] **步骤 3:在 `run.sh` 中给 gunicorn 加 `uv run` 前缀**

`old_string`:
```
gunicorn -c gunicorn.conf.py main:app
```
`new_string`:
```
uv run gunicorn -c gunicorn.conf.py main:app
```

- [ ] **步骤 4:确认两处改动已落地**

运行:
```bash
grep -q "/var/run/gunicorn" gunicorn.conf.py && echo "FAIL: pidfile not changed" || echo "pidfile ok"
grep -q "^uv run gunicorn -c gunicorn.conf.py main:app" run.sh && echo "run.sh ok" || echo "FAIL: run.sh not changed"
```
预期:
```
pidfile ok
run.sh ok
```

- [ ] **步骤 5:验证 gunicorn 能加载配置与 app**

运行:
```bash
uv run gunicorn --check-config -c gunicorn.conf.py main:app
```
预期: 退出码 0,无输出(gunicorn 成功加载 `gunicorn.conf.py` 并导入 `main:app`;此前任务均已完成)。若打印弃用提示无妨 —— 仅非零退出才算失败。

- [ ] **步骤 6:提交**

```bash
git add gunicorn.conf.py run.sh
git commit -m "Update: gunicorn pidfile to local path, run.sh via uv run"
```

---

### 任务 7:删除 `requirements.txt`

**文件:**
- 删除: `requirements.txt`

**接口:**
- 依赖: 任务 1 的 `pyproject.toml` + `uv.lock` 作为依赖唯一真相来源。
- 产出: 依赖管理完全基于 uv。`uv sync` 继续可用(它读 `pyproject.toml`/`uv.lock`,不读 `requirements.txt`)。

- [ ] **步骤 1:确认 `requirements.txt` 仍存在(失败门禁)**

运行:
```bash
test -f requirements.txt && echo "FAIL: requirements.txt still present" || echo "removed"
```
预期: `FAIL: requirements.txt still present`。

- [ ] **步骤 2:删除它(用 `git rm` 暂存)**

运行:
```bash
git rm requirements.txt
```
预期: `rm 'requirements.txt'`。

- [ ] **步骤 3:确认无 `requirements.txt` 后 `uv sync` 仍正常**

运行:
```bash
test ! -f requirements.txt && uv sync && echo "requirements removed, uv sync ok"
```
预期: `uv sync` 报告无需安装(已满足),并打印 `requirements removed, uv sync ok`。

- [ ] **步骤 4:提交**

```bash
git commit -m "Remove: requirements.txt (replaced by pyproject.toml + uv.lock)"
```

---

### 任务 8:更新 README 快速开始为 uv + Python 3.12

**文件:**
- 修改: `README.md`(「快速开始」一节,第 8–20 行)

> **范围说明:** spec 的交付物清单未列 `README.md`,但当前快速开始让用户 `pip install -r requirements.txt`(任务 7 已删除)且写「Python 3.8」(现为 3.12)。保留失效的安装说明会直接误导,故此最小文档修复在迁移范围内。仅改快速开始段落与 bash 代码块;README 其余各节不动。

**接口:**
- 依赖: 任务 1–7 建立的 uv 工作流。
- 产出: 准确的本地安装说明(`uv sync`、`sh -x run.sh`、`uv run python main.py`)与正确的 Python 版本。

- [ ] **步骤 1:确认旧快速开始仍在(失败门禁)**

运行:
```bash
grep -q "pip install -r requirements.txt" README.md && echo "FAIL: old pip instructions still present"
```
预期: `FAIL: old pip instructions still present`。

- [ ] **步骤 2:替换快速开始段落与 bash 代码块**

`old_string`:
````
程序基于 Python 3.8 开发,依赖参考 Pillow 安装文档:https://pillow.readthedocs.io/en/stable/installation.html

```bash
# 安装依赖
pip install -r requirements.txt

# 启动(默认端口 8090)
sh -x run.sh

# 第一个请求: 缩放到 200x100 并转 PNG
curl -F "file=@input.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100/format,f_PNG" \
  http://127.0.0.1:8090/v1/image/process -o out.png
```
````
`new_string`:
````
程序基于 Python 3.12 开发(在 `pyproject.toml` 声明 `requires-python = ">=3.10"`,用 `.python-version` 固定到 3.12),使用 [uv](https://docs.astral.sh/uv/) 管理依赖。先安装 uv:https://docs.astral.sh/uv/getting-started/installation/

```bash
# 同步依赖(生成 .venv 与 uv.lock)
uv sync

# 启动(默认端口 8090)
sh -x run.sh
# 或本地调试(前台 Flask 开发服务器)
uv run python main.py

# 第一个请求: 缩放到 200x100 并转 PNG
curl -F "file=@input.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100/format,f_PNG" \
  http://127.0.0.1:8090/v1/image/process -o out.png
```
````

- [ ] **步骤 3:确认替换已落地**

运行:
```bash
grep -q "uv sync" README.md && grep -q "Python 3.12" README.md && ! grep -q "pip install -r requirements.txt" README.md && echo "readme updated" || echo "FAIL: readme not fully updated"
```
预期: `readme updated`。

- [ ] **步骤 4:提交**

```bash
git add README.md
git commit -m "Docs: README quick-start -> uv sync + Python 3.12"
```

---

### 任务 9:最终集成冒烟测试

**文件:**
- 无修改。测试产物写入 `tmp/`(已忽略)。**不提交** —— 本任务仅端到端跑 spec 的 §验证(冒烟)步骤 3–6。

**接口:**
- 依赖: 任务 1–8 完成的完整迁移服务。任务 6 的 gunicorn 配置、任务 2–5 的 app、任务 1 的 `uv run`。
- 产出: 确认服务在 8090 端口启动并能处理图片(info + process 端点),外加可选的 HEIC 输入与 AVIF 输出检查。满足 spec 的验收标准。

- [ ] **步骤 1:生成测试 JPEG(无需外部文件)**

运行:
```bash
mkdir -p tmp
uv run python -c "from PIL import Image; Image.new('RGB',(320,240),(10,20,30)).save('tmp/test.jpg')"
ls -l tmp/test.jpg
```
预期: `tmp/test.jpg` 存在(几百字节)。

- [ ] **步骤 2:后台启动 gunicorn 并等待就绪**

运行:
```bash
uv run gunicorn -c gunicorn.conf.py main:app &
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1:8090/healthcheck >/dev/null 2>&1; then echo "gunicorn up"; break; fi
  sleep 1
done
```
预期: ~20 秒内打印 `gunicorn up`(spec 验证步骤 3)。(gunicorn 按任务 6 的改动把 `gunicorn.pid` 写到项目根;步骤 6 的清理用它。若你的机器上 gunicorn 无法绑定或启动,可改用 `uv run python main.py &` —— Flask 开发服务器 —— 跑后续步骤;curl 完全相同。)

- [ ] **步骤 3:打 info 端点(spec 验证步骤 4)**

运行:
```bash
curl -s -F "file=@tmp/test.jpg" http://127.0.0.1:8090/v1/image/info
```
预期: JSON 响应,其 `data` 含 `"format": "JPEG"`、`"width": 320`、`"height": 240`,例如 `{"code":0,"data":{"width":320,"height":240,"format":"JPEG","length":...,"animated":0,"number_images":1,"id":...,"exif":{}},"msg":"success","reqeust_id":""}`。

- [ ] **步骤 4:打 process 端点 —— 缩放并转 WEBP(spec 验证步骤 5)**

运行:
```bash
curl -s -F "file=@tmp/test.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100/format,f_WEBP" http://127.0.0.1:8090/v1/image/process -o tmp/out.webp
file tmp/out.webp
uv run python -c "from PIL import Image; im=Image.open('tmp/out.webp'); print('webp', im.format, im.size)"
```
预期: `tmp/out.webp` 为 RIFF/WebP 文件;Python 检查打印 `webp WEBP (200, 150)`(320×240 经 lfit 放入 200×100 -> 200×150)。

- [ ] **步骤 5:(可选)HEIC 输入解码 + AVIF 输出(spec 验证步骤 6)**

运行:
```bash
uv run python -c "from pillow_heif import register_heif_opener; register_heif_opener(); from PIL import Image; Image.new('RGB',(100,100),(40,50,60)).save('tmp/test.heic')"
curl -s -F "file=@tmp/test.heic" http://127.0.0.1:8090/v1/image/info
curl -s -F "file=@tmp/test.jpg" -F "x-image-process=format,f_AVIF" http://127.0.0.1:8090/v1/image/process -o tmp/out.avif
uv run python -c "from PIL import Image; im=Image.open('tmp/out.avif'); print('avif', im.format, im.size)"
```
预期: HEIC 的 info curl 返回含 `"format": "HEIC"` 的 JSON;`tmp/out.avif` 解码为 `avif AVIF (320, 240)`。

- [ ] **步骤 6:停止 gunicorn 并清理**

运行:
```bash
[ -f gunicorn.pid ] && kill "$(cat gunicorn.pid)" 2>/dev/null
rm -f gunicorn.pid
```
预期: gunicorn 停止;`gunicorn.pid` 删除。(此清理无论 gunicorn 前台运行还是自行后台化都有效,因为只要设置了 `pidfile`,它总会写 `gunicorn.pid`。)

- [ ] **步骤 7:确认工作树干净(产物已被忽略)**

运行:
```bash
git status --short
```
预期: 无 `tmp/` 或 `gunicorn.pid` 未跟踪条目(均已被 gitignore)。迁移完成。

---

## 自检

**1. Spec 覆盖** —— 每个 spec 小节对应到任务:
- §目标(uv + Python 3.12 + 依赖更新 + 本地运行):任务 1、6、9。
- §uv 项目结构(`pyproject.toml`、`.python-version`、`uv.lock`、删除 `requirements.txt`、`.gitignore`):任务 1、7。
- §依赖清单(8 个依赖,移除 4 个):任务 1(pyproject)+ 任务 4(移除 `pillow-avif-plugin`/`heif-image-plugin` 用法)+ 任务 7。
- §(a) `configs.py` v1->v2:任务 2。
- §(b) `app/__init__.py` `register_heif_opener` + `app.json.ensure_ascii`:任务 4(HEIF)与任务 5(JSON)。
- §(c) `basic.py` 删除 `JSON_AS_ASCII`:任务 5。
- §(d) 删除 `import pillow_avif`(及 `import HeifImagePlugin` —— 见规划结论 #2):任务 4。
- §(e) `gunicorn.conf.py` pidfile:任务 6。
- §(f) `run.sh` `uv run`:任务 6。
- §(g) `.gitignore`:任务 1。
- §验证(冒烟)步骤 1–6:任务 1 步骤 5(依赖)、任务 4 步骤 7(app 构造 = 步骤 2)、任务 9(步骤 3–6)。
- §风险与回退:flask-log-request-id/Flask 3 规划期**误判**兼容(仅做导入期检查) -- 实际运行时 `flask_ctx_get_request_id` 懒加载已移除的 `_app_ctx_stack` 致每个带日志请求 500(冒烟测试发现);**不回退 Flask**,改用 `app/__init__.py` 的 Flask 3 fetcher shim 修复(commit bcff2ce);Pillow AVIF 已确认自带(任务 1 步骤 5);`cloghandler` 别名已确认不存在 -> 任务 3 即已应用的「回退」(现为必须);pydantic env 加载在任务 2 步骤 3 验证。

**2. 占位符扫描** —— 无 TBD/TODO/「添加适当错误处理」/「类似任务 N」。每个代码步骤含完整内容;每条命令含预期输出。

**3. 类型/签名一致性** —— `get_configs()`/`BaseConfigs`/`settings`(任务 2)与 `app/setting/__init__.py`、`app/libs/logger/__init__.py`、`app/controller/process.py`、`app/__init__.py` 中的既有用法一致。`init_app() -> Flask`、`init_config(app)`、`register_blueprints(app)` 签名不变。`register_heif_opener`(任务 4)是 `pillow_heif` 中已确认存在的真实符号。handler class `concurrent_log_handler.ConcurrentRotatingFileHandler`(任务 3)已确认存在。所有 `old_string` 锚点在其文件中唯一(已对照当前源码核实)。
