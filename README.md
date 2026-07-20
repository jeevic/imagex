# imagex

imagex 是一个通过 HTTP 提供的图片处理程序,处理过程指令化 pipeline,底层基于 Python Pillow。
提供功能:格式转换 / 图像裁剪 / 内切圆裁剪 / 椭圆裁剪 / 圆角矩形 / 图像缩放 / 图像旋转 / 自适应旋转 / 质量转换 / 体积限制 / 获取图片信息 / 图像置灰 / 清理设置。

## 快速开始

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

## 处理限制

- 单图大小 ≤ 20 MB
- 宽或高 ≤ 30,000 px
- 总像素 ≤ 2^30(约 2.5 亿 px)

## x-image-process 指令语法

```bash
x-image-process=${action},${param}_${value},${param}_${value}/${action},${param}_${value}
```

- **action**:图片处理操作指令,如 resize、crop。
- **param**:操作参数,如缩放宽度 w、高度 h。
- **value**:参数取值。
- `param_value` 必须成对出现,多个之间以 `,` 分割。
- 多个操作以 `/` 隔开,按给定顺序处理图片。

分隔符:

| 分隔符 | 含义                     |
| ------ | ------------------------ |
| `/`  | action 之间,前后顺序执行 |
| `,`  | 多参数项之间             |
| `_`  | 参数名与参数值之间       |

拼接顺序建议:**先裁剪后缩放 → 转格式 → 质量限制/体积限制 → 圆形/椭圆/圆角/置灰等**。

多步处理示例:

```bash
curl -F "file=@input.jpg" \
  -F "x-image-process=crop,m_auto,w_800,h_600/resize,m_lfit,w_400,h_300/format,f_WEBP/quality,q_80/circle" \
  http://127.0.0.1:8090/v1/image/process -o out.webp
# 裁剪 → 缩放 → 转 webp → 质量 → 内切圆, 按顺序执行
```

## Action 速查表

| action          | 用途                | 必填参数        | 备注                            |
| --------------- | ------------------- | --------------- | ------------------------------- |
| format          | 格式转换            | f               | 强转动图部分指令不可用          |
| crop            | 矩形裁剪            | m, w, h         | 动图默认取中间帧,first=1 取首帧 |
| circle          | 内切圆裁剪          | —              | png/webp 透明,jpg 白底          |
| ellipse         | 椭圆裁剪            | —              | 以原图宽高为基础                |
| rounded-corners | 圆角矩形            | —              | 半径超范围取短边一半            |
| resize          | 缩放                | m, w, h         | m: fixed/lfit/mfit;动图取首帧   |
| rotate          | 旋转                | a               | 动图不可旋转                    |
| auto-orient     | 自适应旋转          | o               | 0 不转,1 自适应                 |
| quality         | 质量转换 / 体积限制 | q 或 l/decr/min | 仅对有损格式生效;动图忽略       |
| gray            | 置灰                | —              | 动图不可置灰                    |
| strip           | 清理配置(exif 等)   | —              |                                 |

## Action 详解

x-image-process 可放 URL 跟参或 form 提交,以下示例统一用 form 字段提交。

### 格式转换 format

| 参数 | 类型   | 是否必须 | 说明                                  |
| ---- | ------ | -------- | ------------------------------------- |
| f    | string | 是       | 图片转换格式 PNG,JPG,JPEG,WEBP,GIF 等 |

动图强转静图后部分指令无法操作(如 rotate)。

```bash
curl -F "file=@input.jpg" -F "x-image-process=format,f_PNG" http://127.0.0.1:8090/v1/image/process -o out.png
```

### 图像裁剪 crop

| 参数  | 类型   | 是否必须 | 说明                                                   |
| ----- | ------ | -------- | ------------------------------------------------------ |
| ow    | int    | 否       | 原图宽                                                 |
| oh    | int    | 否       | 原图高                                                 |
| m     | string | 是       | 裁剪模式 枚举值 auto, center, top, bottom, left, right |
| w     | int    | 是       | 裁剪宽度,默认原图宽                                    |
| h     | int    | 是       | 裁剪高度,默认原图高                                    |
| x     | int    | 否       | 裁剪起始 x 坐标                                        |
| y     | int    | 否       | 裁剪起始 y 坐标                                        |
| first | int    | 否       | 是否裁剪首帧 0/1,1 取首帧,默认 0 取中间帧,针对动图     |

动图裁剪默认取中间帧变静图,first=1 取首帧。

```bash
curl -F "file=@input.jpg" -F "x-image-process=crop,m_auto,w_200,h_100" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 内切圆裁剪 circle

| 参数 | 类型 | 是否必须 | 说明                                    |
| ---- | ---- | -------- | --------------------------------------- |
| r    | int  | 否       | 内切圆半径,超过最小边一半则以最大内切圆 |

裁剪以图片中心为圆心,取出半径为 r 的圆形区域。png、webp 默认背景透明,jpg 默认白底。

```bash
curl -F "file=@input.jpg" -F "x-image-process=circle,r_100" http://127.0.0.1:8090/v1/image/process -o out.png
```

### 椭圆裁剪 ellipse

椭圆裁剪以原图宽高长度为基础进行椭圆裁图,无参数。

```bash
curl -F "file=@input.jpg" -F "x-image-process=ellipse" http://127.0.0.1:8090/v1/image/process -o out.png
```

### 圆角矩形 rounded-corners

| 参数 | 类型 | 是否必须 | 说明                                                       |
| ---- | ---- | -------- | ---------------------------------------------------------- |
| r    | int  | 否       | 圆角半径,范围 [1, min(width/2, height/2)],超范围取短边一半 |

png、webp 默认背景透明,jpg 默认白底。

```bash
curl -F "file=@input.jpg" -F "x-image-process=rounded-corners,r_20" http://127.0.0.1:8090/v1/image/process -o out.png
```

### 图像缩放 resize

| 参数 | 类型   | 是否必须 | 说明                                                                                        |
| ---- | ------ | -------- | ------------------------------------------------------------------------------------------- |
| m    | string | 是       | 缩放模式 fixed 强制缩放 / lfit 等比缩放限制在 w×h 内最大 / mfit 等比缩放延伸出 w×h 外最小 |
| w    | int    | 是       | 缩放宽度                                                                                    |
| h    | int    | 是       | 缩放高度                                                                                    |

动图缩放取首帧变静图。

```bash
curl -F "file=@input.jpg" -F "x-image-process=resize,m_lfit,w_200,h_100" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 图片旋转 rotate

| 参数 | 类型 | 是否必须 | 说明                                       |
| ---- | ---- | -------- | ------------------------------------------ |
| a    | int  | 是       | 旋转度数 -360 ~ 360,旋转后图片可能比原图大 |

动图不可旋转。

```bash
curl -F "file=@input.jpg" -F "x-image-process=rotate,a_90" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 自适应旋转 auto-orient

| 参数 | 类型 | 是否必须 | 说明                                  |
| ---- | ---- | -------- | ------------------------------------- |
| o    | int  | 是       | 0 按原图方向不自动旋转 / 1 自适应旋转 |

```bash
curl -F "file=@input.jpg" -F "x-image-process=auto-orient,o_1" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 质量转换 quality

| 参数 | 类型 | 是否必须 | 说明                               |
| ---- | ---- | -------- | ---------------------------------- |
| q    | int  | 是       | 相对质量,输出质量 = 原图质量 × q% |

质量只对有损压缩格式生效(JPEG、WebP、Heic 等);无损格式(PNG、TIFF、BMP、GIF 等)无效。动图无法限制体积,会忽略指令。

```bash
curl -F "file=@input.jpg" -F "x-image-process=quality,q_80" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 体积限制 quality

体积限制只对有损压缩格式生效(JPEG、WebP、Heic 等)。

| 参数 | 类型 | 是否必须 | 说明                                  |
| ---- | ---- | -------- | ------------------------------------- |
| l    | int  | 是       | 限制体积,-1 为不限制,基于质量限制大小 |
| decr | int  | 是       | 每次递减质量,加快处理                 |
| min  | int  | 是       | 最小质量                              |

动图无法限制体积。

```bash
curl -F "file=@input.jpg" -F "x-image-process=quality,l_100000,decr_5,min_20" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 图像置灰 gray

动图不可置灰。

```bash
curl -F "file=@input.jpg" -F "x-image-process=gray" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

### 清理设置 strip

去掉图片的所有配置和设置,如 exif。

```bash
curl -F "file=@input.jpg" -F "x-image-process=strip" http://127.0.0.1:8090/v1/image/process -o out.jpg
```

## 获取图片信息 /v1/image/info

请求方式:POST
Content-Type:multipart/form-data

| 参数 | 类型       | 备注                            |
| ---- | ---------- | ------------------------------- |
| file | binary raw | 处理的图片流,form-data 形式提交 |

接口以 JSON 形式返回图片信息。若图片含 exif,返回包含 exif 的完整信息;否则返回基本信息。基本信息:width(宽)、height(高)、length(大小,单位字节)、format(格式:PNG/JPG/GIF/WEBP 等)。

字段说明:

| 字段                | 说明                                         |
| ------------------- | -------------------------------------------- |
| code                | 0 成功,-1 错误                               |
| msg                 | success 或错误信息                           |
| data.width / height | 宽 / 高,单位 px                              |
| data.length         | 图片大小,单位字节                            |
| data.format         | 格式:PNG / JPG / GIF / WEBP 等               |
| data.animated       | 是否动图:0 否,1 是                           |
| data.number_images  | 帧数                                         |
| data.exif           | 若图片含 exif 则返回完整 exif;无则此字段缺省 |
| request_id          | 请求追踪 id                                  |

exif 可能字段(不限于以下):DateTime、DateTimeOriginal、DateTimeDigitized、format、gpsLatitude、gpsLatitudeRef、gpsLongitude、gpsLongitudeRef、imageHeight、imageWidth、imageSize、make、model、orientation、resolutionX、resolutionY、resolutionUnit。

完整 exif 示例:

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

## 响应与错误

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

错误 HTML 模板:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ .title }}</title></head>
<body></body>
</html>
```

失败示例:

```bash
# 缺少 x-image-process
curl -F "file=@input.jpg" http://127.0.0.1:8090/v1/image/process
# HTTP 400, <title>[process] no image  process str</title>

# 未上传文件
curl -F "x-image-process=resize,m_lfit,w_200,h_100" http://127.0.0.1:8090/v1/image/process
# HTTP 400, <title>[process] upload no image file</title>
```
