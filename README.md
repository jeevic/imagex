# imagex
imagex 是一个通过 http 服务提供的图片处理web 程序 底成基于 python pillow simd
功能有: 格式转换、图像裁剪、内切圆裁剪、图像缩放、图像旋转、质量转换
、体积限制、获取图片信息 、图像置灰、清理设置  
### 指令化裁剪接口
接口:   /v1/image/process

请求方式： POST

Content-Type: multipart/form-data
```
参数:
x-image-process
string	指令化裁剪参数	也可 GET放在 url 中
file	binary	处理的图片流
图片处理要求:

原图大小不能超过 20 MB

图片宽或者高不能超过30,000 px，且总像素不能超过2.5亿 px(目前支持: 2^30像素)



图片处理成功, http状态码200 并输出图片

图片处理失败, http 状态码非200  并有可能输出 html 信息

错误返回 html:
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ .title }}</title></head>
<body></body>
</html>



指令化参数:

指令化参数是处理图片定义的一种参数形式 形式如:

x-image-process=${action},${key}\_${value},${key}\_${value}/${action},${key}\_${value}
action,parame_value：图片处理的操作（action）、参数（parame）和值（value），用于定义图片处理的方式。多个操作以正斜线（/）隔开，按给定图片参数的顺序处理图片。

使用x-image-process参数触发图片处理 其中:	

action：支持多种图片处理命令，每种图片处理命令称作一种action，比如缩放resize，裁剪crop等。
key：每种action支持多种具体的处理参数，比如缩放宽度w,高度h等。
value：处理参数取值。
分隔符:

处理分隔符	/	有关	多个action之间的分隔符，前后action顺序执行
参数分隔符	,	无关	多处理参数项之间的分隔符
值分隔符	_	固定顺序	参数名与参数值之间的分隔符
如:   x-image-process=resize,m_lfit,w_200,h_100  表示缩放图片到宽200px 高100px 方式是 lfit

多操作处理 ?x-image-process=resize,m_lfit,w_200,h_100/format, f_PNG 表示缩放图片后在设置格式为 png

指令 pipeline 拼接顺序建议: 先裁剪后缩缩放, 再转格式 而后进行设置质量、大小限制、圆形、 椭圆、 置灰等操作

支持处理action


1、传入原图信息
将原图信息传入裁图服务     (目前此信息未使用)

 action名称: ininfo

1	len	int	
否	图片大小 单位:字节	
2	w	int	
否	图片宽 单位:像素	
3	h	int	
否	图片高 单位:像素	
4	f	string	PNG,JPG,JPEG,WEBP,GIF等	否	图片格式	
5	animated	int	0-否 1-是	否	动图标识	
6	id	string	
图片标志id or url or filename

不超过200个字节

否	图片的标识	




请求实例: ?x-image-process=ininfo,len_65535,w_200,h_100,animated_1,id_0OqXSMXbgX

2、格式转换
图片格式转换

action名称: format

1	f	string	PNG,JPG,JPEG,WEBP,GIF	是	图片转换格式	转换格式耗时高建议尽量放在最后
请求实例: ?x-image-process=format,f_PNG

动图强转静图  部分指令无法操作 如:rotate 

3、图像裁剪
普通矩形裁剪

action名称:  crop

ow:原图宽度 oh:原图高度

1	m	string	
auto, center, top, bottom, left, right

是	
裁剪模式

auto:填写 w,h,x,y 参数

center:裁剪中心点位于图片中心位置

left:x=0, y=(oh-h)/2位置开始裁剪

right: x=(ow-w) y=(oh-h)/2位置开始裁剪

top: x=(ow-w)/2 y=0位置开始裁剪

bottom: x=y=(oh-h)/2 y=(oh-h)位置开始裁剪


2	w	int	裁剪宽度	是	
裁剪后图片的宽度，如果指定的宽度超过了图片的宽度，则以图片宽度为准裁剪。单位为px。非必选，默认值原始图片宽度。
3	h	int	裁剪高度	是	
裁剪后图片的高度，如果指定的高度超过了图片的高度，则以图片高度为准裁剪。单位为px。非必选，默认值原始图片高度。
4	x	int	裁剪起始x坐标	否	

5	y	int	裁剪起始y坐标	否	

6	
first

int	是否裁剪首帧	否	
取值0 或1

1 代表裁剪首帧

默认0 不裁剪首帧取中间帧


如:?x-image-process=crop,m_auto,w_200,h_100

注意:  动图裁剪默认取一帧进行裁剪变静图 设置first=1取首帧 不设置则取中间帧



4、内切圆裁剪
action: circle

1	r	int	
0- 以最小边一半为半径



是	
以图片中心为圆心，从图片取出的半径为r的圆形区域，r如果超过最小边大小的一半，默认取原圆的最大内切圆。

png、webp默认背景为透明，jpg默认背景为白色

椭圆裁剪

action: ellipse

椭圆裁剪将会以原图宽高长度为基础进行椭圆裁图

如:?x-image-process=ellipse 





5、圆角矩形

action:  rounded-corners

1	r	int	[1, min(width/2, height/2)]	

圆角半径，范围[1, min(width/2, height/2)]，如果半径参数超出范围，则使用图像短边的一半。设置此参数后，返回的图像四角为圆角，png、webp默认背景为透明，jpg默认背景为白色






6、图像缩放
在图基础上进行缩放操作

action: resize

1	m	string	
fixed - 强制缩放

lfit - 等比缩放，缩放图限制为指定w与h的矩形内的最大图片 也就是说原图421*422 缩放1000*1000 我们最大给出421*421图片

mfit：等比缩放，缩放图为延伸出指定w与h的矩形框外的最小图片







是	
图片缩放模式



参考: https://cloud.baidu.com/doc/BOS/s/gkbisf3l4
2	w	int	裁剪宽度	是	
裁剪后图片的宽度，如果指定的宽度超过了图片的宽度，则以图片宽度为准裁剪。单位为px。非必选，默认值原始图片宽度。
3	h	int	裁剪高度	是	
裁剪后图片的高度，如果指定的高度超过了图片的高度，则以图片高度为准裁剪。单位为px。非必选，默认值原始图片高度。
注意:动图缩放会抽取首帧进行缩放变为静图



7、图像旋转
图片旋转

action:  rotate

a	int	-360 - 360	是	旋转指定度数, 旋转后图片可能会比原图宽高大	
注意:动图无法旋转

自适应旋转

图像可以根据 exif 信息进行自适应旋转。 目前主要是 jpg

action:  auto-orient

1	o	int	0,1	是	0：按原图默认方向，不自动旋转；1：自适应旋转。	


8、质量转换
设置图片编码质量。

质量只对有损压缩的图片格式生效，包括JPEG, WebP, Heic等。对于无损压缩的图片格式，包括PNG, TIFF，BMP, GIF等，则不会产生效果。

action:  quality

1	q	int	0 - 100	是	指定图片的相对质量，假设原图质量为N，输出质量为N * q%	
动图无法限制体积 会忽略指令



9、体积限制
设置图片体积

体积限制只对有损压缩的图片格式生效，包括JPEG, WebP, Heic等

action: limit

1	l	int	n	是	限制图片的体积 -1 为不限制 基于质量限制大小	
2	decr	int	n	否	每次递减质量	
3	min	int	n	int	最小的质量	
动图无法限制体积



10、获取图片信息    
如果图片有 exif 信息，则返回包含 exif 的完整信息，如果图片不包含 exif 信息，则返回图片的基本信息

基本信息如下: width(宽), height(高), length(大小) 单位:字节, format(格式): PNG, JPG,  GIF, WEBP 等 

exif: 包含 exif 信息 不限于以下

dateTime、dateTimeOriginal、dateTimeDigitized、format、gpsLatitude、gpsLatitudeRef、gpsLongitude、gpsLongitudeRef、imageHeight、imageWidth、imageSize、make、model、orientation、resolutionX、resolutionY、resolutionUnit

action:info

请求示例: ?x-image-process=info

获取图片信息建议使用: /v1/image/info   会有10倍性能提升

错误 code= -1

参考:

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


11、图像置灰
action:  gray

动图无法置灰



12、清理设置  
去掉图片的所有配置和设置 如 exif
action: strip

```