# JmCli
## 依赖
pip install -r requirements.txt安装依赖项

## 配置步骤
1.打开AstrBot的UI面板 → 插件管理 → 找到JmCli → 点击插件配置打开配置页。

2.打开可用的jm网站(可前往[禁漫天堂发布页](https://jmcmomic.github.io)查看) → 将你能进入的网址添加到插件配置页的禁漫域名列表(domain_list)中，如18comic.vip，可添加多个。

3.登录你的jm账号 → 按f12审查元素 → 点击应用程序 → Cookie → 找到你在用的jm网址 → 将AVS值复制进插件配置页的AVS Cookie值(avs_cookie)中。

4.若进不去网址，可添加代理设置，格式例如: http://127.0.0.1:8080

配置完成！

## 注意事项
1.下载好的封面以及本子不会自动清理，请手动清理，目录位于

（你的AstrBot路径）\AstrBot\data\plugins\JmCli\pdf  
（你的AstrBot路径）\AstrBot\data\plugins\JmCli\picture  

2.下载封面提取的并不是封面，而是本子的第一张图片

3.AVS值只对应一个网址，建议将访问最快的网址添加到列表的第一个（最上面）

## 支持
### 文档
[Astrbot文档](https://astrbot.app/what-is-astrbot.html)

[JMComic文档](https://jmcomic.readthedocs.io/zh-cn/latest/)

### GitHub
[Astrbot](https://github.com/AstrBotDevs/AstrBot)

[JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)
