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

### 2. 克隆项目

```bash
# 克隆项目
git clone https://github.com/ncandyaoe/download-video-subtitle.git
cd download-video-subtitle
```

### 3. 安装依赖

```bash
# 安装所有需要的 Python 库
pip install -r requirements.txt
```

#### 系统依赖

本项目需要 `ffmpeg` 来处理音频和视频：

- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg`
- **Windows**: 下载 `ffmpeg` 后，将其 `bin` 目录添加到系统环境变量 `Path` 中
- **CentOS/RHEL**: `sudo yum install ffmpeg` 或 `sudo dnf install ffmpeg`

### 4. 启动服务

```bash
# 启动 API 服务
python run.py
```

服务启动后，你会在终端看到类似下面的信息：

```
INFO:     Uvicorn running on http://0.0.0.0:7878 (Press CTRL+C to quit)
INFO:     启动视频处理API服务
```

### 5. 验证服务

```bash
# 检查服务状态
curl http://localhost:7878/health

# 查看API文档
open http://localhost:7878/docs
```

## 🐳 Docker 部署（推荐）

### 快速启动

```bash
# 克隆项目
git clone https://github.com/ncandyaoe/download-video-subtitle.git
cd download-video-subtitle

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

## 📚 API 使用说明

本服务提供完整的视频处理功能，包括转录、下载、关键帧提取和视频合成。所有功能都采用异步处理架构。

> 📖 **完整API文档**: 查看 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) 获取详细的接口说明

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

### 视频下载功能

**启动下载任务**:
```bash
curl -X POST "http://localhost:7878/download_video" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "quality": "720p",
  "format": "mp4"
}'
```

**查询状态和获取结果**:
```bash
# 查询下载状态
curl -X GET "http://localhost:7878/download_status/{task_id}"

# 获取下载结果
curl -X GET "http://localhost:7878/download_result/{task_id}"

# 下载文件
curl -X GET "http://localhost:7878/download_file/{task_id}" -o "video.mp4"
```

### 关键帧提取功能

支持多种提取方法（间隔、数量、场景变化等）：

**启动提取任务**:
```bash
curl -X POST "http://localhost:7878/extract_keyframes" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "method": "interval",
  "interval": 30,
  "width": 1280,
  "height": 720
}'
```

**获取结果**:
```bash
# 查询状态
curl -X GET "http://localhost:7878/keyframe_status/{task_id}"

# 获取结果
curl -X GET "http://localhost:7878/keyframe_result/{task_id}"

# 下载单个关键帧
curl -X GET "http://localhost:7878/keyframe_image/{task_id}/0" -o "frame_0.jpg"

# 下载缩略图网格
curl -X GET "http://localhost:7878/keyframe_thumbnail/{task_id}" -o "thumbnail.jpg"
```

### 视频合成功能

支持多种合成模式：

**启动合成任务**:
```bash
curl -X POST "http://localhost:7878/compose_videos" \
-H "Content-Type: application/json" \
-d '{
  "video_urls": [
    "https://www.youtube.com/watch?v=VIDEO_ID1",
    "https://www.youtube.com/watch?v=VIDEO_ID2"
  ],
  "composition_type": "side_by_side",
  "output_quality": "720p"
}'
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

## �  相关文档

- **[API 接口文档](./API_DOCUMENTATION.md)** - 完整的API接口说明
- **[N8N 集成指南](./N8N_USAGE_GUIDE.md)** - n8n工作流集成
- **[测试指南](./TESTING_GUIDE.md)** - 测试用例和使用方法
- **[支持的网站](./SUPPORTED_SITES.md)** - 支持的视频平台列表
- **[资源监控](./RESOURCE_MONITORING_IMPLEMENTATION.md)** - 系统监控说明
- **[错误处理](./ERROR_HANDLING_IMPLEMENTATION.md)** - 错误处理机制

## 🛠️ 开发工具

项目提供了多个实用工具和脚本：

### 服务管理
```bash
# 监控服务状态
./monitor.sh

# 重启服务
./restart-service.sh

# 性能测试
./performance_test.sh
```

### 功能演示
```bash
# 转录演示
./demo_progress.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# 视频下载演示
./demo_download.sh "https://www.youtube.com/watch?v=VIDEO_ID" 720p mp4

# 关键帧提取演示
./demo_keyframes.sh "https://www.youtube.com/watch?v=VIDEO_ID" interval 30

# 视频合成演示
./demo_composition.sh
```

### 测试工具
```bash
# 运行所有测试
cd test_files && ./run_tests.sh

# 性能基准测试
python performance_benchmark.py

# 检查支持的网站
python check_site_support.py
```

## 📁 文件输出结构

### 转录文件
```
./output/
├── VIDEO_ID.mp3    # 提取的音频文件
├── VIDEO_ID.srt    # SRT格式字幕文件
└── VIDEO_ID.txt    # 纯文本转录文件
```

### 视频下载文件
```
./downloads/
├── VIDEO_ID_720p.mp4     # 720p MP4视频
├── VIDEO_ID_1080p.webm   # 1080p WebM视频
└── VIDEO_ID_best.mkv     # 最佳质量视频
```

### 关键帧文件
```
./keyframes/
├── {task_id}/
│   ├── frame_000000.jpg    # 关键帧图片
│   ├── frame_000030.jpg
│   ├── frame_000060.jpg
│   └── thumbnail_grid.jpg  # 缩略图网格
└── metadata.json           # 提取信息
```

### 视频合成文件
```
./compositions/
├── {task_id}/
│   ├── composition.mp4     # 合成后的视频
│   ├── temp/              # 临时文件
│   └── metadata.json      # 合成信息
```

## ⚙️ 配置说明

### 环境变量
```bash
PYTHONUNBUFFERED=1          # 禁用Python输出缓冲
OMP_NUM_THREADS=4           # OpenMP线程数
MKL_NUM_THREADS=4           # MKL线程数
MALLOC_TRIM_THRESHOLD_=100000  # 内存管理优化
```

### Docker 资源配置
- **内存限制**: 16GB（支持长视频处理）
- **CPU限制**: 8核心
- **保留资源**: 6GB内存，3核心CPU

### 模型配置
```python
# 在 api.py 中可配置
MODEL_SIZE = "tiny"  # 可选: tiny, base, small, medium, large
DEVICE = "auto"      # 可选: auto, cpu, cuda
```

### 硬件加速配置
- **GPU加速**: 自动检测CUDA/OpenCL
- **硬件编码**: 支持NVENC、VideoToolbox、QSV等
- **内存优化**: 智能缓存管理和垃圾回收

## 🚨 注意事项

### 性能相关
1. **首次启动**：模型加载可能需要1-2分钟，请耐心等待
2. **首次状态查询**：可能需要5-15秒响应时间（正常现象）
3. **内存使用**：长视频和高质量处理会消耗更多内存
4. **硬件加速**：首次使用GPU时需要初始化，可能较慢

### 限制说明
1. **视频时长**：建议单个视频不超过2小时
2. **并发任务**：建议同时处理任务数不超过3个
3. **网络要求**：需要稳定的网络连接下载视频
4. **存储空间**：确保有足够的磁盘空间存储输出文件

### Docker 相关
1. **健康检查**：使用curl进行健康检查，确保服务正常运行
2. **资源监控**：Docker配置了资源限制，避免系统过载
3. **自动重启**：服务异常时会自动重启

## 📊 性能指标

### 转录性能
- **短视频（<5分钟）**：通常1-2分钟完成
- **中等视频（5-30分钟）**：通常3-8分钟完成  
- **长视频（30分钟-2小时）**：通常10-30分钟完成
- **状态查询响应**：10-30ms（除首次查询外）

### 下载性能
- **720p视频**：通常比实时播放快2-5倍
- **1080p视频**：通常比实时播放快1-3倍
- **4K视频**：取决于网络带宽和源服务器

### 关键帧提取
- **间隔提取**：每秒处理约10-20帧
- **场景检测**：每秒处理约5-10帧
- **缩略图生成**：通常1-3秒完成

### 视频合成
- **简单拼接**：通常比视频总时长快5-10倍
- **复杂合成**：通常比视频总时长快2-5倍

## 🚀 项目特色

### 🎯 设计理念
- **异步优先**：所有耗时操作都采用异步处理，避免阻塞
- **资源智能**：智能检测和使用硬件加速，优化性能
- **用户友好**：提供详细的进度反馈和错误信息
- **扩展性强**：模块化设计，易于添加新功能

### 🔧 技术栈
- **后端框架**：FastAPI + Uvicorn
- **音频处理**：faster-whisper + yt-dlp
- **视频处理**：FFmpeg + OpenCV
- **异步处理**：asyncio + threading
- **容器化**：Docker + Docker Compose
- **监控**：psutil + loguru

### 🌟 核心优势
1. **高性能**：硬件加速 + 智能缓存
2. **高可用**：自动重启 + 健康检查
3. **易集成**：标准REST API + 详细文档
4. **多功能**：转录 + 下载 + 提取 + 合成

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发环境设置
```bash
# 克隆项目
git clone https://github.com/ncandyaoe/download-video-subtitle.git
cd download-video-subtitle

# 安装开发依赖
pip install -r requirements_test.txt

# 运行测试
cd test_files && ./run_tests.sh
```

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

## 🙏 致谢

感谢以下开源项目：
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 语音识别
- [FastAPI](https://github.com/tiangolo/fastapi) - Web框架
- [FFmpeg](https://ffmpeg.org/) - 音视频处理

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
4. **内存不足**：检查Docker内存限制，建议至少16GB
5. **下载失败**：检查视频是否可访问，某些地区可能需要代理
6. **GPU不可用**：检查CUDA驱动和Docker GPU支持

### 服务重启

```bash
# 重启服务
./restart-service.sh

# 或者手动重启
docker-compose down
docker-compose up -d --build
```
