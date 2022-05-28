## imagex
**imagex 是一个通过 http形式提供的强大图片处理程序 处理过程 pipeline指令化 底层基于 python pillow simd**

**提供功能有:** 
 - 格式转换
 - 图像裁剪
 - 内切圆裁剪
 - 图像缩放
 - 图像旋转
 - 质量转换
 - 体积限制
 - 获取图片信息
 - 图像置灰
 - 清理设置

## 启动程序
程序基于python3.8开发  基于requirements安装依赖,  底层图片依赖参考pillow官方文档:https://pillow.readthedocs.io/en/stable/installation.html
启动命令:

```bash
sh -x run.sh
```
默认启动端口8090


## 提供处理接口
**接口:   /v1/image/process**
请求方式： POST
Content-Type: multipart/form-data

**请求参数:**

|参数  |类型  |备注 |
|--|--|--|
| x-image-process | string | 指令化裁剪参数	也可GET形式放在url 中跟参|
| file | binary raw | 	处理的图片流 form-data 形式提交| 

**图片处理要求:**
原图大小不能超过 20 MB
图片宽或者高不能超过30,000 px，且总像素不能超过2.5亿 px(目前支持: 2^30像素)

图片处理成功, http状态码200 并输出图片
图片处理失败, http 状态码非200  并有可能输出 html 信息
错误返回 html:  title为错误信息

```bash
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ .title }}</title></head>
<body></body>
</html>
```

## x-image-process指令裁剪参数
x-image-process指令化参数是处理图片定义的一种参数形式 形式如:

```bash
x-image-process=${action},${param}_${value},${param}_${value}/${action},${param}_${value}
```
**action**: 图片处理的操作指令（action）每种图片处理命令称作一种action，比如缩放resize，裁剪crop等
**param:** 操作传递的参数 每种action支持多种具体的处理参数，比如缩放宽度w,高度h等。
**value:** v处理参数取值。
其中param_value必须成对出现 多个之间,分割
多个操作以正斜线（/）隔开，按给定图片参数的顺序处理图片

**分隔符:**
**/:**   处理分隔符	 多个action之间的分隔符，前后action顺序执行
**,:**  多处理参数项之间的分隔符
**_:**	参数名与参数值之间的分隔符

如: 

```bash
x-image-process=resize,m_lfit,w_200,h_100 
表示缩放图片到宽200px 高100px 方式是 lfit

多操作处理 
?x-image-process=resize,m_lfit,w_200,h_100/format,f_PNG 
表示缩放图片后在设置格式为 png
```
指令 pipeline 拼接顺序建议: 先裁剪后缩缩放, 再转格式 而后进行设置质量、大小限制、圆形、 椭圆、 置灰等操作

## 支持处理action
 - **格式转换**
 action名称: **format**
参数:

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| f | string |是|图片转换格式	PNG,JPG,JPEG,WEBP,GIF等|

请求实例: ?x-image-process=format,f_PNG 转为 PNG 格式
动图强转静图  部分指令无法操作 如:rotate 

 - **图像裁剪**
  普通矩形裁剪
 action名称: **crop**
参数:

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| ow| int |否 |原图宽图 |
| oh| int |否|原图高度|
| m| string |是|裁剪模式  枚举值auto, center, top, bottom, left, right|
| w| int |是|裁剪宽度  裁剪后图片的宽度，如果指定的宽度超过了图片的宽度，则以图片宽度为准裁剪。单位为px。非必选，默认值原始图片宽度。
| h| int |是|裁剪高度 裁剪后图片的高度，如果指定的高度超过了图片的高度，则以图片高度为准裁剪。单位为px。非必选，默认值原始图片高度。|
| x| int |否|裁剪起始x坐标|
| y| int |否|裁剪起始y坐标|
| first| int |否|是否裁剪首帧 取值0 或1 1 代表裁剪首帧 默认0 不裁剪首帧取中间帧 针对动图|

如:?x-image-process=crop,m_auto,w_200,h_100
注意:  动图裁剪默认取一帧进行裁剪变静图 设置first=1取首帧 不设置则取中间帧


 - **内切圆裁剪**
action: **circle**

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| r| int |否 |内切圆半径 超过原图长宽0- 以最小边一半为半径 |

裁剪以图片中心为圆心，从图片取出的半径为r的圆形区域，r如果超过最小边大小的一半，默认取原圆的最大内切圆。
png、webp默认背景为透明，jpg默认背景为白色

 - **椭圆裁剪**
action: **ellipse**
椭圆裁剪将会以原图宽高长度为基础进行椭圆裁图
如:?x-image-process=ellipse 
	
 - **圆角矩形**
action: **rounded-corners**

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| r| int |否 | 圆角半径|

圆角半径，范围[1, min(width/2, height/2)]，如果半径参数超出范围，则使用图像短边的一半。设置此参数后，返回的图像四角为圆角，png、webp默认背景为透明，jpg默认背景为白色

	
 - **图像缩放**
action: **resize**
在图基础上进行缩放操作

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| m| string |是|图片缩放模式  fixed - 强制缩放 lfit - 等比缩放，缩放图限制为指定w与h矩形内的最大图片 也就是说原图421*422 缩放1000*1000 我们最大给出421*421图片
mfit：等比缩放，缩放图为延伸出指定w与h的矩形框外的最小图片 参考: https://cloud.baidu.com/doc/BOS/s/gkbisf3l4|
| w| int |是|缩放宽度 |
| h| int |是|缩放高度 |
注意:动图缩放会抽取首帧进行缩放变为静图

 - **图片旋转**
action: **rotate**

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| a| int |是 | int	-360 - 360	是	旋转指定度数, 旋转后图片可能会比原图宽高大	
注意:动图无法旋转|

 - **自适应旋转**
action: **auto-orient**

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| o| int |是 |int	0,1	是	0：按原图默认方向，不自动旋转；1：自适应旋转。|


 - **质量转换**
action: **quality**

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| q| int |是 |指定图片的相对质量，假设原图质量为N，输出质量为N * q%	
动图无法限制体积 会忽略指令|

质量只对有损压缩的图片格式生效，包括JPEG, WebP, Heic等。对于无损压缩的图片格式，包括PNG, TIFF，BMP, GIF等，则不会产生效果。



 - **体积限制**
action: **quality**
体积限制只对有损压缩的图片格式生效，包括JPEG, WebP, Heic等

|参数  |类型  |是否必须 |说明 |
|--|--|--|--|
| l| int |是 |限制图片的体积 -1 为不限制 基于质量限制大小	|
| decr| int |是 |每次递减质量 加快处理速度|
| min| int |是 |最小的质量	 动图无法限制体积|


 - **图像置灰**
action: **gray**
动图无法置灰


 - **清理设置 **
action: **strip**
去掉图片的所有配置和设置 如 exif

## 获取图片信息接口
**接口:   /v1/image/info**
请求方式： POST
Content-Type: multipart/form-data

**请求参数:**

|参数  |类型  |备注 |
|--|--|--| 
| file | binary raw | 	处理的图片流 form-data 形式提交| 

接口已 json 形式返回图片信息

如果图片有 exif 信息，则返回包含 exif 的完整信息，如果图片不包含 exif 信息，则返回图片的基本信息
基本信息如下: width(宽), height(高), length(大小) 单位:字节, format(格式): PNG, JPG,  GIF, WEBP 等 

exif: 包含 exif 信息 不限于以下
dateTime、dateTimeOriginal、dateTimeDigitized、format、gpsLatitude、gpsLatitudeRef、gpsLongitude、gpsLongitudeRef、imageHeight、imageWidth、imageSize、make、model、orientation、resolutionX、resolutionY、resolutionUnit
错误 code= -1

返回值参考
```bash
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
}```

