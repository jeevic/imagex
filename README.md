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

| 分隔符 | 含义 |
|--|--|
| `/` | action 之间,前后顺序执行 |
| `,` | 多参数项之间 |
| `_` | 参数名与参数值之间 |

拼接顺序建议:**先裁剪后缩放 → 转格式 → 质量限制/体积限制 → 圆形/椭圆/圆角/置灰等**。

多步处理示例:

```bash
curl -F "file=@input.jpg" \
  -F "x-image-process=crop,m_auto,w_800,h_600/resize,m_lfit,w_400,h_300/format,f_WEBP/quality,q_80/circle" \
  http://127.0.0.1:8090/v1/image/process -o out.webp
# 裁剪 → 缩放 → 转 webp → 质量 → 内切圆, 按顺序执行
```

## Action 速查表

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
