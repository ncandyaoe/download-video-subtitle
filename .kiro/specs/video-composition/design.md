# 视频合成功能设计文档

## 概述

视频合成功能是对现有视频处理API的重要扩展，将提供多种视频合成模式，包括基础拼接、画中画、并排显示、字幕烧录等功能。该功能采用与现有功能相同的异步处理架构，确保系统的一致性和可扩展性。

## 架构设计

### 整体架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API 层        │    │   业务逻辑层      │    │   处理引擎层     │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ FastAPI 端点    │───▶│ 参数验证         │───▶│ FFmpeg 命令构建  │
│ 请求参数模型    │    │ 任务管理         │    │ 异步执行        │
│ 响应格式定义    │    │ 状态跟踪         │    │ 进度监控        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   存储层        │    │   资源管理层      │    │   错误处理层     │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ 临时文件管理    │    │ 内存监控         │    │ 异常捕获        │
│ 输出文件存储    │    │ 并发控制         │    │ 资源清理        │
│ 文件清理机制    │    │ 队列管理         │    │ 错误恢复        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 核心组件

#### 1. 请求参数模型

```python
class VideoCompositionParams(BaseModel):
    composition_type: str = "concat"  # 合成类型
    videos: List[VideoInput] = []     # 输入视频列表
    audio_file: Optional[str] = None  # 音频文件路径或URL
    subtitle_file: Optional[str] = None  # 字幕文件路径
    output_format: str = "mp4"        # 输出格式
    output_quality: str = "720p"      # 输出质量
    output_settings: OutputSettings = OutputSettings()

class VideoInput(BaseModel):
    video_url: str = ""               # 视频URL或文件路径
    start_time: Optional[float] = None # 开始时间（秒）
    end_time: Optional[float] = None   # 结束时间（秒）
    position: Optional[Position] = None # 位置信息（用于画中画）
    volume: float = 1.0               # 音量调整（0.0-2.0）

class Position(BaseModel):
    x: int = 0                        # X坐标
    y: int = 0                        # Y坐标
    width: Optional[int] = None       # 宽度
    height: Optional[int] = None      # 高度
    opacity: float = 1.0              # 透明度（0.0-1.0）

class OutputSettings(BaseModel):
    width: int = 1920                 # 输出宽度
    height: int = 1080                # 输出高度
    fps: int = 30                     # 帧率
    bitrate: Optional[str] = None     # 比特率
    codec: str = "libx264"            # 视频编码器
```

#### 2. 状态管理类

```python
class CompositionStatus:
    def __init__(self):
        self.status = "processing"     # processing, completed, failed
        self.progress = 0              # 0-100
        self.message = ""              # 当前状态描述
        self.result = None             # 最终结果
        self.error = None              # 错误信息
        self.current_stage = ""        # 当前处理阶段
        self.total_stages = 0          # 总阶段数
        self.temp_files = []           # 临时文件列表
        self.start_time = None         # 开始时间
        self.estimated_duration = 0    # 预估处理时间
```

#### 3. 合成引擎

```python
class VideoCompositionEngine:
    def __init__(self):
        self.max_concurrent_tasks = 2  # 最大并发任务数
        self.temp_dir = "temp_composition"
        self.output_dir = "compositions"
        
    async def compose_video(self, params: VideoCompositionParams, task_id: str):
        """主合成函数"""
        pass
        
    async def prepare_inputs(self, videos: List[VideoInput], task_id: str):
        """准备输入文件"""
        pass
        
    async def normalize_videos(self, video_files: List[str], task_id: str):
        """标准化视频参数"""
        pass
        
    async def execute_composition(self, params: VideoCompositionParams, 
                                normalized_files: List[str], task_id: str):
        """执行具体的合成操作"""
        pass
```

## 组件和接口

### API 端点设计

#### 1. 启动合成任务
```
POST /compose_video
Content-Type: application/json

{
  "composition_type": "concat|pip|side_by_side|slideshow|audio_video_subtitle",
  "videos": [
    {
      "video_url": "string",
      "start_time": 0.0,
      "end_time": 30.0,
      "position": {"x": 0, "y": 0, "width": 640, "height": 360},
      "volume": 1.0
    }
  ],
  "audio_file": "string",
  "subtitle_file": "string", 
  "output_format": "mp4",
  "output_quality": "720p",
  "output_settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "bitrate": "2M",
    "codec": "libx264"
  }
}
```

#### 2. 查询合成状态
```
GET /composition_status/{task_id}

Response:
{
  "task_id": "string",
  "status": "processing|completed|failed",
  "progress": 65,
  "message": "正在合成视频...",
  "current_stage": "normalizing_videos",
  "total_stages": 5,
  "estimated_remaining_time": 120
}
```

#### 3. 获取合成结果
```
GET /composition_result/{task_id}

Response:
{
  "task_id": "string",
  "result": {
    "output_file_path": "./compositions/task_id_output.mp4",
    "file_size": 52428800,
    "duration": 180.5,
    "resolution": "1920x1080",
    "format": "mp4",
    "composition_type": "concat",
    "processing_time": 145.2
  }
}
```

#### 4. 下载合成视频
```
GET /composition_file/{task_id}
```

### 合成类型实现

#### 1. 基础拼接 (concat)
```python
async def concat_videos(self, video_files: List[str], task_id: str) -> str:
    """视频拼接合成"""
    # 创建concat文件列表
    concat_file = os.path.join(self.temp_dir, f"{task_id}_concat.txt")
    with open(concat_file, 'w') as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")
    
    # 构建FFmpeg命令
    output_file = os.path.join(self.output_dir, f"{task_id}_concat.mp4")
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        output_file
    ]
    
    return await self.execute_ffmpeg_command(cmd, task_id)
```

#### 2. 画中画合成 (pip)
```python
async def picture_in_picture(self, main_video: str, overlay_video: str, 
                           position: Position, task_id: str) -> str:
    """画中画合成"""
    output_file = os.path.join(self.output_dir, f"{task_id}_pip.mp4")
    
    # 构建复杂的filter_complex命令
    filter_complex = (
        f"[1:v]scale={position.width}:{position.height}[overlay];"
        f"[0:v][overlay]overlay={position.x}:{position.y}"
    )
    
    cmd = [
        'ffmpeg',
        '-i', main_video,
        '-i', overlay_video,
        '-filter_complex', filter_complex,
        '-c:a', 'copy',
        output_file
    ]
    
    return await self.execute_ffmpeg_command(cmd, task_id)
```

#### 3. 音频视频字幕合成 (audio_video_subtitle)
```python
async def audio_video_subtitle_composition(self, video_file: str, 
                                         audio_file: str, subtitle_file: str, 
                                         task_id: str) -> str:
    """音频视频字幕三合一合成"""
    output_file = os.path.join(self.output_dir, f"{task_id}_avs.mp4")
    
    cmd = [
        'ffmpeg',
        '-i', video_file,      # 输入视频
        '-i', audio_file,      # 输入音频
        '-vf', f'subtitles={subtitle_file}',  # 烧录字幕
        '-c:v', 'libx264',     # 视频编码器
        '-c:a', 'aac',         # 音频编码器
        '-map', '0:v:0',       # 使用第一个输入的视频流
        '-map', '1:a:0',       # 使用第二个输入的音频流
        '-shortest',           # 以最短的流为准
        output_file
    ]
    
    return await self.execute_ffmpeg_command(cmd, task_id)
```

## 数据模型

### 数据库模型（可选）
```python
# 如果需要持久化任务信息
class CompositionTask:
    task_id: str
    user_id: Optional[str]
    composition_type: str
    input_files: List[str]
    output_file: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    processing_time: Optional[float]
```

### 文件结构
```
./compositions/
├── task_id_1/
│   ├── input_video_1.mp4
│   ├── input_video_2.mp4
│   ├── audio.mp3
│   ├── subtitles.srt
│   └── output.mp4
├── task_id_2/
│   └── ...
└── temp/
    ├── normalized_videos/
    ├── concat_lists/
    └── intermediate_files/
```

## 错误处理

### 错误类型定义
```python
class CompositionError(Exception):
    """合成相关错误基类"""
    pass

class InputValidationError(CompositionError):
    """输入验证错误"""
    pass

class ResourceLimitError(CompositionError):
    """资源限制错误"""
    pass

class ProcessingError(CompositionError):
    """处理过程错误"""
    pass

class FFmpegError(CompositionError):
    """FFmpeg执行错误"""
    pass
```

### 错误处理策略
```python
async def handle_composition_error(self, error: Exception, task_id: str):
    """统一错误处理"""
    status = composition_status[task_id]
    
    if isinstance(error, InputValidationError):
        status.status = "failed"
        status.error = f"输入验证失败: {str(error)}"
    elif isinstance(error, ResourceLimitError):
        status.status = "failed"
        status.error = f"资源限制: {str(error)}"
    elif isinstance(error, FFmpegError):
        status.status = "failed"
        status.error = f"视频处理失败: {str(error)}"
    else:
        status.status = "failed"
        status.error = f"未知错误: {str(error)}"
    
    # 清理临时文件
    await self.cleanup_temp_files(task_id)
    
    logger.error(f"合成任务 {task_id} 失败: {str(error)}")
```

## 测试策略

### 单元测试
```python
class TestVideoComposition:
    async def test_concat_videos(self):
        """测试视频拼接功能"""
        pass
        
    async def test_picture_in_picture(self):
        """测试画中画功能"""
        pass
        
    async def test_audio_video_subtitle(self):
        """测试音频视频字幕合成"""
        pass
        
    async def test_input_validation(self):
        """测试输入验证"""
        pass
        
    async def test_error_handling(self):
        """测试错误处理"""
        pass
```

### 集成测试
```python
class TestCompositionAPI:
    async def test_full_composition_workflow(self):
        """测试完整的合成工作流程"""
        pass
        
    async def test_concurrent_tasks(self):
        """测试并发任务处理"""
        pass
        
    async def test_resource_management(self):
        """测试资源管理"""
        pass
```

### 性能测试
- 不同文件大小的处理时间测试
- 内存使用情况监控
- 并发任务性能测试
- 磁盘空间使用测试

## 性能优化

### 处理优化
1. **预处理缓存**: 对相同参数的视频标准化结果进行缓存
2. **分段处理**: 对大文件进行分段处理，减少内存占用
3. **硬件加速**: 支持GPU加速编码（如果可用）
4. **并行处理**: 在可能的情况下并行处理多个步骤

### 资源管理
1. **内存监控**: 实时监控内存使用，超限时暂停新任务
2. **磁盘管理**: 定期清理临时文件和过期输出文件
3. **任务队列**: 实现优先级队列管理并发任务
4. **超时控制**: 设置合理的任务超时时间

### 扩展性设计
1. **插件架构**: 支持新的合成类型通过插件方式添加
2. **配置化**: 关键参数通过配置文件管理
3. **微服务化**: 可以将合成功能独立为微服务
4. **负载均衡**: 支持多实例部署和负载均衡