# 支持的视频网站

## 🌐 网站支持范围

本视频处理服务的所有功能（转录、下载、关键帧提取）都基于 `yt-dlp`，因此支持所有 yt-dlp 支持的视频网站。

### 📊 支持统计

- **总计**: 1000+ 个视频网站
- **主流平台**: 全部支持
- **更新频率**: 随 yt-dlp 更新而更新

## 🔥 热门网站

### 视频分享平台
- **YouTube** (youtube.com, youtu.be)
- **Bilibili** (bilibili.com)
- **Vimeo** (vimeo.com)
- **Dailymotion** (dailymotion.com)
- **Twitch** (twitch.tv)

### 社交媒体
- **Facebook** (facebook.com)
- **Instagram** (instagram.com)
- **Twitter** (twitter.com, x.com)
- **TikTok** (tiktok.com)
- **Reddit** (reddit.com)

### 直播平台
- **Twitch** (twitch.tv)
- **YouTube Live** (youtube.com/live)
- **Bilibili Live** (live.bilibili.com)

### 教育平台
- **Coursera** (coursera.org)
- **edX** (edx.org)
- **Khan Academy** (khanacademy.org)
- **Udemy** (udemy.com)

### 新闻媒体
- **BBC** (bbc.co.uk)
- **CNN** (cnn.com)
- **NBC** (nbc.com)
- **CBS** (cbs.com)

### 音乐平台
- **SoundCloud** (soundcloud.com)
- **Bandcamp** (bandcamp.com)
- **Mixcloud** (mixcloud.com)

## 🌍 地区特色网站

### 中国
- **Bilibili** (bilibili.com)
- **优酷** (youku.com)
- **腾讯视频** (v.qq.com)
- **爱奇艺** (iqiyi.com)
- **抖音** (douyin.com)

### 日本
- **Niconico** (nicovideo.jp)
- **AbemaTV** (abema.tv)

### 韩国
- **Naver TV** (tv.naver.com)
- **Afreeca TV** (afreecatv.com)

### 俄罗斯
- **VK** (vk.com)
- **Yandex** (yandex.ru)

### 欧洲
- **Arte** (arte.tv)
- **France TV** (francetv.fr)
- **ZDF** (zdf.de)

## 🔧 特殊功能支持

### 播放列表支持
- YouTube 播放列表
- Bilibili 合集
- Vimeo 专辑
- SoundCloud 播放列表

### 直播流支持
- YouTube Live
- Twitch 直播
- Bilibili 直播
- Facebook Live

### 私有/受限内容
- 需要登录的视频（通过配置认证）
- 地区限制内容（可能需要代理）
- 年龄限制内容

## 📋 完整网站列表

由于支持的网站数量庞大且持续更新，请参考官方文档获取最新的完整列表：

**yt-dlp 官方支持网站列表**:
https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

## 🧪 测试网站支持

### 快速测试
```bash
# 测试多个网站的URL验证
python test_keyframes_multisite.py

# 测试特定网站
./demo_keyframes.sh "https://vimeo.com/148751763" count 5
```

### 手动验证
1. 访问 [yt-dlp 支持网站列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
2. 找到你想测试的网站
3. 使用该网站的视频URL测试我们的API

## ⚠️ 注意事项

### 网站政策变化
- 某些网站可能会更改其API或政策
- 我们会随着 yt-dlp 的更新来保持兼容性
- 如果遇到特定网站的问题，请检查是否为最新版本

### 地区限制
- 某些内容可能有地区访问限制
- 服务器位置可能影响某些网站的访问
- 可能需要配置代理来访问特定地区的内容

### 认证要求
- 某些私有内容可能需要登录凭据
- 当前版本不支持需要认证的内容
- 未来版本可能会添加认证支持

### 版权考虑
- 请确保你有权下载和处理相关视频内容
- 遵守各网站的使用条款和版权政策
- 本服务仅供合法用途使用

## 🔄 更新机制

### 自动更新
- yt-dlp 会定期更新以支持新网站和修复问题
- 我们的Docker镜像会包含最新版本的 yt-dlp
- 建议定期更新服务以获得最佳兼容性

### 手动更新
```bash
# 更新 yt-dlp
pip install --upgrade yt-dlp

# 重启服务
docker-compose restart
```

## 📞 问题反馈

如果你发现某个网站不支持或出现问题：

1. **检查网站是否在官方支持列表中**
2. **确认URL格式是否正确**
3. **测试最新版本的 yt-dlp**
4. **提供详细的错误信息和测试URL**

我们会根据 yt-dlp 的更新来持续改进网站支持。