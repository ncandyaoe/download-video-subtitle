# 视频处理 API 服务 v2.2

[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](./VERSION)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](./docker-compose.yml)
[![API](https://img.shields.io/badge/API-async-orange.svg)](./API_DOCUMENTATION.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

本项目是一个功能全面的高性能视频处理 API 服务，提供视频转录、下载、关键帧提取、视频合成等多种功能。支持数百个视频平台（基于 yt-dlp），采用异步处理架构，完美解决长视频处理时的连接超时问题。

v2.2 版本在异步处理基础上新增了视频下载、关键帧提取、视频合成等功能，并优化了内存使用和硬件加速支持。

## ✨ v2.2 新特性

- **🚀 异步处理**：采用后台任务处理，支持长视频处理，无连接超时问题
- **📊 实时进度**：提供0-100%的详细进度监控和状态查询
- **🎬 视频下载**：支持多种质量和格式的视频下载功能
- **🖼️ 关键帧提取**：智能提取视频关键帧，生成预览图和缩略图网格
- **🎞️ 视频合成**：支持多种合成模式（拼接、画中画、并排显示等）
- **⚡ 性能优化**：硬件加速、内存优化、缓存管理
- **🔄 分离式API**：状态查询和结果获取分离，提升用户体验
- **🛡️ 稳定性增强**：智能资源监控、自动垃圾回收、Docker资源限制
- **📚 完整文档**：详细的API文档和集成指南

## 🏗️ 核心功能

### 🎯 视频处理功能
- **异步转录**：支持长达2小时的视频转录，无阻塞处理
- **视频下载**：支持多种质量（720p、1080p、4K）和格式（MP4、WebM、MKV）
- **关键帧提取**：智能提取视频关键帧，支持多种提取方法和自定义参数
- **视频合成**：支持多种合成模式，包括拼接、画中画、并排显示等
- **本地文件处理**：直接处理本地视频文件，无需上传

### 🌐 平台支持
- **多平台支持**：基于 `yt-dlp`，支持数百个视频网站
- **主流平台**：YouTube、Bilibili、Vimeo、Dailymotion、TikTok等
- **高精度识别**：使用 `faster-whisper` 模型，准确率高
- **丰富元数据**：返回标题、作者、封面、统计数据等完整信息

### 🔧 技术特性
- **标准化API**：RESTful设计，易于集成到各种系统中
- **硬件加速**：支持GPU加速和硬件编码器（NVENC、VideoToolbox等）
- **智能缓存**：自动缓存管理，提升处理效率
- **资源监控**：实时监控CPU、内存使用情况

## 🚀 快速开始

### 1. 环境准备

你需要先在你的电脑上安装 Python (建议 3.8 或更高版本)。

### 2. 安装依赖

本项目依赖的一些第三方库和工具需要先进行安装。

首先，克隆或下载本项目到你的电脑上，然后进入项目目录 `download-video-subtitle 2`。

```bash
# 进入项目目录
cd "download-video-subtitle 2"

# 安装所有需要的 Python 库
pip install -r requirements.txt
```

> **注意**: `yt-dlp` 依赖 `ffmpeg` 来处理音频。你需要确保你的系统上安装了 `ffmpeg`。
> - **Windows**: 下载 `ffmpeg` 后，将其 `bin` 目录添加到系统环境变量 `Path` 中。
> - **macOS**: `brew install ffmpeg`
> - **Linux**: `sudo apt update && sudo apt install ffmpeg`

### 3. 启动服务

安装完所有依赖后，运行以下命令即可启动 API 服务：

```bash
python run.py
```

服务启动后，你会在终端看到类似下面的信息，代表服务已经成功运行在 7878 端口：

```
INFO:     Uvicorn running on http://0.0.0.0:7878 (Press CTRL+C to quit)
```

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 克隆项目
git clone <your-repo-url>
cd download-video-subtitle-2

# 使用 Docker Compose 启动
docker-compose up -d --build

# 查看服务状态
docker-compose ps
```

### 健康检查

```bash
# 检查服务是否正常运行
curl http://localhost:7878/health

# 查看服务日志
docker logs subtitle-service -f
```

## 📚 API v2.2 使用说明

v2.2 在异步处理架构基础上新增了视频下载和关键帧提取功能。

### 转录功能使用

转录API 使用分为三个步骤：

### 1. 启动转录任务

**Endpoint**: `POST /generate_text_from_video`

```bash
curl -X POST "http://localhost:7878/generate_text_from_video" \
-H "Content-Type: application/json" \
-d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

**响应**:
```json
{
  "task_id": "uuid-string",
  "status": "started",
  "message": "转录任务已启动，请使用task_id查询进度"
}
```

### 2. 查询任务状态

**Endpoint**: `GET /task_status/{task_id}`

```bash
curl -X GET "http://localhost:7878/task_status/your-task-id"
```

**响应**:
```json
{
  "task_id": "uuid-string",
  "status": "processing",
  "progress": 50,
  "message": "开始转录...",
  "result_available": false
}
```

### 3. 获取完整结果

**Endpoint**: `GET /task_result/{task_id}`

```bash
curl -X GET "http://localhost:7878/task_result/your-task-id"
```

**响应**:
```json
{
  "task_id": "uuid-string",
  "result": {
    "title": "视频标题",
    "id": "视频ID",
    "duration": 123.45,
    "author": "作者",
    "text": "完整转录文本...",
    "srt": "SRT格式字幕...",
    "language": "en",
    "like_count": 1000,
    "view_count": 50000
  }
}
```

### 视频下载功能使用 🆕

视频下载API 使用同样分为三个步骤：

### 1. 启动下载任务

**Endpoint**: `POST /download_video`

```bash
curl -X POST "http://localhost:7878/download_video" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "quality": "720p",
  "format": "mp4"
}'
```

### 2. 查询下载状态

**Endpoint**: `GET /download_status/{task_id}`

```bash
curl -X GET "http://localhost:7878/download_status/your-task-id"
```

### 3. 获取下载结果

**Endpoint**: `GET /download_result/{task_id}`

```bash
curl -X GET "http://localhost:7878/download_result/your-task-id"
```

### 4. 下载文件（可选）

**Endpoint**: `GET /download_file/{task_id}`

```bash
curl -X GET "http://localhost:7878/download_file/your-task-id" -o "video.mp4"
```

### 关键帧提取功能使用 🆕

关键帧提取功能支持所有yt-dlp支持的视频网站（数百个网站），包括YouTube、Bilibili、Vimeo、Dailymotion等。

关键帧提取API 支持多种提取方法：

### 1. 启动关键帧提取任务

**Endpoint**: `POST /extract_keyframes`

```bash
curl -X POST "http://localhost:7878/extract_keyframes" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "method": "interval",
  "interval": 30,
  "width": 1280,
  "height": 720,
  "format": "jpg",
  "quality": 85
}'
```

### 2. 查询提取状态

**Endpoint**: `GET /keyframe_status/{task_id}`

```bash
curl -X GET "http://localhost:7878/keyframe_status/your-task-id"
```

### 3. 获取提取结果

**Endpoint**: `GET /keyframe_result/{task_id}`

```bash
curl -X GET "http://localhost:7878/keyframe_result/your-task-id"
```

### 4. 下载关键帧图片

**Endpoint**: `GET /keyframe_image/{task_id}/{frame_index}`

```bash
curl -X GET "http://localhost:7878/keyframe_image/your-task-id/0" -o "frame_0.jpg"
```

### 5. 下载缩略图网格

**Endpoint**: `GET /keyframe_thumbnail/{task_id}`

```bash
curl -X GET "http://localhost:7878/keyframe_thumbnail/your-task-id" -o "thumbnail.jpg"
```

## 🔧 进度状态说明

| 进度范围 | 状态描述 |
|---------|---------|
| 0-10% | 获取视频元数据 |
| 10-30% | 下载音频文件 |
| 30-50% | 准备转录 |
| 50-80% | 执行语音识别 |
| 80-95% | 处理转录结果 |
| 95-100% | 保存文件和完成 |

## 🔗 n8n 集成

详细的 n8n 集成指南请参考：[N8N_USAGE_GUIDE.md](./N8N_USAGE_GUIDE.md)

## 🛠️ 开发工具

项目提供了多个实用工具：

```bash
# 监控服务状态
./monitor.sh

# 重启服务
./restart-service.sh

# 性能测试
./performance_test.sh

# 进度演示
./demo_progress.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# 视频下载演示
./demo_download.sh "https://www.youtube.com/watch?v=VIDEO_ID" 720p mp4

# 关键帧提取演示 🆕
./demo_keyframes.sh "https://www.youtube.com/watch?v=VIDEO_ID" interval 30
```

## 📁 文件输出

### 转录文件输出

转录完成后，文件会保存在以下位置：

```
./output/
├── VIDEO_ID.mp3    # 音频文件
├── VIDEO_ID.srt    # SRT字幕文件
└── VIDEO_ID.txt    # 纯文本文件
```

### 视频下载文件输出

视频下载完成后，文件会保存在以下位置：

```
./downloads/
├── VIDEO_ID_720p.mp4     # 720p MP4视频文件
├── VIDEO_ID_1080p.webm   # 1080p WebM视频文件
└── VIDEO_ID_best.mkv     # 最佳质量MKV视频文件
```

### 关键帧文件输出 🆕

关键帧提取完成后，文件会保存在以下位置：

```
./keyframes/
├── task_id_1/
│   ├── frame_000000.jpg    # 第0秒的关键帧
│   ├── frame_000030.jpg    # 第30秒的关键帧
│   ├── frame_000060.jpg    # 第60秒的关键帧
│   └── thumbnail_grid.jpg  # 缩略图网格
└── task_id_2/
    ├── frame_000015.jpg
    ├── frame_000045.jpg
    └── thumbnail_grid.jpg
```

## ⚙️ 配置说明

### 环境变量

- `PYTHONUNBUFFERED=1`: 禁用Python输出缓冲
- 内存限制: 4GB（可在docker-compose.yml中调整）

### 模型配置

默认使用 `tiny` 模型以节省资源，可在 `api.py` 中修改：

```python
MODEL_SIZE = "tiny"  # 可选: tiny, base, small, medium, large
```

## 🚨 注意事项

1. **首次状态查询**：可能需要5-15秒响应时间（正常现象）
2. **视频时长限制**：最大支持2小时视频
3. **内存使用**：长视频会消耗更多内存
4. **网络要求**：需要稳定的网络连接下载视频
5. **Docker健康检查**：使用Python requests进行健康检查，确保服务正常运行
6. **模型加载**：首次启动时Whisper模型加载可能需要1-2分钟，请耐心等待

## 📊 性能指标

- **短视频（<5分钟）**：通常1-2分钟完成
- **中等视频（5-30分钟）**：通常3-8分钟完成  
- **长视频（30分钟-2小时）**：通常10-30分钟完成
- **状态查询响应**：10-30ms（除首次查询外）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

## 🔍 服务状态检查

### 快速检查服务是否正常运行

```bash
# 检查容器状态
docker ps | grep subtitle-service

# 检查健康状态
curl -X GET "http://localhost:7878/health"

# 检查服务根路径
curl -X GET "http://localhost:7878/"

# 运行完整监控
./monitor.sh
```

### 常见问题排查

1. **服务无法启动**：检查Docker是否运行，端口7878是否被占用
2. **健康检查失败**：等待模型加载完成（首次启动需要1-2分钟）
3. **转录失败**：检查网络连接和视频URL是否有效
4. **内存不足**：检查Docker内存限制，建议至少4GB

### 服务重启

```bash
# 重启服务
./restart-service.sh

# 或者手动重启
docker-compose down
docker-compose up -d --build
```
