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
