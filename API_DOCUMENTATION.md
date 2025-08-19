# 视频处理 API 接口文档 v3.1

## 🚀 服务概述

视频处理API服务提供全面的视频处理功能，包括视频转录、下载、关键帧提取、视频合成等。支持从各种视频平台处理视频内容，并提供高性能的异步处理能力。

### 🎯 主要功能
- **视频转录**: 提取音频并生成文字转录和SRT字幕
- **视频下载**: 支持多种质量和格式的视频下载
- **关键帧提取**: 智能提取视频关键帧
- **视频合成**: 支持多种合成模式（拼接、画中画、并排显示等）
- **性能优化**: 硬件加速、缓存管理、内存优化
- **系统监控**: 实时资源监控和任务管理

### 🚀 v3.1 新特性
- **内存优化启动**: 延迟加载模型和硬件检测，启动时内存使用减少90%
- **智能资源管理**: 自动内存清理和资源监控
- **硬件加速**: 支持macOS VideoToolbox、NVIDIA NVENC等硬件编码器
- **本地文件支持**: 直接处理本地视频文件，无需上传

**服务地址**: `http://localhost:8000` (默认) 或 `http://localhost:7878`  
**Docker地址**: `http://host.docker.internal:8000`

## 📋 接口列表

### 1. 健康检查

**接口**: `GET /`  
**描述**: 检查服务是否正常运行

#### 请求示例
```bash
curl -X GET "http://localhost:7878/"
```

#### 响应示例
```json
{
  "message": "视频转录 API 正在运行。请使用 POST /generate_text_from_video 进行转录。"
}
```

---

### 2. 详细健康检查

**接口**: `GET /health`  
**描述**: 获取服务详细状态信息

#### 请求示例
```bash
curl -X GET "http://localhost:7878/health"
```

#### 响应示例
```json
{
  "status": "healthy",
  "timestamp": "2025-01-24T22:59:00Z",
  "active_tasks": 2
}
```

#### 响应字段说明
- `status`: 服务状态 (`healthy` | `unhealthy`)
- `timestamp`: 响应时间戳
- `active_tasks`: 当前活跃任务数量

---

### 3. 启动转录任务

**接口**: `POST /generate_text_from_video`  
**描述**: 启动异步视频转录任务

#### 请求参数
```json
{
  "video_url": "string"  // 必填，视频URL
}
```

#### 请求示例
```bash
curl -X POST "http://localhost:7878/generate_text_from_video" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk"
}'
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278b",
  "status": "started",
  "message": "转录任务已启动，请使用task_id查询进度"
}
```

#### 响应字段说明
- `task_id`: 任务唯一标识符，用于后续查询
- `status`: 任务状态，固定为 `started`
- `message`: 状态描述信息

#### 错误响应
```json
{
  "detail": "必须提供 video_url 字段。"
}
```

---

### 4. 查询任务状态

**接口**: `GET /task_status/{task_id}`  
**描述**: 查询任务执行状态和进度（轻量级，响应快）

#### 请求示例
```bash
curl -X GET "http://localhost:7878/task_status/483cfade-0732-4252-b897-428ab987278b"
```

#### 响应示例（处理中）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278b",
  "status": "processing",
  "progress": 50,
  "message": "开始转录..."
}
```

#### 响应示例（已完成）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278b",
  "status": "completed",
  "progress": 100,
  "message": "转录完成",
  "result_available": true,
  "result_summary": {
    "title": "How to get your first customers (even with ZERO audience)",
    "duration": 2986.52,
    "language": "en"
  }
}
```

#### 响应示例（失败）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278b",
  "status": "failed",
  "progress": 30,
  "message": "转录失败: 视频下载失败",
  "error": "详细错误信息"
}
```

#### 状态类型说明
- `processing`: 任务进行中
- `completed`: 任务完成
- `failed`: 任务失败

#### 进度范围说明
| 进度范围 | 状态描述 |
|---------|---------|
| 0-10% | 获取视频元数据 |
| 10-30% | 下载音频文件 |
| 30-50% | 准备转录 |
| 50-80% | 执行语音识别 |
| 80-95% | 处理转录结果 |
| 95-100% | 保存文件和完成 |

#### 错误响应
```json
{
  "detail": "任务不存在"
}
```

---

### 5. 获取完整结果

**接口**: `GET /task_result/{task_id}`  
**描述**: 获取任务的完整转录结果

#### 请求示例
```bash
curl -X GET "http://localhost:7878/task_result/483cfade-0732-4252-b897-428ab987278b"
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278b",
  "result": {
    "title": "How to get your first customers (even with ZERO audience)",
    "id": "HzUMAl9PgBk",
    "duration": 2986.52,
    "author": "Greg Isenberg",
    "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk",
    "description": "视频描述内容...",
    "thumbnail": "https://i.ytimg.com/vi/HzUMAl9PgBk/maxresdefault.jpg",
    "text": "完整的转录文本内容...",
    "srt": "1\n00:00:00,000 --> 00:00:05,000\n第一段字幕内容\n\n2\n00:00:05,000 --> 00:00:10,000\n第二段字幕内容\n\n...",
    "language": "en",
    "like_count": 15420,
    "view_count": 234567,
    "comment_count": 890,
    "tags": ["startup", "customers", "business"],
    "timestamp": 1640995200
  }
}
```

#### 结果字段说明
- `title`: 视频标题
- `id`: 视频ID
- `duration`: 视频时长（秒）
- `author`: 视频作者
- `video_url`: 原始视频URL
- `description`: 视频描述
- `thumbnail`: 视频缩略图URL
- `text`: 纯文本转录内容
- `srt`: SRT格式字幕内容
- `language`: 检测到的语言代码
- `like_count`: 点赞数
- `view_count`: 观看数
- `comment_count`: 评论数
- `tags`: 视频标签数组
- `timestamp`: 视频上传时间戳

#### 错误响应
```json
{
  "detail": "任务不存在或已过期"
}
```

```json
{
  "detail": "任务尚未完成，当前状态: processing"
}
```

## 🔄 完整使用流程

### 1. 基本流程
```bash
# 1. 启动转录任务
RESPONSE=$(curl -s -X POST "http://localhost:7878/generate_text_from_video" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}')

# 2. 提取任务ID
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

# 3. 轮询任务状态
while true; do
  STATUS=$(curl -s -X GET "http://localhost:7878/task_status/$TASK_ID")
  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  
  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "任务完成！"
    break
  elif [ "$CURRENT_STATUS" = "failed" ]; then
    echo "任务失败！"
    break
  fi
  
  echo "进度: $(echo $STATUS | jq -r '.progress')%"
  sleep 5
done

# 4. 获取完整结果
curl -s -X GET "http://localhost:7878/task_result/$TASK_ID" | jq '.result'
```

### 2. JavaScript示例
```javascript
// 启动转录任务
const startResponse = await fetch('http://localhost:7878/generate_text_from_video', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ video_url: 'https://www.youtube.com/watch?v=VIDEO_ID' })
});
const { task_id } = await startResponse.json();

// 轮询状态
const pollStatus = async () => {
  const response = await fetch(`http://localhost:7878/task_status/${task_id}`);
  const status = await response.json();
  
  if (status.status === 'completed') {
    // 获取完整结果
    const resultResponse = await fetch(`http://localhost:7878/task_result/${task_id}`);
    const result = await resultResponse.json();
    console.log('转录完成:', result.result);
    return;
  }
  
  if (status.status === 'failed') {
    console.error('转录失败:', status.error);
    return;
  }
  
  console.log(`进度: ${status.progress}% - ${status.message}`);
  setTimeout(pollStatus, 5000); // 5秒后再次查询
};

pollStatus();
```

## ⚡ 性能指标

### 响应时间
- **任务启动**: < 100ms
- **状态查询**: 20-35ms
- **结果获取**: 50-200ms（取决于结果大小）

### 处理时间（预估）
- **短视频（<5分钟）**: 1-3分钟
- **中等视频（5-30分钟）**: 3-10分钟
- **长视频（30分钟-2小时）**: 10-40分钟

### 内存优化 (v3.1)
- **启动内存使用**: < 1GB（相比之前减少90%）
- **延迟加载**: Whisper模型和硬件检测仅在需要时加载
- **自动清理**: 内存使用超过80%时自动触发清理
- **智能缓存**: 基于使用频率的智能缓存管理

### 硬件加速支持
- **macOS**: VideoToolbox (h264_videotoolbox, hevc_videotoolbox)
- **NVIDIA**: NVENC (h264_nvenc, hevc_nvenc)
- **Intel**: QuickSync (h264_qsv, hevc_qsv)
- **AMD**: AMF (h264_amf, hevc_amf)

### 系统限制
- **最大视频时长**: 2小时
- **并发任务数**: 建议不超过5个
- **内存限制**: 动态调整，最大80%系统内存
- **本地文件大小**: 单文件最大2GB

## 🚨 错误处理

### HTTP状态码
- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 任务不存在
- `413`: 视频时长超过限制
- `500`: 服务器内部错误
- `503`: 服务不可用（内存不足或任务过多）

### 常见错误
1. **视频URL无效**: 检查URL格式和可访问性
2. **视频时长超限**: 当前限制为2小时
3. **任务不存在**: 任务可能已过期或ID错误
4. **服务不可用**: 检查服务是否正常运行
5. **内存不足**: 系统内存使用过高，自动拒绝新任务
6. **本地文件不存在**: 检查文件路径和权限

### 内存相关错误 (v3.1)
| 错误码 | 错误信息 | 解决方案 |
|--------|----------|----------|
| 503 | "内存使用率过高" | 等待自动清理或手动清理内存 |
| 503 | "任务队列已满" | 等待现有任务完成 |
| 500 | "模型加载失败" | 检查系统内存是否充足 |
| 400 | "文件权限不足" | 检查本地文件读取权限 |

## 🔧 最佳实践

1. **轮询间隔**: 建议5-10秒查询一次状态
2. **超时处理**: 设置合理的最大等待时间
3. **错误重试**: 网络错误可重试，业务错误不建议重试
4. **结果缓存**: 获取结果后及时保存，任务状态会被清理
5. **内存监控**: 定期检查 `/system/resources` 监控系统状态
6. **硬件加速**: 优先使用硬件编码器提升性能
7. **本地文件**: 使用本地文件可显著提升处理速度

## 🩺 快速诊断工具

### 系统健康检查
```bash
# 检查服务状态
curl -X GET "http://localhost:8000/health"

# 检查系统资源
curl -X GET "http://localhost:8000/system/resources"

# 检查硬件加速
curl -X GET "http://localhost:8000/system/hardware"
```

### 性能测试
```bash
# 测试基础连接
python test_basic_connection.py

# 测试内存使用
python test_memory_usage.py

# 性能基准测试
python performance_benchmark.py
```

### 故障排除步骤
1. **服务无法启动**
   - 检查端口是否被占用: `lsof -i:8000`
   - 查看启动日志中的错误信息
   - 确认依赖包是否正确安装

2. **内存使用过高**
   - 执行手动清理: `curl -X POST "http://localhost:8000/system/cleanup"`
   - 检查活跃任务数: `curl -X GET "http://localhost:8000/system/tasks"`
   - 重启服务释放所有资源

3. **处理速度慢**
   - 检查硬件加速状态: `curl -X GET "http://localhost:8000/system/hardware"`
   - 使用本地文件而非在线URL
   - 减少并发任务数量

4. **任务失败**
   - 检查视频URL是否可访问
   - 确认本地文件路径和权限
   - 查看详细错误信息

## 📁 文件输出

转录完成后，文件会自动保存在服务器的 `output` 目录：

```
./output/
├── VIDEO_ID.mp3    # 提取的音频文件
├── VIDEO_ID.srt    # SRT字幕文件
└── VIDEO_ID.txt    # 纯文本转录文件
```

通过Docker volume映射，这些文件也会出现在主机的 `./output` 目录中。

---

## 🎬 视频下载功能 (v2.1新增)

### 6. 启动视频下载任务

**接口**: `POST /download_video`  
**描述**: 启动异步视频下载任务

#### 请求参数
```json
{
  "video_url": "string",  // 必填，视频URL
  "quality": "string",    // 可选，视频质量 (默认: "best")
  "format": "string"      // 可选，视频格式 (默认: "mp4")
}
```

#### 质量选项
- `best`: 最佳质量
- `worst`: 最低质量  
- `1080p`: 1080p高清
- `720p`: 720p高清
- `480p`: 480p标清

#### 格式选项
- `mp4`: MP4格式 (推荐)
- `webm`: WebM格式
- `mkv`: MKV格式

#### 请求示例
```bash
curl -X POST "http://localhost:7878/download_video" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk",
  "quality": "720p",
  "format": "mp4"
}'
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278c",
  "status": "started",
  "message": "视频下载任务已启动，请使用task_id查询进度",
  "quality": "720p",
  "format": "mp4"
}
```

---

### 7. 查询下载任务状态

**接口**: `GET /download_status/{task_id}`  
**描述**: 查询下载任务执行状态和进度

#### 请求示例
```bash
curl -X GET "http://localhost:7878/download_status/483cfade-0732-4252-b897-428ab987278c"
```

#### 响应示例（下载中）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278c",
  "status": "downloading",
  "progress": 65,
  "message": "下载中... 150.5MB / 230.2MB",
  "file_size": 241467392,
  "downloaded_size": 157810688
}
```

#### 响应示例（已完成）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278c",
  "status": "completed",
  "progress": 100,
  "message": "下载完成",
  "file_size": 241467392,
  "downloaded_size": 241467392,
  "result_available": true,
  "result_summary": {
    "title": "How to get your first customers",
    "duration": 2986.52,
    "file_size": 241467392,
    "quality": "720p",
    "format": "mp4"
  }
}
```

#### 下载进度说明
| 进度范围 | 状态描述 |
|---------|---------|
| 0-10% | 获取视频信息 |
| 10-20% | 准备下载 |
| 20-90% | 下载视频文件 |
| 90-100% | 后处理和完成 |

---

### 8. 获取下载完整结果

**接口**: `GET /download_result/{task_id}`  
**描述**: 获取下载任务的完整结果信息

#### 请求示例
```bash
curl -X GET "http://localhost:7878/download_result/483cfade-0732-4252-b897-428ab987278c"
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278c",
  "result": {
    "title": "How to get your first customers (even with ZERO audience)",
    "id": "HzUMAl9PgBk",
    "duration": 2986.52,
    "author": "Greg Isenberg",
    "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk",
    "description": "视频描述内容...",
    "thumbnail": "https://i.ytimg.com/vi/HzUMAl9PgBk/maxresdefault.jpg",
    "file_path": "./downloads/HzUMAl9PgBk_720p.mp4",
    "file_size": 241467392,
    "quality": "720p",
    "format": "mp4",
    "like_count": 15420,
    "view_count": 234567,
    "comment_count": 890,
    "tags": ["startup", "customers", "business"],
    "timestamp": 1640995200
  }
}
```

---

### 9. 下载视频文件

**接口**: `GET /download_file/{task_id}`  
**描述**: 直接下载视频文件到客户端

#### 请求示例
```bash
curl -X GET "http://localhost:7878/download_file/483cfade-0732-4252-b897-428ab987278c" \
-o "downloaded_video.mp4"
```

#### 响应
返回视频文件的二进制数据流，浏览器会自动下载文件。

---

## 🔄 视频下载完整使用流程

### 基本流程
```bash
# 1. 启动下载任务
RESPONSE=$(curl -s -X POST "http://localhost:7878/download_video" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID", "quality": "720p", "format": "mp4"}')

# 2. 提取任务ID
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

# 3. 轮询下载状态
while true; do
  STATUS=$(curl -s -X GET "http://localhost:7878/download_status/$TASK_ID")
  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  
  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "下载完成！"
    break
  elif [ "$CURRENT_STATUS" = "failed" ]; then
    echo "下载失败！"
    break
  fi
  
  PROGRESS=$(echo $STATUS | jq -r '.progress')
  MESSAGE=$(echo $STATUS | jq -r '.message')
  echo "进度: $PROGRESS% - $MESSAGE"
  sleep 5
done

# 4. 获取完整结果
curl -s -X GET "http://localhost:7878/download_result/$TASK_ID" | jq '.result'

# 5. 下载文件到本地（可选）
curl -X GET "http://localhost:7878/download_file/$TASK_ID" -o "video.mp4"
```

## 📁 下载文件输出

下载完成后，文件会保存在服务器的 `downloads` 目录：

```
./downloads/
├── VIDEO_ID_720p.mp4     # 720p MP4视频文件
├── VIDEO_ID_1080p.webm   # 1080p WebM视频文件
└── VIDEO_ID_best.mkv     # 最佳质量MKV视频文件
```

通过Docker volume映射，这些文件也会出现在主机的 `./downloads` 目录中。

---

## 🎬 关键帧提取功能 (v2.2新增)

关键帧提取功能支持所有yt-dlp支持的视频网站，包括但不限于：
- YouTube (youtube.com, youtu.be)
- Bilibili (bilibili.com)  
- Vimeo (vimeo.com)
- Dailymotion (dailymotion.com)
- Twitch (twitch.tv)
- Facebook (facebook.com)
- 以及其他数百个视频网站

完整支持列表请参考：[yt-dlp支持的网站](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### 10. 启动关键帧提取任务

**接口**: `POST /extract_keyframes`  
**描述**: 启动异步关键帧提取任务

#### 请求参数
```json
{
  "video_url": "string",     // 必填，视频URL
  "method": "string",        // 可选，提取方法 (默认: "interval")
  "interval": 30,            // 可选，时间间隔秒数 (method=interval时)
  "timestamps": [10, 30, 60], // 可选，指定时间点数组 (method=timestamps时)
  "count": 10,               // 可选，提取帧数 (method=count时)
  "width": 1280,             // 可选，输出图片宽度 (默认: 1280)
  "height": 720,             // 可选，输出图片高度 (默认: 720)
  "format": "jpg",           // 可选，图片格式 (默认: "jpg")
  "quality": 85              // 可选，JPEG质量1-100 (默认: 85)
}
```

#### 提取方法
- `interval`: 按时间间隔提取（每N秒一帧）
- `timestamps`: 在指定时间点提取
- `count`: 平均分布提取指定数量的帧
- `keyframes`: 自动检测真正的关键帧

#### 请求示例
```bash
curl -X POST "http://localhost:7878/extract_keyframes" \
-H "Content-Type: application/json" \
-d '{
  "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk",
  "method": "interval",
  "interval": 30,
  "width": 1280,
  "height": 720,
  "format": "jpg",
  "quality": 85
}'
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278d",
  "status": "started",
  "message": "关键帧提取任务已启动，请使用task_id查询进度",
  "method": "interval",
  "parameters": {
    "interval": 30,
    "width": 1280,
    "height": 720,
    "format": "jpg",
    "quality": 85
  }
}
```

---

### 11. 查询关键帧提取状态

**接口**: `GET /keyframe_status/{task_id}`  
**描述**: 查询关键帧提取任务状态和进度

#### 请求示例
```bash
curl -X GET "http://localhost:7878/keyframe_status/483cfade-0732-4252-b897-428ab987278d"
```

#### 响应示例（提取中）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278d",
  "status": "extracting",
  "progress": 65,
  "message": "已提取 8/12 帧",
  "total_frames": 12,
  "extracted_frames": 8
}
```

#### 响应示例（已完成）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278d",
  "status": "completed",
  "progress": 100,
  "message": "关键帧提取完成，共提取 12 帧",
  "total_frames": 12,
  "extracted_frames": 12,
  "result_available": true,
  "result_summary": {
    "title": "How to get your first customers",
    "total_frames": 12,
    "method": "interval",
    "duration": 2986.52
  }
}
```

#### 提取进度说明
| 进度范围 | 状态描述 |
|---------|---------|
| 0-10% | 获取视频信息 |
| 10-20% | 准备视频文件 |
| 20-30% | 计算提取时间点 |
| 30-90% | 提取关键帧 |
| 90-95% | 生成缩略图 |
| 95-100% | 完成处理 |

---

### 12. 获取关键帧提取结果

**接口**: `GET /keyframe_result/{task_id}`  
**描述**: 获取关键帧提取任务的完整结果

#### 请求示例
```bash
curl -X GET "http://localhost:7878/keyframe_result/483cfade-0732-4252-b897-428ab987278d"
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278d",
  "result": {
    "title": "How to get your first customers (even with ZERO audience)",
    "id": "HzUMAl9PgBk",
    "duration": 2986.52,
    "author": "Greg Isenberg",
    "video_url": "https://www.youtube.com/watch?v=HzUMAl9PgBk",
    "method": "interval",
    "total_frames": 12,
    "frames": [
      {
        "index": 0,
        "timestamp": 0.0,
        "filename": "frame_000000.jpg",
        "path": "./keyframes/task_id/frame_000000.jpg",
        "size": 156789,
        "width": 1280,
        "height": 720,
        "format": "jpg"
      },
      {
        "index": 1,
        "timestamp": 30.0,
        "filename": "frame_000030.jpg",
        "path": "./keyframes/task_id/frame_000030.jpg",
        "size": 142356,
        "width": 1280,
        "height": 720,
        "format": "jpg"
      }
    ],
    "thumbnail_path": "./keyframes/task_id/thumbnail_grid.jpg",
    "task_dir": "./keyframes/task_id",
    "extraction_params": {
      "method": "interval",
      "interval": 30,
      "width": 1280,
      "height": 720,
      "format": "jpg",
      "quality": 85
    }
  }
}
```

---

### 13. 下载关键帧图片

**接口**: `GET /keyframe_image/{task_id}/{frame_index}`  
**描述**: 下载指定索引的关键帧图片

#### 请求示例
```bash
curl -X GET "http://localhost:7878/keyframe_image/483cfade-0732-4252-b897-428ab987278d/0" \
-o "frame_0.jpg"
```

#### 响应
返回图片文件的二进制数据流，Content-Type为image/jpeg或image/png。

---

### 14. 下载缩略图网格

**接口**: `GET /keyframe_thumbnail/{task_id}`  
**描述**: 下载关键帧缩略图网格（多帧拼接图）

#### 请求示例
```bash
curl -X GET "http://localhost:7878/keyframe_thumbnail/483cfade-0732-4252-b897-428ab987278d" \
-o "thumbnail_grid.jpg"
```

#### 响应
返回拼接后的缩略图网格，Content-Type为image/jpeg。

---

## 🔄 关键帧提取完整使用流程

### 基本流程
```bash
# 1. 启动关键帧提取任务
RESPONSE=$(curl -s -X POST "http://localhost:7878/extract_keyframes" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID", "method": "interval", "interval": 30}')

# 2. 提取任务ID
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

# 3. 轮询提取状态
while true; do
  STATUS=$(curl -s -X GET "http://localhost:7878/keyframe_status/$TASK_ID")
  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  
  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "关键帧提取完成！"
    break
  elif [ "$CURRENT_STATUS" = "failed" ]; then
    echo "关键帧提取失败！"
    break
  fi
  
  PROGRESS=$(echo $STATUS | jq -r '.progress')
  FRAMES=$(echo $STATUS | jq -r '.extracted_frames')
  TOTAL=$(echo $STATUS | jq -r '.total_frames')
  echo "进度: $PROGRESS% - 已提取 $FRAMES/$TOTAL 帧"
  sleep 5
done

# 4. 获取完整结果
curl -s -X GET "http://localhost:7878/keyframe_result/$TASK_ID" | jq '.result'

# 5. 下载关键帧图片
curl -X GET "http://localhost:7878/keyframe_image/$TASK_ID/0" -o "frame_0.jpg"

# 6. 下载缩略图网格
curl -X GET "http://localhost:7878/keyframe_thumbnail/$TASK_ID" -o "thumbnail.jpg"
```

## 📁 关键帧文件输出

关键帧提取完成后，文件会保存在服务器的 `keyframes` 目录：

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

通过Docker volume映射，这些文件也会出现在主机的 `./keyframes` 目录中。

---

## 🎬 视频合成功能 (v3.0新增)

视频合成功能支持多种合成模式，可以将多个视频、音频、字幕等素材合成为一个完整的视频作品。

### 15. 启动视频合成任务

**接口**: `POST /compose_video`  
**描述**: 启动异步视频合成任务

#### 请求参数
```json
{
  "composition_type": "string",    // 必填，合成类型
  "videos": [                      // 必填，视频列表
    {
      "video_url": "string",       // 视频URL
      "start_time": 0,             // 可选，开始时间(秒)
      "end_time": 60,              // 可选，结束时间(秒)
      "position": {                // 可选，位置信息(画中画模式)
        "x": 10,
        "y": 10,
        "width": 320,
        "height": 240
      }
    }
  ],
  "audio_file": "string",          // 可选，背景音频URL
  "subtitle_file": "string",       // 可选，字幕文件路径
  "output_format": "mp4",          // 可选，输出格式
  "output_resolution": "1920x1080", // 可选，输出分辨率
  "frame_rate": 30,                // 可选，帧率
  "audio_settings": {              // 可选，音频设置
    "volume": 1.0,
    "fade_in": 2.0,
    "fade_out": 2.0
  },
  "subtitle_settings": {           // 可选，字幕设置
    "font_size": 24,
    "font_color": "white",
    "background_color": "black",
    "position": "bottom"
  }
}
```

#### 合成类型说明

##### 1. concat - 视频拼接
将多个视频按顺序拼接成一个视频，支持在线视频URL和本地视频文件

**在线视频拼接：**
```json
{
  "composition_type": "concat",
  "videos": [
    {"video_url": "https://example.com/video1.mp4"},
    {"video_url": "https://example.com/video2.mp4"},
    {"video_url": "https://example.com/video3.mp4"}
  ],
  "output_format": "mp4"
}
```

**本地视频拼接：**
```json
{
  "composition_type": "concat",
  "videos": [
    {"video_url": "/path/to/local/video1.mp4"},
    {"video_url": "file:///absolute/path/to/video2.mp4"},
    {"video_url": "./relative/path/video3.mp4"}
  ],
  "output_format": "mp4"
}
```

**混合视频拼接（本地+在线）：**
```json
{
  "composition_type": "concat",
  "videos": [
    {"video_url": "/path/to/local/video1.mp4"},
    {"video_url": "https://example.com/online_video.mp4"},
    {"video_url": "file:///path/to/local/video2.mp4"}
  ],
  "output_format": "mp4"
}
```

##### 2. picture_in_picture - 画中画
将一个或多个小视频叠加在主视频上
```json
{
  "composition_type": "picture_in_picture",
  "videos": [
    {
      "video_url": "https://example.com/main_video.mp4",
      "role": "main"
    },
    {
      "video_url": "https://example.com/overlay_video.mp4",
      "role": "overlay",
      "position": {
        "x": 50,
        "y": 50,
        "width": 320,
        "height": 240
      },
      "opacity": 0.8
    }
  ]
}
```

##### 3. side_by_side - 并排显示
将多个视频并排显示
```json
{
  "composition_type": "side_by_side",
  "videos": [
    {"video_url": "https://example.com/left_video.mp4"},
    {"video_url": "https://example.com/right_video.mp4"}
  ],
  "layout": "horizontal", // horizontal 或 vertical
  "output_resolution": "1920x1080"
}
```

##### 4. grid - 网格布局
将多个视频以网格形式排列
```json
{
  "composition_type": "grid",
  "videos": [
    {"video_url": "https://example.com/video1.mp4"},
    {"video_url": "https://example.com/video2.mp4"},
    {"video_url": "https://example.com/video3.mp4"},
    {"video_url": "https://example.com/video4.mp4"}
  ],
  "grid_size": "2x2",
  "output_resolution": "1920x1080"
}
```

##### 5. slideshow - 幻灯片
将关键帧图片制作成幻灯片视频
```json
{
  "composition_type": "slideshow",
  "images": [
    {"image_path": "./keyframes/task1/frame_001.jpg", "duration": 3},
    {"image_path": "./keyframes/task1/frame_002.jpg", "duration": 3},
    {"image_path": "./keyframes/task1/frame_003.jpg", "duration": 3}
  ],
  "transition": "fade",
  "audio_file": "https://example.com/background_music.mp3"
}
```

##### 6. audio_video_subtitle - 音频视频字幕合成
将视频、音频和字幕合成为一个完整视频

**支持的字幕格式**:
- `.srt` - SubRip字幕格式（推荐）
- `.txt` - 纯文本格式（**v3.1新增**，自动转换为SRT）
- `.ass` - Advanced SubStation Alpha
- `.ssa` - SubStation Alpha  
- `.vtt` - WebVTT字幕格式

```json
{
  "composition_type": "audio_video_subtitle",
  "videos": [
    {"video_url": "https://example.com/video.mp4"}
  ],
  "audio_file": "https://example.com/audio.mp3",
  "subtitle_file": "./output/video_subtitles.srt", // 支持 .srt, .txt, .ass, .ssa, .vtt
  "audio_settings": {
    "volume": 0.8,
    "start_offset": 2.0
  },
  "subtitle_settings": {
    "font_size": 24,
    "font_color": "white",
    "outline_color": "black"
  }
}
```

**TXT格式字幕示例**:
```txt
看，一群可爱的小猴子在月光下快乐地玩耍呢！
它们在树枝间跳跃，发出欢快的叫声。
突然，小猴子们发现了水中的月亮。
"哇！月亮掉到水里了！"一只小猴子惊呼道。
```

**自动转换**: TXT文件会自动转换为SRT格式，每行文本按标点符号分割，自动分配时间轴。

#### 请求示例
```bash
curl -X POST "http://localhost:7878/compose_video" \
-H "Content-Type: application/json" \
-d '{
  "composition_type": "concat",
  "videos": [
    {"video_url": "https://www.youtube.com/watch?v=video1"},
    {"video_url": "https://www.youtube.com/watch?v=video2"}
  ],
  "output_format": "mp4",
  "output_resolution": "1920x1080"
}'
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278e",
  "status": "started",
  "message": "视频合成任务已启动，请使用task_id查询进度",
  "composition_type": "concat",
  "estimated_duration": 300,
  "parameters": {
    "video_count": 2,
    "output_format": "mp4",
    "output_resolution": "1920x1080"
  }
}
```

---

### 16. 查询合成任务状态

**接口**: `GET /composition_status/{task_id}`  
**描述**: 查询视频合成任务状态和进度

#### 请求示例
```bash
curl -X GET "http://localhost:7878/composition_status/483cfade-0732-4252-b897-428ab987278e"
```

#### 响应示例（合成中）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278e",
  "status": "composing",
  "progress": 45,
  "message": "正在合成视频... 处理第2个视频",
  "current_step": "video_processing",
  "total_steps": 5,
  "current_step_progress": 80,
  "estimated_remaining_time": 180
}
```

#### 响应示例（已完成）
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278e",
  "status": "completed",
  "progress": 100,
  "message": "视频合成完成",
  "result_available": true,
  "result_summary": {
    "composition_type": "concat",
    "output_file_size": 524288000,
    "output_duration": 300.5,
    "output_resolution": "1920x1080",
    "processing_time": 120.5
  }
}
```

#### 合成进度说明
| 进度范围 | 状态描述 |
|---------|---------|
| 0-10% | 准备素材和验证 |
| 10-30% | 下载和预处理视频 |
| 30-60% | 视频格式标准化 |
| 60-85% | 执行合成操作 |
| 85-95% | 后处理和优化 |
| 95-100% | 保存输出文件 |

---

### 17. 获取合成结果

**接口**: `GET /composition_result/{task_id}`  
**描述**: 获取视频合成任务的完整结果

#### 请求示例
```bash
curl -X GET "http://localhost:7878/composition_result/483cfade-0732-4252-b897-428ab987278e"
```

#### 响应示例
```json
{
  "task_id": "483cfade-0732-4252-b897-428ab987278e",
  "result": {
    "composition_type": "concat",
    "output_file": "./compositions/task_id/output.mp4",
    "output_file_size": 524288000,
    "output_duration": 300.5,
    "output_resolution": "1920x1080",
    "output_frame_rate": 30,
    "processing_time": 120.5,
    "input_videos": [
      {
        "video_url": "https://www.youtube.com/watch?v=video1",
        "title": "Video 1 Title",
        "duration": 150.2,
        "resolution": "1920x1080"
      },
      {
        "video_url": "https://www.youtube.com/watch?v=video2", 
        "title": "Video 2 Title",
        "duration": 150.3,
        "resolution": "1920x1080"
      }
    ],
    "composition_settings": {
      "output_format": "mp4",
      "output_resolution": "1920x1080",
      "frame_rate": 30,
      "video_codec": "h264",
      "audio_codec": "aac"
    },
    "performance_stats": {
      "hardware_acceleration": true,
      "encoder_used": "h264_videotoolbox",
      "average_fps": 45.2,
      "peak_memory_usage": "2.1GB"
    }
  }
}
```

---

### 18. 下载合成视频

**接口**: `GET /composition_file/{task_id}`  
**描述**: 下载合成后的视频文件

#### 请求示例
```bash
curl -X GET "http://localhost:7878/composition_file/483cfade-0732-4252-b897-428ab987278e" \
-o "composed_video.mp4"
```

#### 响应
返回合成后的视频文件二进制数据流。

---

## 🔄 视频合成完整使用流程

### 基本流程示例
```bash
# 1. 启动合成任务
RESPONSE=$(curl -s -X POST "http://localhost:7878/compose_video" \
  -H "Content-Type: application/json" \
  -d '{
    "composition_type": "concat",
    "videos": [
      {"video_url": "https://www.youtube.com/watch?v=video1"},
      {"video_url": "https://www.youtube.com/watch?v=video2"}
    ],
    "output_format": "mp4"
  }')

# 2. 提取任务ID
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

# 3. 轮询合成状态
while true; do
  STATUS=$(curl -s -X GET "http://localhost:7878/composition_status/$TASK_ID")
  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  
  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "视频合成完成！"
    break
  elif [ "$CURRENT_STATUS" = "failed" ]; then
    echo "视频合成失败！"
    break
  fi
  
  PROGRESS=$(echo $STATUS | jq -r '.progress')
  MESSAGE=$(echo $STATUS | jq -r '.message')
  echo "进度: $PROGRESS% - $MESSAGE"
  sleep 10
done

# 4. 获取完整结果
curl -s -X GET "http://localhost:7878/composition_result/$TASK_ID" | jq '.result'

# 5. 下载合成视频
curl -X GET "http://localhost:7878/composition_file/$TASK_ID" -o "final_video.mp4"
```

### JavaScript示例
```javascript
// 启动视频合成任务
const composeVideo = async () => {
  const response = await fetch('http://localhost:7878/compose_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      composition_type: 'picture_in_picture',
      videos: [
        {
          video_url: 'https://example.com/main.mp4',
          role: 'main'
        },
        {
          video_url: 'https://example.com/overlay.mp4',
          role: 'overlay',
          position: { x: 50, y: 50, width: 320, height: 240 }
        }
      ]
    })
  });
  
  const { task_id } = await response.json();
  
  // 轮询状态
  const pollStatus = async () => {
    const statusResponse = await fetch(`http://localhost:7878/composition_status/${task_id}`);
    const status = await statusResponse.json();
    
    if (status.status === 'completed') {
      console.log('合成完成！');
      // 获取结果
      const resultResponse = await fetch(`http://localhost:7878/composition_result/${task_id}`);
      const result = await resultResponse.json();
      console.log('合成结果:', result.result);
      return;
    }
    
    if (status.status === 'failed') {
      console.error('合成失败:', status.error);
      return;
    }
    
    console.log(`进度: ${status.progress}% - ${status.message}`);
    setTimeout(pollStatus, 10000); // 10秒后再次查询
  };
  
  pollStatus();
};

composeVideo();
```

## 📁 本地视频文件支持 (v3.0新增)

API现在支持直接使用本地视频文件进行合成，无需上传或转换为在线URL。

### 支持的本地文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| MP4 | .mp4, .m4v | 推荐格式，兼容性最好 |
| AVI | .avi | 经典格式，广泛支持 |
| MOV | .mov | Apple格式，高质量 |
| MKV | .mkv | 开源格式，支持多轨道 |
| WebM | .webm | Web优化格式 |
| FLV | .flv | Flash视频格式 |
| WMV | .wmv | Windows媒体格式 |
| 3GP | .3gp | 移动设备格式 |

### 本地文件路径格式

#### 1. 绝对路径
```json
{
  "video_url": "/Users/username/Videos/my_video.mp4"
}
```

#### 2. 相对路径
```json
{
  "video_url": "./videos/my_video.mp4"
}
```

#### 3. file:// 协议
```json
{
  "video_url": "file:///Users/username/Videos/my_video.mp4"
}
```

### 本地视频使用示例

#### 基本本地视频拼接
```bash
curl -X POST "http://localhost:7878/compose_video" \
-H "Content-Type: application/json" \
-d '{
  "composition_type": "concat",
  "videos": [
    {"video_url": "/path/to/video1.mp4"},
    {"video_url": "/path/to/video2.mp4"}
  ],
  "output_format": "mp4"
}'
```

#### 混合本地和在线视频
```bash
curl -X POST "http://localhost:7878/compose_video" \
-H "Content-Type: application/json" \
-d '{
  "composition_type": "concat",
  "videos": [
    {"video_url": "/path/to/local_intro.mp4"},
    {"video_url": "https://example.com/online_content.mp4"},
    {"video_url": "file:///path/to/local_outro.mp4"}
  ],
  "output_format": "mp4"
}'
```

#### 本地视频画中画
```bash
curl -X POST "http://localhost:7878/compose_video" \
-H "Content-Type: application/json" \
-d '{
  "composition_type": "picture_in_picture",
  "videos": [
    {
      "video_url": "/path/to/main_video.mp4",
      "role": "main"
    },
    {
      "video_url": "./overlay_video.mp4",
      "role": "overlay",
      "position": {"x": 50, "y": 50, "width": 320, "height": 240}
    }
  ]
}'
```

### 本地文件限制

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 最大文件大小 | 2GB | 单个视频文件大小限制 |
| 最大时长 | 3小时 | 单个视频时长限制 |
| 文件权限 | 可读 | 服务需要有文件读取权限 |
| 路径长度 | 260字符 | 文件路径长度限制 |

### 性能优势

使用本地视频文件相比在线视频有以下优势：

- ✅ **更快的处理速度** - 无需下载时间
- ✅ **更稳定的处理** - 不受网络影响
- ✅ **更高的质量** - 避免在线压缩损失
- ✅ **更好的隐私** - 文件不离开本地环境
- ✅ **支持大文件** - 不受网络传输限制

### 错误处理

#### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 文件不存在 | 路径错误或文件被删除 | 检查文件路径和文件是否存在 |
| 权限不足 | 服务无法读取文件 | 检查文件权限，确保可读 |
| 格式不支持 | 文件格式不在支持列表中 | 转换为支持的格式 |
| 文件过大 | 超过2GB限制 | 压缩文件或分段处理 |
| 路径过长 | 文件路径超过限制 | 使用较短的路径或移动文件 |

## 📁 合成文件输出

视频合成完成后，文件会保存在服务器的 `compositions` 目录：

```
./compositions/
├── task_id_1/
│   ├── output.mp4          # 最终合成视频
│   ├── temp_video_1.mp4    # 临时处理文件
│   ├── temp_video_2.mp4    # 临时处理文件
│   └── composition.log     # 处理日志
└── task_id_2/
    ├── output.mp4
    └── composition.log
```

---

## ⚡ 系统监控和性能优化 (v3.1新增)

### 19. 系统资源状态

**接口**: `GET /system/resources`  
**描述**: 获取系统资源使用状态和性能指标

#### 请求示例
```bash
curl -X GET "http://localhost:8000/system/resources"
```

#### 响应示例
```json
{
  "cpu_percent": 45.2,
  "memory_percent": 68.5,
  "disk_percent": 23.1,
  "active_tasks": 3,
  "max_concurrent_tasks": 5,
  "can_accept_tasks": true,
  "free_disk_gb": 125.6,
  "total_memory_gb": 16.0,
  "available_memory_gb": 5.0,
  "system_load": [1.2, 1.5, 1.8],
  "uptime_seconds": 86400,
  "memory_optimization": {
    "auto_cleanup_enabled": true,
    "cleanup_threshold": 80.0,
    "last_cleanup": "2025-01-24T10:30:00Z",
    "cleanup_count": 5
  },
  "hardware_acceleration": {
    "available": true,
    "preferred_encoder": "h264_videotoolbox",
    "supported_encoders": ["h264_videotoolbox", "hevc_videotoolbox"]
  }
}
```

---

### 20. 性能优化统计

**接口**: `GET /system/performance`  
**描述**: 获取详细的性能优化统计信息

#### 请求示例
```bash
curl -X GET "http://localhost:8000/system/performance"
```

#### 响应示例
```json
{
  "cache_stats": {
    "total_size_gb": 2.1,
    "max_size_gb": 5.0,
    "hit_rate": 0.85,
    "total_hits": 142,
    "total_misses": 25,
    "cleanup_count": 3
  },
  "hardware_info": {
    "available_encoders": ["h264_videotoolbox", "hevc_videotoolbox"],
    "preferred_encoder": "h264_videotoolbox",
    "encoder_details": {
      "h264_videotoolbox": {
        "name": "h264_videotoolbox",
        "type": "videotoolbox",
        "codec": "h264"
      }
    },
    "has_hardware_acceleration": true
  },
  "memory_stats": {
    "total_gb": 16.0,
    "available_gb": 5.2,
    "used_percent": 67.5,
    "max_usage_percent": 80.0,
    "chunk_size_mb": 100,
    "cleanup_triggered": 5,
    "last_cleanup": "2025-01-24T10:30:00Z"
  },
  "timestamp": "2025-01-24T11:00:00Z"
}
```

---

### 21. 任务管理

**接口**: `GET /system/tasks`  
**描述**: 获取所有任务状态和统计信息

#### 请求示例
```bash
curl -X GET "http://localhost:8000/system/tasks"
```

#### 响应示例
```json
{
  "total_active_tasks": 3,
  "task_summary": {
    "transcription": 1,
    "download": 1,
    "composition": 1,
    "keyframe": 0
  },
  "transcription_tasks": {
    "task_id_1": {
      "status": "processing",
      "progress": 65,
      "start_time": 1640995200,
      "video_url": "https://example.com/video1.mp4",
      "estimated_remaining": 120
    }
  },
  "download_tasks": {
    "task_id_2": {
      "status": "completed",
      "progress": 100,
      "start_time": 1640995100,
      "completion_time": 1640995300,
      "file_size": 241467392
    }
  },
  "composition_tasks": {
    "task_id_3": {
      "status": "composing",
      "progress": 45,
      "start_time": 1640995250,
      "composition_type": "concat",
      "video_count": 2
    }
  },
  "system_limits": {
    "max_concurrent_tasks": 5,
    "can_accept_new_tasks": true,
    "memory_available_for_tasks": "4.2GB"
  }
}
```

---

### 22. 手动内存清理

**接口**: `POST /system/cleanup`  
**描述**: 手动触发系统内存和缓存清理

#### 请求示例
```bash
curl -X POST "http://localhost:8000/system/cleanup" \
-H "Content-Type: application/json" \
-d '{
  "cleanup_type": "all",
  "force": false
}'
```

#### 请求参数
```json
{
  "cleanup_type": "string",  // 可选，清理类型 (默认: "all")
  "force": false            // 可选，强制清理 (默认: false)
}
```

#### 清理类型
- `memory`: 仅清理内存
- `cache`: 仅清理缓存
- `temp`: 仅清理临时文件
- `all`: 清理所有资源

#### 响应示例
```json
{
  "status": "success",
  "message": "系统清理完成",
  "cleanup_results": {
    "memory_freed_mb": 512.3,
    "cache_cleared_gb": 1.2,
    "temp_files_removed": 15,
    "cleanup_duration_seconds": 2.5
  },
  "before_cleanup": {
    "memory_percent": 82.1,
    "cache_size_gb": 3.2
  },
  "after_cleanup": {
    "memory_percent": 65.4,
    "cache_size_gb": 2.0
  }
}
```

---

### 23. 硬件加速状态

**接口**: `GET /system/hardware`  
**描述**: 获取硬件加速支持状态和详细信息

#### 请求示例
```bash
curl -X GET "http://localhost:8000/system/hardware"
```

#### 响应示例
```json
{
  "hardware_acceleration_available": true,
  "preferred_encoder": "h264_videotoolbox",
  "available_encoders": {
    "h264_videotoolbox": {
      "name": "h264_videotoolbox",
      "type": "videotoolbox",
      "codec": "h264",
      "platform": "macOS",
      "performance_rating": 9,
      "quality_rating": 8
    },
    "hevc_videotoolbox": {
      "name": "hevc_videotoolbox", 
      "type": "videotoolbox",
      "codec": "hevc",
      "platform": "macOS",
      "performance_rating": 9,
      "quality_rating": 9
    }
  },
  "system_info": {
    "platform": "darwin",
    "architecture": "arm64",
    "cpu_count": 8,
    "gpu_available": true
  },
  "encoder_test_results": {
    "h264_videotoolbox": {
      "tested": true,
      "working": true,
      "test_time": "2025-01-24T10:00:00Z"
    }
  },
  "recommendations": {
    "best_for_speed": "h264_videotoolbox",
    "best_for_quality": "hevc_videotoolbox",
    "best_for_compatibility": "h264_videotoolbox"
  }
}
```

---

## 🔧 内存优化最佳实践 (v3.1)

### 启动优化
- **延迟加载**: Whisper模型仅在首次转录时加载
- **硬件检测**: 编码器检测仅在需要时执行
- **启动内存**: 服务启动时内存使用 < 1GB

### 运行时优化
- **自动清理**: 内存使用超过80%时自动清理
- **智能缓存**: 基于LRU算法的缓存管理
- **资源监控**: 每5秒检查一次系统资源

### 手动优化建议
1. **定期清理**: 建议每小时执行一次手动清理
2. **监控内存**: 通过 `/system/resources` 监控内存使用
3. **合理并发**: 根据系统内存调整并发任务数
4. **硬件加速**: 启用硬件编码器提升性能

### 内存使用阈值
| 内存使用率 | 系统行为 | 建议操作 |
|-----------|----------|----------|
| < 60% | 正常运行 | 无需操作 |
| 60-80% | 监控状态 | 考虑清理缓存 |
| 80-90% | 自动清理 | 减少并发任务 |
| > 90% | 拒绝新任务 | 立即手动清理 |_time": 1640995100,
      "end_time": 1640995300
    }
  },
  "keyframe_tasks": {},
  "composition_tasks": {
    "task_id_3": {
      "status": "composing",
      "progress": 30,
      "start_time": 1640995400,
      "composition_type": "concat"
    }
  }
}
```

---

### 21. 性能统计

**接口**: `GET /system/performance/stats`  
**描述**: 获取性能优化统计信息

#### 请求示例
```bash
curl -X GET "http://localhost:7878/system/performance/stats"
```

#### 响应示例
```json
{
  "status": "success",
  "data": {
    "cache_stats": {
      "total_items": 25,
      "total_size_mb": 1024.5,
      "max_size_mb": 5120.0,
      "usage_percent": 20.0,
      "hit_rate": 0.85,
      "items_by_type": {
        "metadata": {"count": 15, "size_mb": 2.5},
        "processed_video": {"count": 10, "size_mb": 1022.0}
      }
    },
    "hardware_info": {
      "available_encoders": ["h264_videotoolbox", "hevc_videotoolbox"],
      "preferred_encoder": "h264_videotoolbox",
      "has_hardware_acceleration": true,
      "encoder_details": {
        "h264_videotoolbox": {
          "type": "videotoolbox",
          "codec": "h264"
        }
      }
    },
    "memory_stats": {
      "memory_info": {
        "total_gb": 16.0,
        "available_gb": 5.2,
        "used_percent": 67.5
      },
      "max_usage_percent": 80.0,
      "chunk_size_mb": 100,
      "is_memory_available": true
    }
  },
  "timestamp": 1640995500
}
```

---

### 22. 缓存管理

#### 获取缓存统计
**接口**: `GET /system/performance/cache/stats`

```bash
curl -X GET "http://localhost:7878/system/performance/cache/stats"
```

#### 清空缓存
**接口**: `POST /system/performance/cache/clear`

```bash
curl -X POST "http://localhost:7878/system/performance/cache/clear"
```

---

### 23. 内存优化

#### 获取内存统计
**接口**: `GET /system/performance/memory`

```bash
curl -X GET "http://localhost:7878/system/performance/memory"
```

#### 触发内存清理
**接口**: `POST /system/performance/memory/cleanup`

```bash
curl -X POST "http://localhost:7878/system/performance/memory/cleanup"
```

---

### 24. 系统优化

**接口**: `POST /system/performance/optimize`  
**描述**: 执行系统性能优化

```bash
curl -X POST "http://localhost:7878/system/performance/optimize"
```

#### 响应示例
```json
{
  "status": "success",
  "message": "系统性能优化完成",
  "data": {
    "cache_cleaned": true,
    "memory_freed_mb": 256.5,
    "temp_files_removed": 15,
    "optimization_time": 2.3
  }
}
```

---

## 🚨 错误处理和状态码

### HTTP状态码说明

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 413 | Payload Too Large | 请求体过大或视频时长超限 |
| 429 | Too Many Requests | 请求频率过高 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用或资源不足 |

### 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "detail": "错误描述信息",
  "error_code": "ERROR_CODE",
  "timestamp": 1640995600,
  "request_id": "req_123456789"
}
```

### 常见错误代码

#### 参数验证错误 (4xx)

| 错误代码 | HTTP状态码 | 描述 | 解决方案 |
|----------|------------|------|----------|
| INVALID_URL | 400 | 视频URL格式无效 | 检查URL格式和可访问性 |
| MISSING_PARAMETER | 400 | 缺少必需参数 | 检查请求参数完整性 |
| INVALID_QUALITY | 400 | 不支持的视频质量 | 使用支持的质量选项 |
| INVALID_FORMAT | 400 | 不支持的视频格式 | 使用支持的格式选项 |
| INVALID_COMPOSITION_TYPE | 400 | 不支持的合成类型 | 使用支持的合成类型 |
| VIDEO_TOO_LONG | 413 | 视频时长超过限制 | 使用较短的视频或分段处理 |
| FILE_TOO_LARGE | 413 | 文件大小超过限制 | 使用较小的文件或压缩 |
| TASK_NOT_FOUND | 404 | 任务不存在 | 检查任务ID是否正确 |

#### 系统资源错误 (5xx)

| 错误代码 | HTTP状态码 | 描述 | 解决方案 |
|----------|------------|------|----------|
| RESOURCE_LIMIT_EXCEEDED | 503 | 系统资源不足 | 等待其他任务完成或稍后重试 |
| MEMORY_INSUFFICIENT | 503 | 内存不足 | 等待内存释放或重启服务 |
| DISK_SPACE_INSUFFICIENT | 503 | 磁盘空间不足 | 清理磁盘空间 |
| MAX_TASKS_EXCEEDED | 503 | 超过最大并发任务数 | 等待任务完成或稍后重试 |
| PROCESSING_ERROR | 500 | 处理过程中出错 | 检查输入文件或联系支持 |
| FFMPEG_ERROR | 500 | FFmpeg处理错误 | 检查视频格式兼容性 |
| DOWNLOAD_ERROR | 500 | 下载失败 | 检查网络连接和URL有效性 |

#### 任务状态错误

| 错误代码 | HTTP状态码 | 描述 | 解决方案 |
|----------|------------|------|----------|
| TASK_EXPIRED | 404 | 任务已过期 | 重新提交任务 |
| TASK_CANCELLED | 400 | 任务已被取消 | 重新提交任务 |
| TASK_FAILED | 500 | 任务执行失败 | 查看详细错误信息 |
| RESULT_NOT_READY | 400 | 结果尚未准备就绪 | 等待任务完成 |

### 错误处理最佳实践

#### 1. 重试策略
```javascript
const retryRequest = async (url, options, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      
      if (response.ok) {
        return response;
      }
      
      // 对于5xx错误进行重试
      if (response.status >= 500 && i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
        continue;
      }
      
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
};
```

#### 2. 错误分类处理
```javascript
const handleApiError = (error) => {
  const { status, error_code, detail } = error;
  
  switch (status) {
    case 400:
      // 参数错误，不应重试
      console.error('请求参数错误:', detail);
      break;
      
    case 404:
      // 资源不存在
      console.error('资源不存在:', detail);
      break;
      
    case 413:
      // 文件过大
      console.error('文件大小超限:', detail);
      break;
      
    case 503:
      // 服务不可用，可以重试
      console.warn('服务暂时不可用，稍后重试:', detail);
      break;
      
    case 500:
      // 服务器错误，可能需要重试
      console.error('服务器内部错误:', detail);
      break;
      
    default:
      console.error('未知错误:', detail);
  }
};
```

#### 3. 任务状态监控
```javascript
const monitorTask = async (taskId, taskType) => {
  const statusEndpoints = {
    transcription: `/transcription_status/${taskId}`,
    download: `/download_status/${taskId}`,
    keyframe: `/keyframe_status/${taskId}`,
    composition: `/composition_status/${taskId}`
  };
  
  const endpoint = statusEndpoints[taskType];
  let attempts = 0;
  const maxAttempts = 360; // 最多监控30分钟 (5秒间隔)
  
  while (attempts < maxAttempts) {
    try {
      const response = await fetch(`http://localhost:7878${endpoint}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('任务不存在或已过期');
        }
        throw new Error(`状态查询失败: ${response.status}`);
      }
      
      const status = await response.json();
      
      if (status.status === 'completed') {
        return { success: true, result: status };
      }
      
      if (status.status === 'failed') {
        return { success: false, error: status.error || status.message };
      }
      
      // 显示进度
      console.log(`任务进度: ${status.progress}% - ${status.message}`);
      
      // 等待5秒后继续查询
      await new Promise(resolve => setTimeout(resolve, 5000));
      attempts++;
      
    } catch (error) {
      console.error('状态查询错误:', error.message);
      
      // 网络错误等待后重试
      await new Promise(resolve => setTimeout(resolve, 10000));
      attempts++;
    }
  }
  
  return { success: false, error: '任务监控超时' };
};
```

### 调试和故障排除

#### 1. 启用详细日志
在开发环境中，可以通过以下方式获取更详细的错误信息：

```bash
# 查看服务日志
curl -X GET "http://localhost:7878/system/logs?level=debug&limit=100"
```

#### 2. 系统健康检查
```bash
# 检查系统状态
curl -X GET "http://localhost:7878/health"

# 检查资源使用情况
curl -X GET "http://localhost:7878/system/resources"

# 检查错误统计
curl -X GET "http://localhost:7878/system/errors/stats"
```

#### 3. 性能分析
```bash
# 获取性能统计
curl -X GET "http://localhost:7878/system/performance/stats"

# 检查缓存状态
curl -X GET "http://localhost:7878/system/performance/cache/stats"

# 检查内存使用
curl -X GET "http://localhost:7878/system/performance/memory"
```
---


## 📝 更新日志

### v3.1 (2025-01-24)
**🚀 重大性能优化**
- **内存优化**: 启动时内存使用减少90%，从8GB降至<1GB
- **延迟加载**: Whisper模型和硬件检测改为按需加载
- **自动清理**: 内存使用超过80%时自动触发清理机制
- **智能监控**: 新增系统资源实时监控和性能统计

**🎬 字幕功能增强**
- **TXT格式支持**: 新增对 `.txt` 纯文本字幕文件的支持
- **智能转换**: TXT文件自动转换为SRT格式，按标点符号智能分割
- **时间轴生成**: 根据文本长度自动分配字幕显示时长
- **格式验证**: 增强字幕文件格式验证和错误处理

**🔧 新增接口**
- `GET /system/performance` - 性能优化统计
- `POST /system/cleanup` - 手动内存清理
- `GET /system/hardware` - 硬件加速详情

**🐛 问题修复**
- 修复启动时内存使用过高导致的系统不稳定
- 优化硬件编码器检测逻辑，避免启动阻塞
- 改进错误处理和资源清理机制
- 增强字幕文件处理的稳定性

### v3.0 (2025-01-20)
**🎬 视频合成功能**
- 支持多种合成模式：拼接、画中画、并排显示、网格布局
- 本地视频文件支持，无需上传
- 硬件加速编码，提升处理速度

**🖼️ 关键帧提取**
- 智能关键帧提取算法
- 多种提取模式：时间间隔、指定时间点、平均分布
- 自动生成缩略图网格

### v2.2 (2025-01-15)
**📸 关键帧提取功能**
- 支持所有yt-dlp兼容的视频网站
- 多种提取方法和自定义参数
- 高质量图片输出

### v2.1 (2025-01-10)
**📥 视频下载功能**
- 支持多种质量和格式选择
- 异步下载和进度跟踪
- 直接文件下载支持

### v2.0 (2025-01-05)
**⚡ 性能优化**
- 硬件加速支持
- 缓存管理系统
- 系统资源监控

### v1.0 (2024-12-01)
**🎯 基础功能**
- 视频转录和字幕生成
- 异步任务处理
- 多语言支持

---

## 📞 技术支持

如果您在使用过程中遇到问题，请：

1. **查看日志**: 检查服务运行日志中的错误信息
2. **运行诊断**: 使用提供的诊断工具检查系统状态
3. **检查文档**: 参考故障排除部分的解决方案
4. **性能监控**: 定期检查系统资源使用情况

**推荐监控命令**:
```bash
# 实时监控系统状态
watch -n 5 'curl -s http://localhost:8000/system/resources | jq'

# 检查活跃任务
curl -s http://localhost:8000/system/tasks | jq '.task_summary'

# 性能统计
curl -s http://localhost:8000/system/performance | jq '.cache_stats'
```

---

*文档最后更新: 2025-01-24*  
*API版本: v3.1*  
*服务状态: 生产就绪*