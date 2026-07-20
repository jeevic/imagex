# imagex README 重写设计

**日期:** 2026-07-20
**范围:** 仅 `README.md` 重写,不改动任何源码。
**语言:** 中文(与现有 README 一致)。

## 目标

当前 README 信息完整但组织零散:action 详解靠散文叙述、缺少可跑示例、错误返回格式与响应结构分散。重写目标是在**保留全部实质内容**(每 action 完整参数表、info 端点完整 exif 示例、处理限制数值、pipeline 顺序建议)的前提下,重新组织为一份新用户 10 秒内能跑通、老用户一屏速查的文档。

## 非目标

- 不新建文档站点(mkdocs/Hugo 等)。
- 不写客户端 SDK。
- 不改源码、不改接口、不改返回结构。
- 不为准确性去核对源码与实际行为之外的内容——文档只描述现有行为,不引入新约定。

## 整体结构

自顶向下八节:

1. **标题 + 一句话定位**
2. **快速开始** —— 3 行可跑(安装依赖 / `sh -x run.sh` / 第一条 curl)
3. **处理限制** —— 保留原数值,一句话压缩
4. **x-image-process 指令语法** —— 语法 / 分隔符表 / 顺序建议(前置到此处)
5. **Action 速查表** —— 一屏总览所有 action
6. **Action 详解** —— 逐个:一句话 + 原参数表 + 一条可跑 curl
7. **获取图片信息 /v1/image/info** —— 请求 / 返回字段 / 完整 exif 示例
8. **响应与错误** —— 成功与失败的 HTTP/Body 形态 + 错误 HTML 模板 + 失败 curl 示例

设计意图:快速开始先给可跑示例;速查表让用户一屏看完所有 action;详解保留原参数表;顺序建议前置到语法节,避免用户先组合再回头查。

## 各节具体内容

### 第 1 节 标题 + 定位

```
# imagex

imagex 是一个通过 HTTP 提供的图片处理程序,处理过程指令化 pipeline,底层基于 Python Pillow。
提供功能:格式转换 / 图像裁剪 / 内切圆裁剪 / 椭圆裁剪 / 圆角矩形 / 图像缩放 / 图像旋转 / 自适应旋转 / 质量转换 / 体积限制 / 获取图片信息 / 图像置灰 / 清理设置。
```

### 第 2 节 快速开始

```bash
# 安装依赖 (参考 Pillow 安装: https://pillow.readthedocs.io/en/stable/installation.html)
pip install -r requirements.txt

# 启动 (默认端口 8090)
sh -x run.sh

# 第一个请求: 缩放到 200x100 并转 PNG
curl -F "file=@input.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100/format,f_PNG" \
  http://127.0.0.1:8090/v1/image/process -o out.png
```

说明:程序基于 Python 3.8 开发。

### 第 3 节 处理限制

- 单图大小 ≤ 20 MB
- 宽或高 ≤ 30,000 px
- 总像素 ≤ 2^30(约 2.5 亿 px)

### 第 4 节 x-image-process 指令语法

语法:

```
x-image-process=${action},${param}_${value},${param}_${value}/${action},${param}_${value}
```

- **action**:图片处理操作指令,如 resize、crop。
- **param**:操作参数,如缩放宽度 w、高度 h。
- **value**:参数取值。
- `param_value` 必须成对出现,多个之间以 `,` 分割。
- 多个操作以 `/` 隔开,按给定顺序处理图片。

分隔符表:

| 分隔符 | 含义 |
|--|--|
| `/` | action 之间,前后顺序执行 |
| `,` | 多参数项之间 |
| `_` | 参数名与参数值之间 |

拼接顺序建议:**先裁剪后缩放 → 转格式 → 质量限制/体积限制 → 圆形/椭圆/圆角/置灰等**。

多步示例(与顺序建议呼应):

```bash
curl -F "file=@input.jpg" \
  -F "x-image-process=crop,m_auto,w_800,h_600/resize,m_lfit,w_400,h_300/format,f_WEBP/quality,q_80/circle" \
  http://127.0.0.1:8090/v1/image/process -o out.webp
# 裁剪 → 缩放 → 转 webp → 质量 → 内切圆, 按顺序执行
```

### 第 5 节 Action 速查表

| action | 用途 | 必填参数 | 备注 |
|--|--|--|--|
| format | 格式转换 | f | 强转动图部分指令不可用 |
| crop | 矩形裁剪 | m, w, h | 动图默认取中间帧,first=1 取首帧 |
| circle | 内切圆裁剪 | — | png/webp 透明,jpg 白底 |
| ellipse | 椭圆裁剪 | — | 以原图宽高为基础 |
| rounded-corners | 圆角矩形 | — | 半径超范围取短边一半 |
| resize | 缩放 | m, w, h | m: fixed/lfit/mfit;动图取首帧 |
| rotate | 旋转 | a | 动图不可旋转 |
| auto-orient | 自适应旋转 | o | 0 不转,1 自适应 |
| quality | 质量转换 / 体积限制 | q 或 l/decr/min | 仅对有损格式生效;动图忽略 |
| gray | 置灰 | — | 动图不可置灰 |
| strip | 清理配置(exif 等) | — | |

### 第 6 节 Action 详解

每个 action 小节统一格式:一句话作用 → 原参数表(保留全部列与说明)→ 一条可跑 curl。
x-image-process 统一用 form 字段提交(与 README 现有"GET 放 URL 跟参或 form 提交"两种方式一致,此处统一用 form 更直观)。
curl 统一指向 `http://127.0.0.1:8090/v1/image/process`,输入 `@input.jpg`,`-o` 指定输出。

逐个 action 的内容(参数表原文保留,这里只列示例 curl):

- **format**: `curl -F "file=@input.jpg" -F "x-image-process=format,f_PNG" http://127.0.0.1:8090/v1/image/process -o out.png`
- **crop**: `curl -F "file=@input.jpg" -F "x-image-process=crop,m_auto,w_200,h_100" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **circle**: `curl -F "file=@input.jpg" -F "x-image-process=circle,r_100" http://127.0.0.1:8090/v1/image/process -o out.png`
- **ellipse**: `curl -F "file=@input.jpg" -F "x-image-process=ellipse" http://127.0.0.1:8090/v1/image/process -o out.png`
- **rounded-corners**: `curl -F "file=@input.jpg" -F "x-image-process=rounded-corners,r_20" http://127.0.0.1:8090/v1/image/process -o out.png`
- **resize**: `curl -F "file=@input.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **rotate**: `curl -F "file=@input.jpg" -F "x-image-process=rotate,a_90" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **auto-orient**: `curl -F "file=@input.jpg" -F "x-image-process=auto-orient,o_1" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **quality**: `curl -F "file=@input.jpg" -F "x-image-process=quality,q_80" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **gray**: `curl -F "file=@input.jpg" -F "x-image-process=gray" http://127.0.0.1:8090/v1/image/process -o out.jpg`
- **strip**: `curl -F "file=@input.jpg" -F "x-image-process=strip" http://127.0.0.1:8090/v1/image/process -o out.jpg`

各 action 的原参数表(逐字保留自现有 README,不删列不删行):

**format**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| f | string | 是 | 图片转换格式 PNG,JPG,JPEG,WEBP,GIF 等 |

**crop**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| ow | int | 否 | 原图宽 |
| oh | int | 否 | 原图高 |
| m | string | 是 | 裁剪模式 枚举值 auto, center, top, bottom, left, right |
| w | int | 是 | 裁剪宽度,默认原图宽 |
| h | int | 是 | 裁剪高度,默认原图高 |
| x | int | 否 | 裁剪起始 x 坐标 |
| y | int | 否 | 裁剪起始 y 坐标 |
| first | int | 否 | 是否裁剪首帧 0/1,1 取首帧,默认 0 取中间帧,针对动图 |

**circle**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| r | int | 否 | 内切圆半径,超过最小边一半则以最大内切圆 |

**ellipse**:无参数。

**rounded-corners**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| r | int | 否 | 圆角半径,范围 [1, min(width/2, height/2)],超范围取短边一半 |

**resize**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| m | string | 是 | 缩放模式 fixed 强制缩放 / lfit 等比缩放限制在 w×h 内最大 / mfit 等比缩放延伸出 w×h 外最小 |
| w | int | 是 | 缩放宽度 |
| h | int | 是 | 缩放高度 |

**rotate**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| a | int | 是 | 旋转度数 -360 ~ 360,旋转后图片可能比原图大 |

**auto-orient**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| o | int | 是 | 0 按原图方向不自动旋转 / 1 自适应旋转 |

**quality(质量转换)**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| q | int | 是 | 相对质量,输出质量 = 原图质量 × q% |

**quality(体积限制)**

| 参数 | 类型 | 是否必须 | 说明 |
|--|--|--|--|
| l | int | 是 | 限制体积,-1 为不限制,基于质量限制大小 |
| decr | int | 是 | 每次递减质量,加快处理 |
| min | int | 是 | 最小质量 |

补充说明(保留原文要点):
- 动图强转静图后部分指令无法操作(如 rotate)。
- 动图裁剪默认取中间帧变静图,first=1 取首帧。
- circle/rounded-corners:png、webp 默认背景透明,jpg 默认白底。
- 动图缩放取首帧变静图。
- 动图不可旋转。
- 质量与体积限制仅对有损格式(JPEG、WebP、Heic 等)生效;无损格式(PNG、TIFF、BMP、GIF 等)无效;动图无法限制体积,会忽略指令。
- 动图不可置灰。

### 第 7 节 获取图片信息 /v1/image/info

请求:
- POST /v1/image/info
- Content-Type: multipart/form-data
- 参数:file(binary,form-data 提交)

成功返回 JSON 结构:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "width": 1936,
    "height": 4000,
    "format": "JPEG",
    "length": 2652164,
    "animated": 0,
    "number_images": 1,
    "exif": { ... }
  },
  "request_id": "f59f5733-d794-4509-b6ba-deeb8b171bd9"
}
```

字段说明:

| 字段 | 说明 |
|--|--|
| code | 0 成功,-1 错误 |
| msg | success 或错误信息 |
| data.width / height | 宽 / 高,单位 px |
| data.length | 图片大小,单位字节 |
| data.format | 格式:PNG / JPG / GIF / WEBP 等 |
| data.animated | 是否动图:0 否,1 是 |
| data.number_images | 帧数 |
| data.exif | 若图片含 exif 则返回完整 exif;无则此字段缺省 |
| request_id | 请求追踪 id |

exif 可能字段(不限于以下):DateTime、DateTimeOriginal、DateTimeDigitized、format、gpsLatitude、gpsLatitudeRef、gpsLongitude、gpsLongitudeRef、imageHeight、imageWidth、imageSize、make、model、orientation、resolutionX、resolutionY、resolutionUnit。

完整 exif 示例(原样保留 README 现有那块 JSON,不删字段):

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "width": 1936,
    "height": 4000,
    "format": "JPEG",
    "length": 2652164,
    "animated": 0,
    "number_images": 1,
    "exif": {
      "DateTime": "2021:08:07 17:48:33",
      "DateTimeDigitized": "2021:08:07 17:48:33",
      "DateTimeOriginal": "2021:08:07 17:48:33",
      "ExifOffset": "137",
      "ExposureBiasValue": "0/100",
      "ExposureMode": "0",
      "ExposureTime": "8333333/1000000000",
      "FNumber": "260/100",
      "Flash": "0",
      "FocalLength": "530/100",
      "FocalLengthIn35mmFilm": "28",
      "GPSDateStamp": "2021:08:07",
      "GPSInfo": "371",
      "GPSLatitude": "39/1, 57/1, 393/100",
      "GPSLatitudeRef": "N",
      "GPSLongitude": "116/1, 33/1, 5807/100",
      "GPSLongitudeRef": "E",
      "GPSTimeStamp": "9/1, 48/1, 33/1",
      "Make": "meizu",
      "MeteringMode": "2",
      "Model": "16s",
      "Orientation": "1",
      "PhotographicSensitivity": "111",
      "Software": "Meizu Camera",
      "UserComment": "101, 110, 100",
      "WhiteBalance": "0",
      "thumbnail:JPEGInterchangeFormat": "562",
      "thumbnail:JPEGInterchangeFormatLength": "8678"
    }
  },
  "request_id": "f59f5733-d794-4509-b6ba-deeb8b171bd9"
}
```

示例:

```bash
curl -F "file=@input.jpg" http://127.0.0.1:8090/v1/image/info
```

### 第 8 节 响应与错误

成功(process 端点):
- HTTP 200
- Body:处理后的图片二进制
- Content-Type:对应输出格式(PNG / JPEG / WEBP 等)

成功(info 端点):
- HTTP 200
- Body:上述 JSON

失败:
- HTTP 非 200
- Body:HTML,`<title>` 为错误信息

错误 HTML 模板(保留原文):

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ .title }}</title></head>
<body></body>
</html>
```

失败示例(对应 controller 中两个校验分支):

```bash
# 缺少 x-image-process
curl -F "file=@input.jpg" http://127.0.0.1:8090/v1/image/process
# HTTP 400, <title>[process] no image process str</title>

# 未上传文件
curl -F "x-image-process=resize,m_lfit,w_200,h_100" http://127.0.0.1:8090/v1/image/process
# HTTP 400, <title>[process] upload no image file</title>
```

## 实现方式

- 仅替换 `README.md` 全文。
- 不改动任何源码、配置、接口。
- 不新增文件。

## 验收标准

- 新 README 含全部八节,顺序如上。
- 每个 action 保留原参数表(列与说明齐全,无删减)。
- 第 7 节 info 完整 exif JSON 与现有一致。
- 第 3 节限制数值与原文一致(20 MB / 30,000 px / 2^30)。
- 每个 action 附一条可跑 curl;第 4 节附一条多步 pipeline curl。
- 第 8 节附错误 HTML 模板与两条失败 curl。
- 全文中文。

## 不确定项

无。所有内容来自现有 README,重写不引入新约定。
