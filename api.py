import os
import subprocess
import gc
import psutil
import asyncio
import signal
import time
import uuid
import threading
from contextlib import asynccontextmanager
from loguru import logger
import math # 导入 math 用于时间戳计算
import json # <--- 在这里添加导入
from datetime import timedelta # 导入 timedelta 用于时间戳格式化
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware # 确保导入 CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from faster_whisper import WhisperModel
import re  # 添加正则表达式模块
import urllib.parse  # 添加URL解析模块
import hashlib  # 添加哈希计算模块
import shutil  # 添加文件操作模块
from performance_optimizer import get_performance_optimizer  # 导入性能优化器

# 配置日志记录
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("启动视频处理API服务")
    resource_monitor.start_monitoring()
    task_manager.start_cleanup_service()
    
    yield
    
    # 关闭时执行
    logger.info("关闭视频处理API服务")
    resource_monitor.stop_monitoring()
    task_manager.stop_cleanup_service()

app = FastAPI(lifespan=lifespan)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应配置具体的来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 定义请求体模型
class RequestParams(BaseModel):
    video_url: str = ""

class DownloadRequestParams(BaseModel):
    video_url: str = ""
    quality: str = "best"  # best, worst, 720p, 1080p, 480p
    format: str = "mp4"    # mp4, webm, mkv

class KeyframeRequestParams(BaseModel):
    video_url: str = ""
    method: str = "interval"  # interval, timestamps, keyframes, count
    interval: int = 30        # 每30秒截取一帧（method=interval时）
    timestamps: list = []     # 指定时间点列表（method=timestamps时）
    count: int = 10          # 总共截取帧数（method=count时）
    width: int = 1280        # 输出图片宽度
    height: int = 720        # 输出图片高度
    format: str = "jpg"      # 输出格式：jpg, png
    quality: int = 85        # JPEG质量（1-100）

# 视频合成相关数据模型
class Position(BaseModel):
    x: int = 0                        # X坐标
    y: int = 0                        # Y坐标
    width: Optional[int] = None       # 宽度
    height: Optional[int] = None      # 高度
    opacity: float = 1.0              # 透明度（0.0-1.0）

class VideoInput(BaseModel):
    video_url: str = ""               # 视频URL或文件路径
    start_time: Optional[float] = None # 开始时间（秒）
    end_time: Optional[float] = None   # 结束时间（秒）
    position: Optional[Position] = None # 位置信息（用于画中画）
    volume: float = 1.0               # 音量调整（0.0-2.0）

class OutputSettings(BaseModel):
    width: int = 1920                 # 输出宽度
    height: int = 1080                # 输出高度
    fps: int = 30                     # 帧率
    bitrate: Optional[str] = None     # 比特率
    codec: str = "libx264"            # 视频编码器

class VideoCompositionParams(BaseModel):
    composition_type: str = "concat"  # 合成类型: concat, pip, side_by_side, slideshow, audio_video_subtitle
    videos: List[VideoInput] = []     # 输入视频列表
    audio_file: Optional[str] = None  # 音频文件路径或URL
    subtitle_file: Optional[str] = None  # 字幕文件路径
    layout: str = "horizontal"        # 布局类型: horizontal, vertical, grid
    transition_type: str = "none"     # 转场类型: none, fade
    output_format: str = "mp4"        # 输出格式
    output_quality: str = "720p"      # 输出质量
    output_settings: OutputSettings = OutputSettings()

# 定义输出目录
OUTPUT_DIR = "output"
DOWNLOAD_DIR = "downloads"
KEYFRAME_DIR = "keyframes"
COMPOSITION_DIR = "compositions"
TEMP_COMPOSITION_DIR = "temp_composition"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(KEYFRAME_DIR, exist_ok=True)
os.makedirs(COMPOSITION_DIR, exist_ok=True)
os.makedirs(TEMP_COMPOSITION_DIR, exist_ok=True)

# --- 加载 faster-whisper 模型 ---
# 可选模型: "tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"
# "tiny" 模型更小，占用更少磁盘空间，适合资源受限环境
# 如果有兼容的 GPU 并已配置 CUDA，可以将 device 设置为 "cuda"
MODEL_SIZE = "tiny"
COMPUTE_TYPE = "int8" # 使用 int8 量化以减少内存占用和加速 CPU 推理
whisper_model = None

def load_whisper_model():
    """延迟加载Whisper模型"""
    global whisper_model
    if whisper_model is None:
        try:
            logger.info(f"正在加载 Faster Whisper 模型: {MODEL_SIZE} (设备=cpu, 计算类型={COMPUTE_TYPE})")
            whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
            logger.info("Faster Whisper 模型加载成功。")
        except Exception as e:
            logger.exception(f"加载 Faster Whisper 模型 '{MODEL_SIZE}' 失败: {e}")
            raise RuntimeError(f"无法加载 Whisper 模型: {e}") from e
    return whisper_model

def validate_and_clean_url(url: str) -> str:
    """
    验证和清理视频URL，支持本地文件
    
    Args:
        url: 原始视频URL或本地文件路径
        
    Returns:
        清理后的有效URL或文件路径
        
    Raises:
        HTTPException: 如果URL或文件路径无效
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL或文件路径不能为空")
    
    url = url.strip()
    
    # 移除可能的引号或其他字符
    url = url.strip('\'"')
    
    # 检查是否为本地文件路径
    if url.startswith('file://') or (not url.startswith(('http://', 'https://')) and os.path.exists(url)):
        return validate_local_video_file(url)
    
    # 原有的在线URL验证逻辑
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise HTTPException(status_code=400, detail="URL格式无效")
    
    # 由于yt-dlp支持数百个视频网站，我们不限制特定域名
    # 让yt-dlp自己处理网站兼容性
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc.lower()
    
    logger.info(f"URL验证通过: {url} (域名: {domain})")
    return url

def validate_local_video_file(file_path: str) -> str:
    """
    验证本地视频文件
    
    Args:
        file_path: 本地文件路径（可能包含file://前缀）
        
    Returns:
        标准化的文件路径
        
    Raises:
        HTTPException: 如果文件无效
    """
    # 处理file://协议
    if file_path.startswith('file://'):
        file_path = file_path[7:]  # 移除file://前缀
    
    # 转换为绝对路径
    file_path = os.path.abspath(file_path)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"视频文件不存在: {file_path}")
    
    # 检查是否为文件（不是目录）
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"路径不是文件: {file_path}")
    
    # 检查文件扩展名
    valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp'}
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension not in valid_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的视频格式: {file_extension}。支持的格式: {', '.join(valid_extensions)}"
        )
    
    # 检查文件大小（限制为2GB）
    file_size = os.path.getsize(file_path)
    max_size = 2 * 1024 * 1024 * 1024  # 2GB
    
    if file_size > max_size:
        raise HTTPException(
            status_code=413, 
            detail=f"视频文件过大: {file_size / 1024 / 1024:.1f}MB，最大支持: {max_size / 1024 / 1024:.1f}MB"
        )
    
    # 检查文件权限
    if not os.access(file_path, os.R_OK):
        raise HTTPException(status_code=403, detail=f"无法读取视频文件: {file_path}")
    
    logger.info(f"本地视频文件验证通过: {file_path} (大小: {file_size / 1024 / 1024:.1f}MB)")
    return file_path

def is_local_file(url: str) -> bool:
    """判断是否为本地文件路径"""
    if not url:
        return False
    
    url = url.strip().strip('\'"')
    
    # 检查file://协议
    if url.startswith('file://'):
        return True
    
    # 检查是否为本地路径且文件存在
    if not url.startswith(('http://', 'https://')) and os.path.exists(url):
        return True
    
    return False

# 不在启动时加载模型，改为真正的延迟加载
logger.info("Whisper模型将在首次使用时加载")

# --- API 端点 ---

# --- Helper function for SRT timestamp ---
def format_srt_timestamp(seconds: float) -> str:
    """Formats seconds into SRT timestamp format HH:MM:SS,ms"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    seconds = milliseconds // 1_000
    milliseconds %= 1_000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

@app.get("/")
async def root():
    """ 根路径，用于检查服务是否运行 """
    # return {"message": "Video Transcription API is running. Use POST /generate_text_from_video to transcribe."}
    return {"message": "视频转录 API 正在运行。请使用 POST /generate_text_from_video 进行转录。"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    from datetime import datetime
    
    # 获取资源状态
    resource_stats = resource_monitor.get_resource_stats()
    can_accept_tasks, resource_message = resource_monitor.check_resource_limits()
    
    return {
        "status": "healthy" if can_accept_tasks else "degraded",
        "timestamp": datetime.now().isoformat() + "Z",
        "active_transcription_tasks": len(processing_status),
        "active_download_tasks": len(download_status),
        "active_keyframe_tasks": len(keyframe_status),
        "active_composition_tasks": len(composition_status),
        "total_active_tasks": resource_stats['active_tasks'],
        "resource_status": {
            "can_accept_tasks": can_accept_tasks,
            "message": resource_message,
            "cpu_percent": resource_stats['cpu_percent'],
            "memory_percent": resource_stats['memory_percent'],
            "disk_percent": resource_stats['disk_percent'],
            "free_disk_gb": resource_stats['free_disk_gb']
        }
    }

@app.get("/system/resources")
async def get_system_resources():
    """获取系统资源状态"""
    return resource_monitor.get_resource_stats()

@app.get("/system/resources/history")
async def get_resource_history(duration_minutes: int = 5):
    """获取资源历史数据"""
    if duration_minutes < 1 or duration_minutes > 60:
        raise HTTPException(status_code=400, detail="duration_minutes必须在1-60之间")
    
    return resource_monitor.get_resource_history(duration_minutes)

@app.post("/system/resources/cleanup")
async def force_resource_cleanup():
    """强制执行资源清理"""
    try:
        resource_monitor.force_cleanup()
        return {"message": "资源清理已执行", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"强制资源清理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"资源清理失败: {str(e)}")

@app.put("/system/resources/limits")
async def update_resource_limits(
    max_concurrent_tasks: Optional[int] = None,
    max_memory_usage: Optional[int] = None,
    max_disk_usage: Optional[int] = None,
    max_cpu_usage: Optional[int] = None,
    min_free_disk_gb: Optional[float] = None
):
    """更新资源限制"""
    try:
        # 验证参数
        if max_concurrent_tasks is not None and (max_concurrent_tasks < 1 or max_concurrent_tasks > 10):
            raise HTTPException(status_code=400, detail="max_concurrent_tasks必须在1-10之间")
        
        if max_memory_usage is not None and (max_memory_usage < 50 or max_memory_usage > 95):
            raise HTTPException(status_code=400, detail="max_memory_usage必须在50-95之间")
        
        if max_disk_usage is not None and (max_disk_usage < 70 or max_disk_usage > 95):
            raise HTTPException(status_code=400, detail="max_disk_usage必须在70-95之间")
        
        if max_cpu_usage is not None and (max_cpu_usage < 70 or max_cpu_usage > 95):
            raise HTTPException(status_code=400, detail="max_cpu_usage必须在70-95之间")
        
        if min_free_disk_gb is not None and (min_free_disk_gb < 1 or min_free_disk_gb > 100):
            raise HTTPException(status_code=400, detail="min_free_disk_gb必须在1-100之间")
        
        # 更新限制
        kwargs = {}
        if max_concurrent_tasks is not None:
            kwargs['max_concurrent_tasks'] = max_concurrent_tasks
        if max_memory_usage is not None:
            kwargs['max_memory_usage'] = max_memory_usage
        if max_disk_usage is not None:
            kwargs['max_disk_usage'] = max_disk_usage
        if max_cpu_usage is not None:
            kwargs['max_cpu_usage'] = max_cpu_usage
        if min_free_disk_gb is not None:
            kwargs['min_free_disk_gb'] = min_free_disk_gb
        
        if not kwargs:
            raise HTTPException(status_code=400, detail="至少需要提供一个参数")
        
        updated_stats = resource_monitor.update_limits(**kwargs)
        return {
            "message": "资源限制已更新",
            "updated_limits": updated_stats['limits'],
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新资源限制失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新资源限制失败: {str(e)}")

@app.post("/system/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消指定的任务"""
    try:
        # 检查任务是否存在
        task_found = False
        task_type = None
        
        if task_id in composition_status:
            task_found = True
            task_type = "composition"
            if composition_status[task_id].status == "processing":
                composition_status[task_id].status = "failed"
                composition_status[task_id].error = "任务已被取消"
                composition_status[task_id].message = "任务已被用户取消"
        
        elif task_id in processing_status:
            task_found = True
            task_type = "transcription"
            if processing_status[task_id].status == "processing":
                processing_status[task_id].status = "failed"
                processing_status[task_id].error = "任务已被取消"
                processing_status[task_id].message = "任务已被用户取消"
        
        elif task_id in download_status:
            task_found = True
            task_type = "download"
            if download_status[task_id].status == "downloading":
                download_status[task_id].status = "failed"
                download_status[task_id].error = "任务已被取消"
                download_status[task_id].message = "任务已被用户取消"
        
        elif task_id in keyframe_status:
            task_found = True
            task_type = "keyframe"
            if keyframe_status[task_id].status == "extracting":
                keyframe_status[task_id].status = "failed"
                keyframe_status[task_id].error = "任务已被取消"
                keyframe_status[task_id].message = "任务已被用户取消"
        
        if not task_found:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        logger.info(f"任务已取消: {task_id} (类型: {task_type})")
        return {
            "message": f"任务已取消: {task_id}",
            "task_type": task_type,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@app.get("/system/tasks")
async def get_all_tasks():
    """获取所有任务状态"""
    try:
        tasks = {
            "composition_tasks": {
                task_id: {
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "start_time": status.start_time,
                    "current_stage": status.current_stage
                }
                for task_id, status in composition_status.items()
            },
            "transcription_tasks": {
                task_id: {
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message
                }
                for task_id, status in processing_status.items()
            },
            "download_tasks": {
                task_id: {
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "file_size": status.file_size,
                    "downloaded_size": status.downloaded_size
                }
                for task_id, status in download_status.items()
            },
            "keyframe_tasks": {
                task_id: {
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "total_frames": status.total_frames,
                    "extracted_frames": status.extracted_frames
                }
                for task_id, status in keyframe_status.items()
            }
        }
        
        # 统计信息
        total_tasks = (len(composition_status) + len(processing_status) + 
                      len(download_status) + len(keyframe_status))
        
        active_tasks = sum([
            len([s for s in composition_status.values() if s.status == "processing"]),
            len([s for s in processing_status.values() if s.status == "processing"]),
            len([s for s in download_status.values() if s.status == "downloading"]),
            len([s for s in keyframe_status.values() if s.status == "extracting"])
        ])
        
        return {
            "tasks": tasks,
            "summary": {
                "total_tasks": total_tasks,
                "active_tasks": active_tasks,
                "composition_tasks": len(composition_status),
                "transcription_tasks": len(processing_status),
                "download_tasks": len(download_status),
                "keyframe_tasks": len(keyframe_status)
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@app.get("/system/errors/stats")
async def get_error_stats():
    """获取错误统计信息"""
    try:
        return error_handler.get_error_stats()
    except Exception as e:
        logger.error(f"获取错误统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取错误统计失败: {str(e)}")

@app.get("/system/errors/recent")
async def get_recent_errors(limit: int = 10):
    """获取最近的错误记录"""
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit必须在1-100之间")
        
        return {
            "recent_errors": error_handler.get_recent_errors(limit),
            "timestamp": time.time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最近错误失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最近错误失败: {str(e)}")

@app.get("/system/cleanup/stats")
async def get_cleanup_stats():
    """获取清理统计信息"""
    try:
        return task_manager.get_cleanup_stats()
    except Exception as e:
        logger.error(f"获取清理统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取清理统计失败: {str(e)}")

@app.post("/system/cleanup/force")
async def force_comprehensive_cleanup():
    """强制执行全面清理"""
    try:
        cleanup_start = time.time()
        
        # 执行各种清理操作
        expired_tasks = task_manager.cleanup_expired_tasks()
        temp_files = task_manager.cleanup_temp_files()
        processes = task_manager.cleanup_zombie_processes()
        task_manager.cleanup_orphaned_resources()
        
        # 执行资源监控器的清理
        resource_monitor.force_cleanup()
        
        cleanup_duration = time.time() - cleanup_start
        
        return {
            "message": "全面清理已完成",
            "cleanup_results": {
                "expired_tasks_cleaned": expired_tasks,
                "temp_files_cleaned": temp_files,
                "processes_terminated": processes,
                "cleanup_duration": round(cleanup_duration, 2)
            },
            "timestamp": cleanup_start
        }
        
    except Exception as e:
        error_info = error_handler.handle_error(e, context={'operation': 'force_comprehensive_cleanup'})
        logger.error(f"强制全面清理失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"强制全面清理失败: {error_info['message']}")

@app.post("/system/tasks/{task_id}/force-cleanup")
async def force_task_cleanup(task_id: str):
    """强制清理指定任务的资源"""
    try:
        # 查找任务
        task_found = False
        task_status = None
        
        for task_map in [composition_status, processing_status, download_status, keyframe_status]:
            if task_id in task_map:
                task_status = task_map[task_id]
                task_found = True
                break
        
        if not task_found:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        # 强制清理任务资源
        error_handler._cleanup_task_resources(task_id, task_status)
        
        # 终止相关进程
        task_manager._terminate_task_process(task_id)
        
        return {
            "message": f"任务资源清理完成: {task_id}",
            "task_id": task_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_info = error_handler.handle_error(e, task_id, {'operation': 'force_task_cleanup'})
        logger.error(f"强制任务清理失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"强制任务清理失败: {error_info['message']}")

# ==================== 性能优化相关端点 ====================

@app.get("/system/performance/stats")
async def get_performance_stats():
    """获取性能优化统计信息"""
    try:
        stats = performance_optimizer.get_optimization_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'get_performance_stats'})
        logger.error(f"获取性能统计失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"获取性能统计失败: {error_info['message']}")

@app.get("/system/performance/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        cache_stats = performance_optimizer.cache_manager.get_cache_stats()
        return {
            "status": "success",
            "data": cache_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'get_cache_stats'})
        logger.error(f"获取缓存统计失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {error_info['message']}")

@app.post("/system/performance/cache/clear")
async def clear_cache():
    """清空所有缓存"""
    try:
        performance_optimizer.cache_manager.clear_cache()
        return {
            "status": "success",
            "message": "缓存已清空",
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'clear_cache'})
        logger.error(f"清空缓存失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {error_info['message']}")

@app.get("/system/performance/hardware")
async def get_hardware_info():
    """获取硬件加速信息"""
    try:
        hardware_info = performance_optimizer.hardware_detector.get_hardware_info()
        return {
            "status": "success",
            "data": hardware_info,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'get_hardware_info'})
        logger.error(f"获取硬件信息失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"获取硬件信息失败: {error_info['message']}")

@app.get("/system/performance/memory")
async def get_memory_stats():
    """获取内存优化统计信息"""
    try:
        memory_stats = performance_optimizer.memory_processor.get_memory_stats()
        return {
            "status": "success",
            "data": memory_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'get_memory_stats'})
        logger.error(f"获取内存统计失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"获取内存统计失败: {error_info['message']}")

@app.post("/system/performance/memory/cleanup")
async def trigger_memory_cleanup():
    """触发内存清理"""
    try:
        performance_optimizer.memory_processor.trigger_memory_cleanup()
        memory_stats = performance_optimizer.memory_processor.get_memory_stats()
        return {
            "status": "success",
            "message": "内存清理完成",
            "data": memory_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'trigger_memory_cleanup'})
        logger.error(f"内存清理失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"内存清理失败: {error_info['message']}")

@app.post("/system/performance/optimize")
async def optimize_system_performance():
    """执行系统性能优化"""
    try:
        # 触发内存清理
        performance_optimizer.memory_processor.trigger_memory_cleanup()
        
        # 清理过期缓存
        performance_optimizer.cache_manager._cleanup_old_cache()
        
        # 获取优化后的统计信息
        stats = performance_optimizer.get_optimization_stats()
        
        return {
            "status": "success",
            "message": "系统性能优化完成",
            "data": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        error_info = error_handler.handle_error(e, None, {'operation': 'optimize_system_performance'})
        logger.error(f"系统性能优化失败: {error_info['message']}")
        raise HTTPException(status_code=500, detail=f"系统性能优化失败: {error_info['message']}")

def check_memory_usage():
    """检查内存使用情况"""
    memory = psutil.virtual_memory()
    logger.info(f"内存使用情况: {memory.percent}% ({memory.used / 1024**3:.2f}GB / {memory.total / 1024**3:.2f}GB)")
    return memory.percent

def cleanup_memory():
    """强制垃圾回收以释放内存"""
    gc.collect()
    logger.info("执行垃圾回收以释放内存")

def transcribe_audio_in_process(audio_file, beam_size, chunk_length, model_size):
    """在独立进程中执行转录，避免影响主服务"""
    try:
        # 在子进程中重新加载模型
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(
            audio_file,
            beam_size=beam_size,
            chunk_length=chunk_length,
            initial_prompt="输出中文简体的句子"
        )
        
        # 将生成器转换为列表以便序列化
        segments_list = []
        for segment in segments:
            segments_list.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })
        
        return {
            'segments': segments_list,
            'language': info.language,
            'duration': info.duration
        }
    except Exception as e:
        return {'error': str(e)}

# 全局变量来跟踪处理状态
processing_status = {}
download_status = {}
keyframe_status = {}
composition_status = {}

class ProcessingStatus:
    def __init__(self):
        self.status = "processing"
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None

class DownloadStatus:
    def __init__(self):
        self.status = "downloading"
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.file_path = None
        self.file_size = 0
        self.downloaded_size = 0

class KeyframeStatus:
    def __init__(self):
        self.status = "extracting"
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.frames = []  # 存储帧信息列表
        self.total_frames = 0
        self.extracted_frames = 0

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


class ResourceMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        self.max_concurrent_tasks = 3  # 最大并发任务数
        self.max_memory_usage = 80     # 最大内存使用率(%)
        self.max_disk_usage = 90       # 最大磁盘使用率(%)
        self.min_free_disk_gb = 5      # 最小剩余磁盘空间(GB)
        self.max_cpu_usage = 90        # 最大CPU使用率(%)
        self.monitoring = False
        self.monitor_thread = None
        self.alert_threshold_count = 3  # 连续超限次数触发警报
        self.alert_counts = {
            'memory': 0,
            'disk': 0,
            'cpu': 0
        }
        self.stats = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'free_disk_gb': 0,
            'active_tasks': 0,
            'memory_used_gb': 0,
            'memory_total_gb': 0,
            'disk_used_gb': 0,
            'disk_total_gb': 0,
            'last_update': 0
        }
        self.history = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'tasks': []
        }
        self.max_history_length = 60  # 保留60个数据点（5分钟历史）
    
    def start_monitoring(self):
        """启动资源监控"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("资源监控已启动")
    
    def stop_monitoring(self):
        """停止资源监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.info("资源监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取系统资源信息
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_usage = psutil.disk_usage('/')
                
                # 更新统计信息
                self.stats.update({
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': (disk_usage.used / disk_usage.total) * 100,
                    'disk_used_gb': disk_usage.used / (1024**3),
                    'disk_total_gb': disk_usage.total / (1024**3),
                    'free_disk_gb': disk_usage.free / (1024**3),
                    'last_update': time.time()
                })
                
                # 获取活跃任务数
                active_composition_tasks = len([
                    status for status in composition_status.values() 
                    if status.status == "processing"
                ])
                active_transcription_tasks = len([
                    status for status in processing_status.values() 
                    if status.status == "processing"
                ])
                active_download_tasks = len([
                    status for status in download_status.values() 
                    if status.status == "downloading"
                ])
                active_keyframe_tasks = len([
                    status for status in keyframe_status.values() 
                    if status.status == "extracting"
                ])
                
                total_active_tasks = (active_composition_tasks + active_transcription_tasks + 
                                    active_download_tasks + active_keyframe_tasks)
                self.stats['active_tasks'] = total_active_tasks
                
                # 更新历史数据
                self._update_history()
                
                # 检查资源警报
                self._check_resource_alerts()
                
                time.sleep(5)  # 每5秒更新一次
                
            except Exception as e:
                logger.error(f"资源监控错误: {str(e)}")
                time.sleep(10)
    
    def _update_history(self):
        """更新历史数据"""
        timestamp = time.time()
        
        # 添加新数据点
        self.history['cpu'].append((timestamp, self.stats['cpu_percent']))
        self.history['memory'].append((timestamp, self.stats['memory_percent']))
        self.history['disk'].append((timestamp, self.stats['disk_percent']))
        self.history['tasks'].append((timestamp, self.stats['active_tasks']))
        
        # 保持历史数据长度限制
        for key in self.history:
            if len(self.history[key]) > self.max_history_length:
                self.history[key] = self.history[key][-self.max_history_length:]
    
    def _check_resource_alerts(self):
        """检查资源警报"""
        # 检查内存使用率
        if self.stats['memory_percent'] > self.max_memory_usage:
            self.alert_counts['memory'] += 1
            if self.alert_counts['memory'] >= self.alert_threshold_count:
                logger.warning(f"内存使用率持续过高: {self.stats['memory_percent']:.1f}% "
                             f"(连续{self.alert_counts['memory']}次超过{self.max_memory_usage}%)")
                self._trigger_memory_cleanup()
        else:
            self.alert_counts['memory'] = 0
        
        # 检查磁盘使用率
        if self.stats['disk_percent'] > self.max_disk_usage:
            self.alert_counts['disk'] += 1
            if self.alert_counts['disk'] >= self.alert_threshold_count:
                logger.warning(f"磁盘使用率持续过高: {self.stats['disk_percent']:.1f}% "
                             f"(连续{self.alert_counts['disk']}次超过{self.max_disk_usage}%)")
                self._trigger_disk_cleanup()
        else:
            self.alert_counts['disk'] = 0
        
        # 检查CPU使用率
        if self.stats['cpu_percent'] > self.max_cpu_usage:
            self.alert_counts['cpu'] += 1
            if self.alert_counts['cpu'] >= self.alert_threshold_count:
                logger.warning(f"CPU使用率持续过高: {self.stats['cpu_percent']:.1f}% "
                             f"(连续{self.alert_counts['cpu']}次超过{self.max_cpu_usage}%)")
        else:
            self.alert_counts['cpu'] = 0
    
    def _trigger_memory_cleanup(self):
        """触发内存清理"""
        try:
            # 强制垃圾回收
            gc.collect()
            logger.info("执行内存清理：强制垃圾回收")
            
            # 可以在这里添加更多内存清理逻辑
            # 例如清理缓存、释放不必要的资源等
            
        except Exception as e:
            logger.error(f"内存清理失败: {str(e)}")
    
    def _trigger_disk_cleanup(self):
        """触发磁盘清理"""
        try:
            # 清理临时文件
            temp_dirs = [TEMP_COMPOSITION_DIR, OUTPUT_DIR, DOWNLOAD_DIR, KEYFRAME_DIR]
            current_time = time.time()
            cleaned_files = 0
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for file_name in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file_name)
                        if os.path.isfile(file_path):
                            # 删除超过1小时的临时文件
                            if (current_time - os.path.getctime(file_path)) > 3600:
                                try:
                                    os.remove(file_path)
                                    cleaned_files += 1
                                except Exception as e:
                                    logger.error(f"清理文件失败 {file_path}: {str(e)}")
            
            if cleaned_files > 0:
                logger.info(f"磁盘清理完成：清理了{cleaned_files}个临时文件")
            
        except Exception as e:
            logger.error(f"磁盘清理失败: {str(e)}")
    
    def check_resource_limits(self) -> tuple[bool, str]:
        """检查资源限制"""
        # 检查并发任务数
        if self.stats['active_tasks'] >= self.max_concurrent_tasks:
            return False, f"已达到最大并发任务数限制: {self.max_concurrent_tasks}"
        
        # 检查内存使用率
        if self.stats['memory_percent'] > self.max_memory_usage:
            return False, f"内存使用率过高: {self.stats['memory_percent']:.1f}% > {self.max_memory_usage}%"
        
        # 检查磁盘使用率
        if self.stats['disk_percent'] > self.max_disk_usage:
            return False, f"磁盘使用率过高: {self.stats['disk_percent']:.1f}% > {self.max_disk_usage}%"
        
        # 检查剩余磁盘空间
        if self.stats['free_disk_gb'] < self.min_free_disk_gb:
            return False, f"磁盘剩余空间不足: {self.stats['free_disk_gb']:.1f}GB < {self.min_free_disk_gb}GB"
        
        # 检查CPU使用率
        if self.stats['cpu_percent'] > self.max_cpu_usage:
            return False, f"CPU使用率过高: {self.stats['cpu_percent']:.1f}% > {self.max_cpu_usage}%"
        
        return True, "资源检查通过"
    
    def get_resource_stats(self) -> dict:
        """获取资源统计信息"""
        return {
            'cpu_percent': round(self.stats['cpu_percent'], 1),
            'memory_percent': round(self.stats['memory_percent'], 1),
            'memory_used_gb': round(self.stats['memory_used_gb'], 2),
            'memory_total_gb': round(self.stats['memory_total_gb'], 2),
            'disk_percent': round(self.stats['disk_percent'], 1),
            'disk_used_gb': round(self.stats['disk_used_gb'], 2),
            'disk_total_gb': round(self.stats['disk_total_gb'], 2),
            'free_disk_gb': round(self.stats['free_disk_gb'], 2),
            'active_tasks': self.stats['active_tasks'],
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'last_update': self.stats['last_update'],
            'limits': {
                'max_memory_usage': self.max_memory_usage,
                'max_disk_usage': self.max_disk_usage,
                'max_cpu_usage': self.max_cpu_usage,
                'min_free_disk_gb': self.min_free_disk_gb
            },
            'alert_counts': self.alert_counts.copy()
        }
    
    def get_resource_history(self, duration_minutes: int = 5) -> dict:
        """获取资源历史数据"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        history = {}
        for key, data in self.history.items():
            # 过滤指定时间范围内的数据
            filtered_data = [(timestamp, value) for timestamp, value in data 
                           if timestamp >= cutoff_time]
            history[key] = filtered_data
        
        return history
    
    def force_cleanup(self):
        """强制执行资源清理"""
        logger.info("执行强制资源清理")
        self._trigger_memory_cleanup()
        self._trigger_disk_cleanup()
    
    def update_limits(self, **kwargs):
        """更新资源限制"""
        updated = []
        if 'max_concurrent_tasks' in kwargs:
            self.max_concurrent_tasks = kwargs['max_concurrent_tasks']
            updated.append(f"max_concurrent_tasks={self.max_concurrent_tasks}")
        
        if 'max_memory_usage' in kwargs:
            self.max_memory_usage = kwargs['max_memory_usage']
            updated.append(f"max_memory_usage={self.max_memory_usage}%")
        
        if 'max_disk_usage' in kwargs:
            self.max_disk_usage = kwargs['max_disk_usage']
            updated.append(f"max_disk_usage={self.max_disk_usage}%")
        
        if 'max_cpu_usage' in kwargs:
            self.max_cpu_usage = kwargs['max_cpu_usage']
            updated.append(f"max_cpu_usage={self.max_cpu_usage}%")
        
        if 'min_free_disk_gb' in kwargs:
            self.min_free_disk_gb = kwargs['min_free_disk_gb']
            updated.append(f"min_free_disk_gb={self.min_free_disk_gb}GB")
        
        if updated:
            logger.info(f"资源限制已更新: {', '.join(updated)}")
        
        return self.get_resource_stats()

# 视频合成错误处理类
class CompositionError(Exception):
    """合成相关错误基类"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = time.time()

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

class TaskTimeoutError(CompositionError):
    """任务超时错误"""
    pass

class FileSystemError(CompositionError):
    """文件系统错误"""
    pass

class NetworkError(CompositionError):
    """网络错误"""
    pass

class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.error_stats = {
            'total_errors': 0,
            'error_types': {},
            'recent_errors': []
        }
        self.max_recent_errors = 100
    
    def handle_error(self, error: Exception, task_id: str = None, context: dict = None) -> dict:
        """统一错误处理"""
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'timestamp': time.time(),
            'task_id': task_id,
            'context': context or {}
        }
        
        # 更新错误统计
        self.error_stats['total_errors'] += 1
        error_type = error_info['error_type']
        self.error_stats['error_types'][error_type] = self.error_stats['error_types'].get(error_type, 0) + 1
        
        # 记录最近错误
        self.error_stats['recent_errors'].append(error_info)
        if len(self.error_stats['recent_errors']) > self.max_recent_errors:
            self.error_stats['recent_errors'] = self.error_stats['recent_errors'][-self.max_recent_errors:]
        
        # 根据错误类型进行特定处理
        if isinstance(error, CompositionError):
            return self._handle_composition_error(error, task_id, context)
        elif isinstance(error, HTTPException):
            return self._handle_http_error(error, task_id, context)
        else:
            return self._handle_generic_error(error, task_id, context)
    
    def _handle_composition_error(self, error: CompositionError, task_id: str, context: dict) -> dict:
        """处理合成相关错误"""
        logger.error("合成错误 (任务ID: %s): %s", task_id, error.message, extra={
            'error_code': error.error_code,
            'details': error.details,
            'context': context
        })
        
        # 更新任务状态
        if task_id and task_id in composition_status:
            status = composition_status[task_id]
            status.status = "failed"
            status.error = error.message
            status.message = f"任务失败: {error.message}"
            
            # 清理任务相关资源
            self._cleanup_task_resources(task_id, status)
        
        return {
            'error_code': error.error_code,
            'message': error.message,
            'details': error.details,
            'timestamp': error.timestamp,
            'recoverable': self._is_recoverable_error(error)
        }
    
    def _handle_http_error(self, error: HTTPException, task_id: str, context: dict) -> dict:
        """处理HTTP错误"""
        logger.warning(f"HTTP错误 (任务ID: {task_id}): {error.detail}", extra={
            'status_code': error.status_code,
            'context': context
        })
        
        return {
            'error_code': f'HTTP_{error.status_code}',
            'message': error.detail,
            'status_code': error.status_code,
            'timestamp': time.time(),
            'recoverable': error.status_code < 500
        }
    
    def _handle_generic_error(self, error: Exception, task_id: str, context: dict) -> dict:
        """处理通用错误"""
        logger.error(f"未知错误 (任务ID: {task_id}): {str(error)}", extra={
            'error_type': type(error).__name__,
            'context': context
        }, exc_info=True)
        
        # 更新任务状态
        if task_id:
            self._update_task_status_on_error(task_id, str(error))
        
        return {
            'error_code': 'UNKNOWN_ERROR',
            'message': f"系统内部错误: {str(error)}",
            'error_type': type(error).__name__,
            'timestamp': time.time(),
            'recoverable': False
        }
    
    def _update_task_status_on_error(self, task_id: str, error_message: str):
        """更新任务状态为错误状态"""
        status_maps = [
            (composition_status, "processing"),
            (processing_status, "processing"),
            (download_status, "downloading"),
            (keyframe_status, "extracting")
        ]
        
        for status_map, active_status in status_maps:
            if task_id in status_map:
                status = status_map[task_id]
                if hasattr(status, 'status') and status.status == active_status:
                    status.status = "failed"
                    status.error = error_message
                    status.message = f"任务失败: {error_message}"
                    
                    # 清理资源
                    if hasattr(status, 'temp_files'):
                        self._cleanup_task_resources(task_id, status)
                break
    
    def _cleanup_task_resources(self, task_id: str, status):
        """清理任务相关资源"""
        try:
            # 清理临时文件
            if hasattr(status, 'temp_files') and status.temp_files:
                for temp_file in status.temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            logger.info(f"清理临时文件: {temp_file}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {temp_file}: {str(e)}")
                
                status.temp_files.clear()
            
            # 清理任务相关目录
            task_dirs = [
                os.path.join(TEMP_COMPOSITION_DIR, task_id),
                os.path.join(COMPOSITION_DIR, task_id)
            ]
            
            for task_dir in task_dirs:
                if os.path.exists(task_dir):
                    try:
                        import shutil
                        shutil.rmtree(task_dir)
                        logger.info(f"清理任务目录: {task_dir}")
                    except Exception as e:
                        logger.warning(f"清理任务目录失败 {task_dir}: {str(e)}")
            
        except Exception as e:
            logger.error(f"资源清理异常 (任务ID: {task_id}): {str(e)}")
    
    def _is_recoverable_error(self, error: CompositionError) -> bool:
        """判断错误是否可恢复"""
        recoverable_types = [
            NetworkError,
            ResourceLimitError
        ]
        
        non_recoverable_types = [
            InputValidationError,
            FFmpegError,
            TaskTimeoutError
        ]
        
        if type(error) in recoverable_types:
            return True
        elif type(error) in non_recoverable_types:
            return False
        else:
            # 默认根据错误消息判断
            recoverable_keywords = ['timeout', 'network', 'connection', 'temporary']
            error_msg = error.message.lower()
            return any(keyword in error_msg for keyword in recoverable_keywords)
    
    def get_error_stats(self) -> dict:
        """获取错误统计信息"""
        return {
            'total_errors': self.error_stats['total_errors'],
            'error_types': self.error_stats['error_types'].copy(),
            'recent_errors_count': len(self.error_stats['recent_errors']),
            'most_common_errors': sorted(
                self.error_stats['error_types'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近的错误记录"""
        return self.error_stats['recent_errors'][-limit:]

class TaskManager:
    """增强的任务管理器"""
    
    def __init__(self, resource_monitor: ResourceMonitor, error_handler: ErrorHandler):
        self.resource_monitor = resource_monitor
        self.error_handler = error_handler
        self.task_timeout = 3600  # 任务超时时间(秒) - 1小时
        self.cleanup_interval = 300  # 清理间隔(秒) - 5分钟
        self.cleanup_thread = None
        self.running = False
        self.active_processes = {}  # 跟踪活跃的进程
        self.task_locks = {}  # 任务锁，防止并发操作
        
        # 清理统计
        self.cleanup_stats = {
            'expired_tasks_cleaned': 0,
            'temp_files_cleaned': 0,
            'processes_terminated': 0,
            'last_cleanup_time': 0
        }
    
    def start_cleanup_service(self):
        """启动清理服务"""
        if not self.running:
            self.running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            logger.info("增强任务清理服务已启动")
    
    def stop_cleanup_service(self):
        """停止清理服务"""
        self.running = False
        
        # 终止所有活跃进程
        self._terminate_all_processes()
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("增强任务清理服务已停止")
    
    def register_process(self, task_id: str, process):
        """注册活跃进程"""
        self.active_processes[task_id] = process
        logger.debug(f"注册进程: 任务ID {task_id}, PID {process.pid if hasattr(process, 'pid') else 'N/A'}")
    
    def unregister_process(self, task_id: str):
        """注销进程"""
        if task_id in self.active_processes:
            del self.active_processes[task_id]
            logger.debug(f"注销进程: 任务ID {task_id}")
    
    def _cleanup_loop(self):
        """增强的清理循环"""
        while self.running:
            try:
                cleanup_start = time.time()
                
                # 执行各种清理任务
                expired_count = self.cleanup_expired_tasks()
                files_count = self.cleanup_temp_files()
                processes_count = self.cleanup_zombie_processes()
                self.cleanup_orphaned_resources()
                
                # 更新统计信息
                self.cleanup_stats.update({
                    'expired_tasks_cleaned': self.cleanup_stats['expired_tasks_cleaned'] + expired_count,
                    'temp_files_cleaned': self.cleanup_stats['temp_files_cleaned'] + files_count,
                    'processes_terminated': self.cleanup_stats['processes_terminated'] + processes_count,
                    'last_cleanup_time': cleanup_start
                })
                
                cleanup_duration = time.time() - cleanup_start
                if cleanup_duration > 10:  # 如果清理时间超过10秒，记录警告
                    logger.warning(f"清理周期耗时过长: {cleanup_duration:.2f}秒")
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                error_info = self.error_handler.handle_error(e, context={'operation': 'cleanup_loop'})
                logger.error(f"清理服务错误: {error_info['message']}")
                time.sleep(60)  # 出错后等待更长时间
    
    def cleanup_expired_tasks(self) -> int:
        """清理过期任务，返回清理数量"""
        current_time = time.time()
        expired_tasks = []
        timeout_tasks = []
        
        # 检查所有任务状态映射
        task_maps = [
            (composition_status, "processing"),
            (processing_status, "processing"),
            (download_status, "downloading"),
            (keyframe_status, "extracting")
        ]
        
        for task_map, active_status in task_maps:
            for task_id, status in list(task_map.items()):
                if not hasattr(status, 'start_time') or not status.start_time:
                    continue
                
                task_age = current_time - status.start_time
                
                # 检查任务超时
                if task_age > self.task_timeout and status.status == active_status:
                    timeout_tasks.append((task_id, status, task_map))
                    logger.warning(f"任务超时: {task_id} (运行时间: {task_age:.1f}秒)")
                
                # 标记过期任务（超时时间的2倍后删除）
                elif task_age > (self.task_timeout * 2):
                    expired_tasks.append((task_id, task_map))
        
        # 处理超时任务
        for task_id, status, task_map in timeout_tasks:
            try:
                # 终止相关进程
                self._terminate_task_process(task_id)
                
                # 更新状态
                status.status = "failed"
                status.error = "任务超时"
                status.message = f"任务执行超时（{self.task_timeout}秒），已自动取消"
                
                # 清理资源
                self.error_handler._cleanup_task_resources(task_id, status)
                
            except Exception as e:
                logger.error(f"处理超时任务失败 {task_id}: {str(e)}")
        
        # 删除过期任务
        for task_id, task_map in expired_tasks:
            try:
                del task_map[task_id]
                logger.info(f"清理过期任务: {task_id}")
            except KeyError:
                pass  # 任务可能已被其他线程删除
        
        return len(timeout_tasks) + len(expired_tasks)
    
    def cleanup_temp_files(self) -> int:
        """增强的临时文件清理，返回清理文件数量"""
        cleaned_count = 0
        current_time = time.time()
        
        # 定义需要清理的目录和对应的保留时间
        cleanup_configs = [
            (TEMP_COMPOSITION_DIR, 3600),    # 临时文件1小时后清理
            (COMPOSITION_DIR, 86400 * 7),    # 输出文件7天后清理
            (OUTPUT_DIR, 86400 * 3),         # 转录输出3天后清理
            (DOWNLOAD_DIR, 86400 * 7),       # 下载文件7天后清理
            (KEYFRAME_DIR, 86400 * 3),       # 关键帧3天后清理
        ]
        
        for dir_path, max_age in cleanup_configs:
            if not os.path.exists(dir_path):
                continue
            
            try:
                for item_name in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item_name)
                    
                    try:
                        # 获取文件/目录的创建时间
                        item_age = current_time - os.path.getctime(item_path)
                        
                        if item_age > max_age:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                                cleaned_count += 1
                                logger.debug(f"清理临时文件: {item_path}")
                            elif os.path.isdir(item_path):
                                import shutil
                                shutil.rmtree(item_path)
                                cleaned_count += 1
                                logger.debug(f"清理临时目录: {item_path}")
                    
                    except Exception as e:
                        logger.warning(f"清理项目失败 {item_path}: {str(e)}")
            
            except Exception as e:
                logger.error(f"清理目录失败 {dir_path}: {str(e)}")
        
        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个临时文件/目录")
        
        return cleaned_count
    
    def cleanup_zombie_processes(self) -> int:
        """清理僵尸进程"""
        terminated_count = 0
        
        for task_id, process in list(self.active_processes.items()):
            try:
                # 检查进程是否还在运行
                if hasattr(process, 'poll') and process.poll() is not None:
                    # 进程已结束，从列表中移除
                    self.unregister_process(task_id)
                    continue
                
                # 检查任务是否已被标记为失败或取消
                task_cancelled = False
                for task_map in [composition_status, processing_status, download_status, keyframe_status]:
                    if task_id in task_map:
                        status = task_map[task_id]
                        if hasattr(status, 'status') and status.status in ['failed', 'cancelled']:
                            task_cancelled = True
                            break
                
                if task_cancelled:
                    self._terminate_task_process(task_id)
                    terminated_count += 1
            
            except Exception as e:
                logger.warning(f"检查进程状态失败 {task_id}: {str(e)}")
        
        return terminated_count
    
    def cleanup_orphaned_resources(self):
        """清理孤立资源"""
        try:
            # 清理任务锁
            current_time = time.time()
            expired_locks = []
            
            for task_id, lock_time in self.task_locks.items():
                if current_time - lock_time > 3600:  # 1小时后清理锁
                    expired_locks.append(task_id)
            
            for task_id in expired_locks:
                del self.task_locks[task_id]
                logger.debug(f"清理过期任务锁: {task_id}")
        
        except Exception as e:
            logger.error(f"清理孤立资源失败: {str(e)}")
    
    def _terminate_task_process(self, task_id: str):
        """终止任务相关进程"""
        if task_id in self.active_processes:
            process = self.active_processes[task_id]
            try:
                if hasattr(process, 'terminate'):
                    process.terminate()
                    
                    # 等待进程结束
                    try:
                        process.wait(timeout=5)
                    except:
                        # 如果进程不响应，强制杀死
                        if hasattr(process, 'kill'):
                            process.kill()
                
                self.unregister_process(task_id)
                logger.info(f"终止任务进程: {task_id}")
                
            except Exception as e:
                logger.error(f"终止进程失败 {task_id}: {str(e)}")
    
    def _terminate_all_processes(self):
        """终止所有活跃进程"""
        for task_id in list(self.active_processes.keys()):
            self._terminate_task_process(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """增强的任务取消功能"""
        try:
            # 获取任务锁
            if task_id in self.task_locks:
                logger.warning(f"任务正在被其他操作处理: {task_id}")
                return False
            
            self.task_locks[task_id] = time.time()
            
            try:
                # 查找并取消任务
                task_found = False
                task_maps = [
                    (composition_status, "processing"),
                    (processing_status, "processing"),
                    (download_status, "downloading"),
                    (keyframe_status, "extracting")
                ]
                
                for task_map, active_status in task_maps:
                    if task_id in task_map:
                        status = task_map[task_id]
                        if hasattr(status, 'status') and status.status == active_status:
                            # 终止相关进程
                            self._terminate_task_process(task_id)
                            
                            # 更新状态
                            status.status = "failed"
                            status.error = "任务已被取消"
                            status.message = "任务已被用户取消"
                            
                            # 清理资源
                            self.error_handler._cleanup_task_resources(task_id, status)
                            
                            task_found = True
                            logger.info(f"任务已取消: {task_id}")
                            break
                
                return task_found
            
            finally:
                # 释放任务锁
                if task_id in self.task_locks:
                    del self.task_locks[task_id]
        
        except Exception as e:
            error_info = self.error_handler.handle_error(e, task_id, {'operation': 'cancel_task'})
            logger.error(f"取消任务失败: {error_info['message']}")
            return False
    
    def get_cleanup_stats(self) -> dict:
        """获取清理统计信息"""
        return {
            'cleanup_stats': self.cleanup_stats.copy(),
            'active_processes': len(self.active_processes),
            'task_locks': len(self.task_locks),
            'cleanup_running': self.running
        }





# FFmpeg命令构建器和执行器
class FFmpegCommandBuilder:
    """FFmpeg命令构建器基类"""
    
    def __init__(self):
        self.command = ['ffmpeg']
        self.inputs = []
        self.filters = []
        self.outputs = []
        self.global_options = []
        
    def add_global_option(self, option: str, value: str = None):
        """添加全局选项"""
        self.global_options.append(option)
        if value:
            self.global_options.append(value)
        return self
    
    def add_input(self, input_file: str, options: dict = None):
        """添加输入文件"""
        input_entry = {'file': input_file, 'options': options or {}}
        self.inputs.append(input_entry)
        return self
    
    def add_filter(self, filter_str: str):
        """添加滤镜"""
        self.filters.append(filter_str)
        return self
    
    def add_output(self, output_file: str, options: dict = None):
        """添加输出文件"""
        output_entry = {'file': output_file, 'options': options or {}}
        self.outputs.append(output_entry)
        return self
    
    def build(self) -> List[str]:
        """构建完整的FFmpeg命令"""
        cmd = ['ffmpeg'] + self.global_options
        
        # 添加输入文件和选项
        for input_entry in self.inputs:
            for option, value in input_entry['options'].items():
                cmd.extend([f'-{option}', str(value)])
            cmd.extend(['-i', input_entry['file']])
        
        # 添加滤镜
        if self.filters:
            cmd.extend(['-filter_complex', ';'.join(self.filters)])
        
        # 添加输出文件和选项
        for output_entry in self.outputs:
            for option, value in output_entry['options'].items():
                if value is not None:  # 跳过None值
                    if value == '':  # 对于空字符串值，只添加选项名
                        cmd.append(f'-{option}')
                    else:
                        cmd.extend([f'-{option}', str(value)])
            cmd.append(output_entry['file'])
        
        return cmd
    
    def validate_command(self, cmd: List[str]) -> bool:
        """验证命令的安全性"""
        # 检查危险的命令注入，但排除FFmpeg滤镜中的合法使用
        dangerous_patterns = ['&&', '||', '`', '$']
        cmd_str = ' '.join(cmd)
        
        for pattern in dangerous_patterns:
            if pattern in cmd_str:
                logger.warning(f"检测到潜在危险的命令模式: {pattern}")
                return False
        
        # 检查分号，但排除FFmpeg滤镜中的使用
        if ';' in cmd_str:
            # 检查是否在滤镜上下文中
            filter_context = False
            for i, arg in enumerate(cmd):
                if arg == '-filter_complex':
                    filter_context = True
                elif filter_context and not arg.startswith('-'):
                    # 这是滤镜参数，允许包含分号
                    continue
                elif arg.startswith('-'):
                    filter_context = False
                
                if not filter_context and ';' in arg:
                    logger.warning(f"检测到潜在危险的分号: {arg}")
                    return False
        
        # 检查重定向符号，但排除FFmpeg滤镜中的使用
        if '>' in cmd_str or '<' in cmd_str:
            # 检查是否在滤镜上下文中
            filter_context = False
            for i, arg in enumerate(cmd):
                if arg == '-filter_complex':
                    filter_context = True
                elif filter_context and not arg.startswith('-'):
                    # 这是滤镜参数，允许包含 > 和 <
                    continue
                elif arg.startswith('-'):
                    filter_context = False
                
                if not filter_context and ('>' in arg or '<' in arg):
                    logger.warning(f"检测到潜在危险的重定向: {arg}")
                    return False
        
        # 检查管道符号，但排除FFmpeg滤镜中的使用
        if '|' in cmd_str:
            # 检查是否在滤镜上下文中
            filter_context = False
            for i, arg in enumerate(cmd):
                if arg == '-filter_complex':
                    filter_context = True
                elif filter_context and not arg.startswith('-'):
                    # 这是滤镜参数，允许包含 |
                    continue
                elif arg.startswith('-'):
                    filter_context = False
                
                if not filter_context and '|' in arg:
                    logger.warning(f"检测到潜在危险的管道: {arg}")
                    return False
        
        # 检查输入文件是否存在
        for input_entry in self.inputs:
            if not os.path.exists(input_entry['file']) and not input_entry['file'].startswith('http'):
                logger.error(f"输入文件不存在: {input_entry['file']}")
                return False
        
        return True

class FFmpegExecutor:
    """FFmpeg命令执行器"""
    
    def __init__(self, max_concurrent_tasks: int = 2):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = 0
        
    async def execute_command(self, cmd: List[str], task_id: str, 
                            progress_callback=None, timeout: int = 3600) -> str:
        """异步执行FFmpeg命令"""
        try:
            # 检查并发任务限制
            if self.running_tasks >= self.max_concurrent_tasks:
                raise ResourceLimitError(f"已达到最大并发任务数限制: {self.max_concurrent_tasks}")
            
            # 应用硬件加速优化
            optimized_cmd = performance_optimizer.optimize_ffmpeg_command(cmd, 'medium')
            
            self.running_tasks += 1
            logger.info(f"开始执行FFmpeg命令 (任务ID: {task_id}): {' '.join(optimized_cmd)}")
            if optimized_cmd != cmd:
                logger.info(f"已应用硬件加速优化 (任务ID: {task_id})")
            
            # 创建异步进程
            process = await asyncio.create_subprocess_exec(
                *optimized_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待进程完成，带超时控制
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise ProcessingError(f"FFmpeg命令执行超时 (超过{timeout}秒)")
            
            # 检查执行结果
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"FFmpeg命令执行失败 (任务ID: {task_id}): {error_msg}")
                raise FFmpegError(f"FFmpeg执行失败: {error_msg}")
            
            logger.info(f"FFmpeg命令执行成功 (任务ID: {task_id})")
            return stdout.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f"FFmpeg命令执行异常 (任务ID: {task_id}): {str(e)}")
            raise
        finally:
            self.running_tasks -= 1
    
    async def get_video_info(self, video_file: str) -> dict:
        """获取视频文件信息"""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_file
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise FFmpegError(f"获取视频信息失败: {error_msg}")
            
            return json.loads(stdout.decode('utf-8'))
            
        except json.JSONDecodeError as e:
            raise FFmpegError(f"解析视频信息失败: {str(e)}")
        except Exception as e:
            raise FFmpegError(f"获取视频信息异常: {str(e)}")

class FFmpegProgressParser:
    """FFmpeg进度解析器"""
    
    def __init__(self):
        self.duration_pattern = re.compile(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})')
        self.progress_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')
        
    def parse_duration(self, stderr_line: str) -> float:
        """解析视频总时长"""
        match = self.duration_pattern.search(stderr_line)
        if match:
            hours, minutes, seconds, centiseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
        return 0.0
    
    def parse_progress(self, stderr_line: str) -> float:
        """解析当前进度时间"""
        match = self.progress_pattern.search(stderr_line)
        if match:
            hours, minutes, seconds, centiseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
        return 0.0
    
    def calculate_progress_percentage(self, current_time: float, total_duration: float) -> int:
        """计算进度百分比"""
        if total_duration <= 0:
            return 0
        return min(100, int((current_time / total_duration) * 100))

class EnhancedFFmpegExecutor(FFmpegExecutor):
    """增强的FFmpeg执行器，支持进度监控"""
    
    def __init__(self, max_concurrent_tasks: int = 2):
        super().__init__(max_concurrent_tasks)
        self.progress_parser = FFmpegProgressParser()
    
    async def execute_command_with_progress(self, cmd: List[str], task_id: str, 
                                          status_obj, timeout: int = 3600) -> str:
        """执行FFmpeg命令并实时更新进度"""
        try:
            if self.running_tasks >= self.max_concurrent_tasks:
                raise ResourceLimitError(f"已达到最大并发任务数限制: {self.max_concurrent_tasks}")
            
            # 应用硬件加速优化
            optimized_cmd = performance_optimizer.optimize_ffmpeg_command(cmd, 'medium')
            
            self.running_tasks += 1
            logger.info(f"开始执行FFmpeg命令 (任务ID: {task_id}): {' '.join(optimized_cmd)}")
            if optimized_cmd != cmd:
                logger.info(f"已应用硬件加速优化 (任务ID: {task_id})")
            
            # 创建异步进程
            process = await asyncio.create_subprocess_exec(
                *optimized_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            total_duration = 0.0
            stdout_data = []
            stderr_data = []
            
            # 异步读取stderr以获取进度信息
            async def read_stderr():
                nonlocal total_duration
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    stderr_data.append(line_str)
                    
                    # 解析总时长
                    if total_duration == 0.0:
                        total_duration = self.progress_parser.parse_duration(line_str)
                    
                    # 解析当前进度
                    current_time = self.progress_parser.parse_progress(line_str)
                    if current_time > 0 and total_duration > 0:
                        progress = self.progress_parser.calculate_progress_percentage(
                            current_time, total_duration
                        )
                        status_obj.progress = min(95, progress)  # 最多95%，留5%给后处理
                        status_obj.message = f"处理中... {progress}%"
            
            # 异步读取stdout
            async def read_stdout():
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    stdout_data.append(line.decode('utf-8', errors='ignore'))
            
            # 并发执行读取任务
            read_tasks = [
                asyncio.create_task(read_stderr()),
                asyncio.create_task(read_stdout())
            ]
            
            # 等待进程完成
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                await asyncio.gather(*read_tasks, return_exceptions=True)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise ProcessingError(f"FFmpeg命令执行超时 (超过{timeout}秒)")
            
            # 检查执行结果
            if process.returncode != 0:
                error_msg = '\n'.join(stderr_data)
                logger.error(f"FFmpeg命令执行失败 (任务ID: {task_id}): {error_msg}")
                raise FFmpegError(f"FFmpeg执行失败: {error_msg}")
            
            logger.info(f"FFmpeg命令执行成功 (任务ID: {task_id})")
            return '\n'.join(stdout_data)
            
        except Exception as e:
            logger.error(f"FFmpeg命令执行异常 (任务ID: {task_id}): {str(e)}")
            raise
        finally:
            self.running_tasks -= 1
    
    async def validate_inputs(self, inputs: List[str]) -> bool:
        """验证输入文件的有效性"""
        for input_file in inputs:
            if input_file.startswith('http'):
                # 对于URL，我们跳过本地文件检查
                continue
            
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入文件不存在: {input_file}")
            
            try:
                # 使用ffprobe验证文件格式
                info = await self.get_video_info(input_file)
                if not info.get('streams'):
                    raise InputValidationError(f"无效的媒体文件: {input_file}")
            except Exception as e:
                raise InputValidationError(f"文件验证失败 {input_file}: {str(e)}")
        
        return True

# 全局实例
resource_monitor = ResourceMonitor()
error_handler = ErrorHandler()
task_manager = TaskManager(resource_monitor, error_handler)
performance_optimizer = get_performance_optimizer()  # 初始化性能优化器
ffmpeg_executor = EnhancedFFmpegExecutor(max_concurrent_tasks=2)

# 视频预处理和标准化功能
class VideoInfo:
    """视频信息类"""
    
    def __init__(self, info_dict: dict):
        self.raw_info = info_dict
        self.format_info = info_dict.get('format', {})
        self.streams = info_dict.get('streams', [])
        
        # 解析视频流信息
        self.video_stream = None
        self.audio_stream = None
        
        for stream in self.streams:
            if stream.get('codec_type') == 'video' and not self.video_stream:
                self.video_stream = stream
            elif stream.get('codec_type') == 'audio' and not self.audio_stream:
                self.audio_stream = stream
    
    @property
    def duration(self) -> float:
        """获取视频时长"""
        if self.format_info.get('duration'):
            return float(self.format_info['duration'])
        elif self.video_stream and self.video_stream.get('duration'):
            return float(self.video_stream['duration'])
        return 0.0
    
    @property
    def width(self) -> int:
        """获取视频宽度"""
        return int(self.video_stream.get('width', 0)) if self.video_stream else 0
    
    @property
    def height(self) -> int:
        """获取视频高度"""
        return int(self.video_stream.get('height', 0)) if self.video_stream else 0
    
    @property
    def fps(self) -> float:
        """获取帧率"""
        if self.video_stream and self.video_stream.get('r_frame_rate'):
            fps_str = self.video_stream['r_frame_rate']
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den) if float(den) != 0 else 0.0
            return float(fps_str)
        return 0.0
    
    @property
    def video_codec(self) -> str:
        """获取视频编码器"""
        return self.video_stream.get('codec_name', '') if self.video_stream else ''
    
    @property
    def audio_codec(self) -> str:
        """获取音频编码器"""
        return self.audio_stream.get('codec_name', '') if self.audio_stream else ''
    
    @property
    def has_video(self) -> bool:
        """是否包含视频流"""
        return self.video_stream is not None
    
    @property
    def has_audio(self) -> bool:
        """是否包含音频流"""
        return self.audio_stream is not None
    
    @property
    def file_size(self) -> int:
        """获取文件大小"""
        return int(self.format_info.get('size', 0))

class VideoValidator:
    """视频验证器"""
    
    def __init__(self):
        self.max_duration = 10800  # 3小时
        self.max_file_size = 2 * 1024 * 1024 * 1024  # 2GB
        self.supported_video_codecs = ['h264', 'h265', 'hevc', 'vp8', 'vp9', 'av1']
        self.supported_audio_codecs = ['aac', 'mp3', 'opus', 'vorbis', 'ac3']
    
    async def validate_video_file(self, file_path: str) -> VideoInfo:
        """验证视频文件并返回视频信息"""
        try:
            # 获取视频信息
            info_dict = await ffmpeg_executor.get_video_info(file_path)
            video_info = VideoInfo(info_dict)
            
            # 检查是否包含视频流
            if not video_info.has_video:
                raise InputValidationError(f"文件不包含视频流: {file_path}")
            
            # 检查时长限制
            if video_info.duration > self.max_duration:
                raise ResourceLimitError(
                    f"视频时长 ({video_info.duration/60:.1f}分钟) 超过限制 "
                    f"({self.max_duration/60:.1f}分钟)"
                )
            
            # 检查文件大小限制
            if video_info.file_size > self.max_file_size:
                raise ResourceLimitError(
                    f"文件大小 ({video_info.file_size/1024/1024:.1f}MB) 超过限制 "
                    f"({self.max_file_size/1024/1024:.1f}MB)"
                )
            
            # 检查分辨率
            if video_info.width <= 0 or video_info.height <= 0:
                raise InputValidationError(f"无效的视频分辨率: {video_info.width}x{video_info.height}")
            
            # 检查帧率
            if video_info.fps <= 0 or video_info.fps > 120:
                logger.warning(f"异常的帧率: {video_info.fps}, 文件: {file_path}")
            
            logger.info(f"视频验证通过: {file_path} - {video_info.width}x{video_info.height}, "
                       f"{video_info.duration:.1f}s, {video_info.fps:.1f}fps")
            
            return video_info
            
        except Exception as e:
            if isinstance(e, (InputValidationError, ResourceLimitError)):
                raise
            raise InputValidationError(f"视频文件验证失败 {file_path}: {str(e)}")
    
    def check_compatibility(self, video_infos: List[VideoInfo]) -> dict:
        """检查多个视频的兼容性"""
        if not video_infos:
            return {"compatible": True, "issues": []}
        
        issues = []
        
        # 检查分辨率一致性
        resolutions = [(info.width, info.height) for info in video_infos]
        unique_resolutions = set(resolutions)
        if len(unique_resolutions) > 1:
            issues.append(f"分辨率不一致: {unique_resolutions}")
        
        # 检查帧率一致性
        fps_values = [info.fps for info in video_infos]
        unique_fps = set(fps_values)
        if len(unique_fps) > 1:
            issues.append(f"帧率不一致: {unique_fps}")
        
        # 检查编码器
        video_codecs = [info.video_codec for info in video_infos]
        unique_codecs = set(video_codecs)
        if len(unique_codecs) > 1:
            issues.append(f"视频编码器不一致: {unique_codecs}")
        
        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "needs_normalization": len(issues) > 0
        }

# 全局视频验证器实例
video_validator = VideoValidator()

class VideoNormalizer:
    """视频标准化处理器"""
    
    def __init__(self):
        self.default_settings = {
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'video_bitrate': '2M',
            'audio_bitrate': '128k',
            'audio_sample_rate': 48000
        }
    
    async def normalize_video(self, input_file: str, output_file: str, 
                            settings: dict = None, task_id: str = None,
                            status_obj = None) -> str:
        """标准化单个视频文件"""
        try:
            # 合并设置
            norm_settings = {**self.default_settings, **(settings or {})}
            
            # 获取输入视频信息
            video_info = await video_validator.validate_video_file(input_file)
            
            # 检查是否需要标准化
            if self._is_already_normalized(video_info, norm_settings):
                logger.info(f"视频已符合标准，跳过标准化: {input_file}")
                # 直接复制文件
                import shutil
                shutil.copy2(input_file, output_file)
                return output_file
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 视频编码设置
            video_options = {
                'c:v': norm_settings['video_codec'],
                's': f"{norm_settings['width']}x{norm_settings['height']}",
                'r': str(norm_settings['fps']),
                'b:v': norm_settings['video_bitrate']
            }
            
            # 音频编码设置
            audio_options = {
                'c:a': norm_settings['audio_codec'],
                'b:a': norm_settings['audio_bitrate'],
                'ar': str(norm_settings['audio_sample_rate'])
            }
            
            # 合并选项
            output_options = {**video_options, **audio_options}
            builder.add_output(output_file, output_options)
            
            # 构建并验证命令
            cmd = builder.build()
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg命令验证失败")
            
            # 执行标准化
            if status_obj:
                status_obj.message = f"正在标准化视频: {os.path.basename(input_file)}"
                await ffmpeg_executor.execute_command_with_progress(
                    cmd, task_id or "normalize", status_obj
                )
            else:
                await ffmpeg_executor.execute_command(cmd, task_id or "normalize")
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"标准化失败，输出文件不存在: {output_file}")
            
            logger.info(f"视频标准化完成: {input_file} -> {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"视频标准化失败: {input_file} -> {output_file}, 错误: {str(e)}")
            # 清理可能的不完整输出文件
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise
    
    async def normalize_multiple_videos(self, input_files: List[str], 
                                      output_dir: str, settings: dict = None,
                                      task_id: str = None, status_obj = None) -> List[str]:
        """标准化多个视频文件"""
        normalized_files = []
        total_files = len(input_files)
        
        try:
            for i, input_file in enumerate(input_files):
                # 生成输出文件名
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(output_dir, f"{base_name}_normalized.mp4")
                
                # 更新进度
                if status_obj:
                    progress = int((i / total_files) * 80)  # 标准化占80%进度
                    status_obj.progress = progress
                    status_obj.message = f"标准化视频 {i+1}/{total_files}: {base_name}"
                
                # 标准化单个视频
                normalized_file = await self.normalize_video(
                    input_file, output_file, settings, 
                    f"{task_id}_norm_{i}" if task_id else None, status_obj
                )
                normalized_files.append(normalized_file)
                
                logger.info(f"完成标准化 {i+1}/{total_files}: {normalized_file}")
            
            return normalized_files
            
        except Exception as e:
            # 清理已生成的文件
            for file in normalized_files:
                try:
                    if os.path.exists(file):
                        os.remove(file)
                except:
                    pass
            raise ProcessingError(f"批量标准化失败: {str(e)}")
    
    def _is_already_normalized(self, video_info: VideoInfo, settings: dict) -> bool:
        """检查视频是否已经符合标准化要求"""
        # 检查编码器
        if video_info.video_codec != settings['video_codec'].replace('lib', ''):
            return False
        
        # 检查分辨率（允许10像素的误差）
        if abs(video_info.width - settings['width']) > 10:
            return False
        if abs(video_info.height - settings['height']) > 10:
            return False
        
        # 检查帧率（允许1fps的误差）
        if abs(video_info.fps - settings['fps']) > 1:
            return False
        
        # 检查音频编码器
        if video_info.has_audio and video_info.audio_codec != settings['audio_codec']:
            return False
        
        return True
    
    def get_optimal_settings(self, video_infos: List[VideoInfo]) -> dict:
        """根据输入视频获取最优的标准化设置"""
        if not video_infos:
            return self.default_settings
        
        # 分析所有视频的特征
        max_width = max(info.width for info in video_infos)
        max_height = max(info.height for info in video_infos)
        max_fps = max(info.fps for info in video_infos)
        
        # 选择合适的分辨率
        if max_width <= 1280 and max_height <= 720:
            width, height = 1280, 720
            bitrate = '1.5M'
        elif max_width <= 1920 and max_height <= 1080:
            width, height = 1920, 1080
            bitrate = '2M'
        else:
            width, height = 1920, 1080  # 降采样到1080p
            bitrate = '2.5M'
        
        # 选择合适的帧率
        if max_fps <= 30:
            fps = 30
        elif max_fps <= 60:
            fps = 60
        else:
            fps = 30  # 降帧率到30fps
        
        return {
            **self.default_settings,
            'width': width,
            'height': height,
            'fps': fps,
            'video_bitrate': bitrate
        }

# 全局视频标准化器实例
video_normalizer = VideoNormalizer()

# 视频合成器
class VideoComposer:
    """视频合成器 - 支持多种合成模式"""
    
    def __init__(self):
        self.temp_dir = TEMP_COMPOSITION_DIR
        self.output_dir = COMPOSITION_DIR
    
    def split_string_by_punctuations(self, s):
        """分割字符串按标点符号"""
        import re
        return [seg for seg in re.split(r'[，。！？；:,.!?;:]', s) if seg.strip()]
    
    def convert_txt_to_srt_with_audio_timing(self, txt_file: str, audio_file: str, output_srt: str) -> str:
        """
        基于音频文件生成精确时间戳的SRT字幕（参考srt_merge的实现）
        
        Args:
            txt_file: 输入的TXT文件路径
            audio_file: 对应的音频文件路径
            output_srt: 输出的SRT文件路径
        
        Returns:
            转换后的SRT文件路径
        """
        try:
            # 使用Whisper分析音频获取精确时间戳
            whisper_model = load_whisper_model()
            
            segments, info = whisper_model.transcribe(
                audio_file,
                beam_size=5,
                word_timestamps=True,  # 🎯 关键：获取每个词的时间戳
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                initial_prompt="输出中文简体的句子"
            )
            
            # 读取TXT文件内容用于校正
            with open(txt_file, 'r', encoding='utf-8') as f:
                txt_content = f.read().strip()
            
            # 基于音频时间戳生成字幕
            subtitles = []
            subtitle_index = 1
            
            for segment in segments:
                if not segment.words:
                    continue
                    
                seg_start = None
                seg_end = None
                seg_text = ""
                
                for word in segment.words:
                    if seg_start is None:
                        seg_start = word.start
                    
                    seg_end = word.end
                    seg_text += word.word
                    
                    # 在标点符号处分割字幕
                    if any(c in "，。！？；:,.!?;:, " for c in word.word):
                        if seg_text.strip():
                            subtitles.append({
                                "index": subtitle_index,
                                "start_time": seg_start,
                                "end_time": seg_end,
                                "text": seg_text.strip()
                            })
                            subtitle_index += 1
                            
                        seg_start = None
                        seg_text = ""
                
                # 处理段落结尾
                if seg_text.strip() and seg_start is not None:
                    subtitles.append({
                        "index": subtitle_index,
                        "start_time": seg_start,
                        "end_time": seg_end,
                        "text": seg_text.strip()
                    })
                    subtitle_index += 1
            
            # 🎯 关键改进：用TXT内容校正识别错误（参考srt_merge的correct函数）
            corrected_subtitles = self._correct_subtitles_with_script(subtitles, txt_content)
            
            # 写入SRT文件
            with open(output_srt, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(corrected_subtitles, 1):
                    start_time = format_srt_timestamp(subtitle["start_time"])
                    end_time = format_srt_timestamp(subtitle["end_time"])
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{subtitle['text']}\n\n")
            
            logger.info(f"基于音频时间戳+文字校正的SRT生成完成: {txt_file} + {audio_file} -> {output_srt}, 生成{len(corrected_subtitles)}条字幕")
            return output_srt
            
        except Exception as e:
            logger.error(f"基于音频时间戳的SRT生成失败: {str(e)}")
            # 回退到原来的方法
            return self.convert_txt_to_srt_fallback(txt_file, output_srt, None)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离（参考srt_merge实现）"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]
    
    def _similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度（0-1）（参考srt_merge实现）"""
        distance = self._levenshtein_distance(a.lower(), b.lower())
        max_length = max(len(a), len(b))
        return 1 - (distance / max_length) if max_length > 0 else 1.0
    
    def _correct_subtitles_with_script(self, whisper_subtitles: list, script_content: str) -> list:
        """
        用脚本内容校正Whisper识别的字幕（参考srt_merge的correct函数）
        
        Args:
            whisper_subtitles: Whisper识别的字幕列表（包含时间戳）
            script_content: 正确的脚本内容
        
        Returns:
            校正后的字幕列表
        """
        # 分割脚本内容
        script_lines = self.split_string_by_punctuations(script_content)
        script_lines = [line.strip() for line in script_lines if line.strip()]
        
        corrected_subtitles = []
        script_index = 0
        subtitle_index = 0
        
        logger.info(f"开始字幕校正: Whisper识别{len(whisper_subtitles)}条，脚本{len(script_lines)}行")
        
        while script_index < len(script_lines) and subtitle_index < len(whisper_subtitles):
            script_line = script_lines[script_index].strip()
            subtitle_item = whisper_subtitles[subtitle_index]
            subtitle_text = subtitle_item["text"].strip()
            
            # 如果完全匹配，直接使用
            if script_line == subtitle_text:
                corrected_subtitles.append({
                    "start_time": subtitle_item["start_time"],
                    "end_time": subtitle_item["end_time"],
                    "text": script_line
                })
                script_index += 1
                subtitle_index += 1
                logger.debug(f"完全匹配: {script_line}")
            else:
                # 尝试合并多个字幕段来匹配脚本行
                combined_text = subtitle_text
                start_time = subtitle_item["start_time"]
                end_time = subtitle_item["end_time"]
                next_subtitle_index = subtitle_index + 1
                
                # 尝试合并后续字幕段
                while next_subtitle_index < len(whisper_subtitles):
                    next_subtitle = whisper_subtitles[next_subtitle_index]
                    next_text = next_subtitle["text"].strip()
                    
                    # 如果合并后相似度更高，则合并
                    if self._similarity(script_line, combined_text + " " + next_text) > self._similarity(script_line, combined_text):
                        combined_text += " " + next_text
                        end_time = next_subtitle["end_time"]
                        next_subtitle_index += 1
                    else:
                        break
                
                # 如果相似度足够高（>0.8），使用脚本文字替换识别文字
                similarity_score = self._similarity(script_line, combined_text)
                if similarity_score > 0.8:
                    logger.info(f"校正字幕 (相似度:{similarity_score:.2f}): '{combined_text}' -> '{script_line}'")
                else:
                    logger.warning(f"相似度过低 (相似度:{similarity_score:.2f}): '{combined_text}' vs '{script_line}'，强制使用脚本文字")
                
                # 🎯 关键：无论相似度如何，都使用正确的脚本文字
                corrected_subtitles.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": script_line  # 用正确的脚本文字替换识别错误的文字
                })
                
                script_index += 1
                subtitle_index = next_subtitle_index
        
        # 处理剩余的脚本行
        while script_index < len(script_lines):
            logger.warning(f"额外的脚本行: {script_lines[script_index]}")
            if subtitle_index < len(whisper_subtitles):
                # 使用剩余字幕的时间戳
                subtitle_item = whisper_subtitles[subtitle_index]
                corrected_subtitles.append({
                    "start_time": subtitle_item["start_time"],
                    "end_time": subtitle_item["end_time"],
                    "text": script_lines[script_index]
                })
                subtitle_index += 1
            else:
                # 没有更多时间戳，使用默认时间
                last_end_time = corrected_subtitles[-1]["end_time"] if corrected_subtitles else 0.0
                corrected_subtitles.append({
                    "start_time": last_end_time,
                    "end_time": last_end_time + 3.0,  # 默认3秒
                    "text": script_lines[script_index]
                })
            script_index += 1
        
        logger.info(f"字幕校正完成: 生成{len(corrected_subtitles)}条校正后的字幕")
        return corrected_subtitles
    
    def convert_txt_to_srt_fallback(self, txt_file: str, output_srt: str, target_duration: float = None, default_duration: float = 3.0) -> str:
        """
        将TXT文件转换为SRT格式
        
        Args:
            txt_file: 输入的TXT文件路径
            output_srt: 输出的SRT文件路径
            target_duration: 目标时长（通常是音频时长），用于优化时间轴分配
            default_duration: 每行字幕的默认显示时长（秒）
        
        Returns:
            转换后的SRT文件路径
        """
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if not lines:
                raise ValueError("TXT文件为空")
            
            subtitles = []
            
            # 预处理：分割所有文本段
            all_segments = []
            for line in lines:
                segments = self.split_string_by_punctuations(line)
                if not segments:
                    segments = [line]
                
                for segment in segments:
                    if segment.strip():
                        all_segments.append(segment.strip())
            
            if not all_segments:
                raise ValueError("没有有效的字幕内容")
            
            # 如果有目标时长信息（通常是音频时长），优化时间分配
            if target_duration and target_duration > 0:
                # 计算每个字幕的理想时长
                total_chars = sum(len(seg) for seg in all_segments)
                if total_chars > 0:
                    # 基于字符数量和目标时长分配时间
                    time_per_char = min(target_duration * 0.9 / total_chars, 0.3)  # 最多90%的目标时长，每字符最多0.3秒
                    
                    # 添加1秒延迟以补偿音频编码和处理延迟
                    subtitle_delay = 1.0
                    current_time = subtitle_delay
                    
                    for segment in all_segments:
                        # 根据字符数量计算时长，最少1.5秒，最多6秒
                        duration = max(1.5, min(6.0, len(segment) * time_per_char + 0.5))
                        
                        subtitles.append({
                            "start_time": current_time,
                            "end_time": current_time + duration,
                            "text": segment
                        })
                        
                        current_time += duration
                        
                        # 如果超过目标时长，调整最后一个字幕的结束时间
                        if current_time >= target_duration:
                            if subtitles:
                                subtitles[-1]["end_time"] = target_duration
                            break
                else:
                    # 平均分配时间，添加1秒延迟
                    subtitle_delay = 1.0
                    available_duration = max(1.0, target_duration - subtitle_delay)  # 减去延迟后的可用时长
                    duration_per_subtitle = available_duration / len(all_segments)
                    
                    for i, segment in enumerate(all_segments):
                        start_time = subtitle_delay + i * duration_per_subtitle
                        end_time = min(subtitle_delay + (i + 1) * duration_per_subtitle, target_duration)
                        
                        subtitles.append({
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": segment
                        })
            else:
                # 没有目标时长信息，使用默认方式，同样添加1秒延迟
                subtitle_delay = 1.0
                current_time = subtitle_delay
                
                for segment in all_segments:
                    duration = max(default_duration, len(segment) * 0.15)
                    
                    subtitles.append({
                        "start_time": current_time,
                        "end_time": current_time + duration,
                        "text": segment
                    })
                    
                    current_time += duration
            
            # 写入SRT文件
            with open(output_srt, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(subtitles, 1):
                    start_time = format_srt_timestamp(subtitle["start_time"])
                    end_time = format_srt_timestamp(subtitle["end_time"])
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{subtitle['text']}\n\n")
            
            logger.info(f"TXT转SRT完成: {txt_file} -> {output_srt}, 生成{len(subtitles)}条字幕")
            return output_srt
            
        except Exception as e:
            logger.error(f"TXT转SRT失败: {str(e)}")
            raise
    
    async def concat_videos(self, video_files: List[str], output_file: str,
                          task_id: str, status_obj) -> str:
        """视频拼接合成"""
        try:
            status_obj.message = "准备视频拼接..."
            status_obj.progress = 10
            
            # 验证输入文件
            if len(video_files) < 2:
                raise InputValidationError("至少需要2个视频文件进行拼接")
            
            # 准备所有输入文件（下载在线视频或准备本地文件）
            prepared_video_files = []
            video_infos = []
            
            for i, video_file in enumerate(video_files):
                if is_local_file(video_file):
                    # 本地文件，直接使用
                    prepared_file = video_file
                    if video_file.startswith('file://'):
                        prepared_file = video_file[7:]  # 移除file://前缀
                    prepared_file = os.path.abspath(prepared_file)
                    logger.info(f"使用本地视频文件: {prepared_file}")
                else:
                    # 在线视频，需要下载
                    status_obj.message = f"下载视频 {i+1}/{len(video_files)}..."
                    temp_video_dir = os.path.join(self.temp_dir, f"{task_id}_video_{i}")
                    os.makedirs(temp_video_dir, exist_ok=True)
                    status_obj.temp_files.append(temp_video_dir)
                    
                    video_id = hashlib.md5(video_file.encode()).hexdigest()[:8]
                    prepared_file = await download_video_for_keyframes(video_file, video_id, temp_video_dir)
                    logger.info(f"下载在线视频完成: {video_file} -> {prepared_file}")
                
                prepared_video_files.append(prepared_file)
                
                # 验证视频文件
                info = await video_validator.validate_video_file(prepared_file)
                video_infos.append(info)
            
            # 更新video_files为准备好的文件列表
            video_files = prepared_video_files
            
            # 检查兼容性
            compatibility = video_validator.check_compatibility(video_infos)
            
            status_obj.progress = 20
            
            # 如果需要标准化
            if compatibility["needs_normalization"]:
                status_obj.message = "视频参数不一致，正在标准化..."
                logger.info(f"视频需要标准化: {compatibility['issues']}")
                
                # 创建临时目录
                temp_normalized_dir = os.path.join(self.temp_dir, f"{task_id}_normalized")
                os.makedirs(temp_normalized_dir, exist_ok=True)
                
                # 获取最优标准化设置
                norm_settings = video_normalizer.get_optimal_settings(video_infos)
                
                # 标准化所有视频
                normalized_files = await video_normalizer.normalize_multiple_videos(
                    video_files, temp_normalized_dir, norm_settings, task_id, status_obj
                )
                
                # 使用标准化后的文件
                video_files = normalized_files
                status_obj.temp_files.extend(normalized_files)
            
            status_obj.progress = 60
            status_obj.message = "正在拼接视频..."
            
            # 创建concat文件列表
            concat_file = os.path.join(self.temp_dir, f"{task_id}_concat.txt")
            with open(concat_file, 'w', encoding='utf-8') as f:
                for video_file in video_files:
                    # 使用绝对路径并转义特殊字符
                    abs_path = os.path.abspath(video_file)
                    f.write(f"file '{abs_path}'\n")
            
            status_obj.temp_files.append(concat_file)
            
            # 构建FFmpeg拼接命令
            builder = FFmpegCommandBuilder()
            builder.add_global_option('-f', 'concat')
            builder.add_global_option('-safe', '0')
            builder.add_input(concat_file)
            
            # 输出选项 - 尽量避免重新编码
            output_options = {
                'c': 'copy',  # 复制流，避免重新编码
                'avoid_negative_ts': 'make_zero'  # 处理时间戳问题
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建并执行命令
            cmd = builder.build()
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg拼接命令验证失败")
            
            # 执行拼接
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"视频拼接失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "视频拼接完成"
            
            logger.info(f"视频拼接成功: {len(video_files)}个文件 -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"视频拼接失败: {str(e)}")
            # 清理输出文件
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"视频拼接失败: {str(e)}")
    
    async def extract_video_segment(self, input_file: str, output_file: str,
                                  start_time: float, end_time: float = None,
                                  task_id: str = None, status_obj = None) -> str:
        """提取视频片段"""
        try:
            # 验证输入文件
            video_info = await video_validator.validate_video_file(input_file)
            
            # 验证时间范围
            if start_time < 0:
                raise InputValidationError("开始时间不能为负数")
            
            if start_time >= video_info.duration:
                raise InputValidationError(f"开始时间 ({start_time}s) 超过视频长度 ({video_info.duration}s)")
            
            if end_time is not None:
                if end_time <= start_time:
                    raise InputValidationError("结束时间必须大于开始时间")
                if end_time > video_info.duration:
                    logger.warning(f"结束时间 ({end_time}s) 超过视频长度，将截断到 {video_info.duration}s")
                    end_time = video_info.duration
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_global_option('-ss', str(start_time))  # 开始时间
            
            if end_time is not None:
                duration = end_time - start_time
                builder.add_global_option('-t', str(duration))  # 持续时间
            
            builder.add_input(input_file)
            
            # 输出选项 - 尽量避免重新编码
            output_options = {
                'c': 'copy',
                'avoid_negative_ts': 'make_zero'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建并执行命令
            cmd = builder.build()
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg片段提取命令验证失败")
            
            if status_obj:
                status_obj.message = f"正在提取视频片段: {start_time}s - {end_time or '结尾'}s"
                await ffmpeg_executor.execute_command_with_progress(
                    cmd, task_id or "extract", status_obj
                )
            else:
                await ffmpeg_executor.execute_command(cmd, task_id or "extract")
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"视频片段提取失败，输出文件不存在: {output_file}")
            
            logger.info(f"视频片段提取成功: {input_file} [{start_time}s-{end_time or '结尾'}s] -> {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"视频片段提取失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"视频片段提取失败: {str(e)}")
    
    async def extract_and_concat_segments(self, video_inputs: List[VideoInput], 
                                        output_file: str, task_id: str, 
                                        status_obj) -> str:
        """提取多个片段并拼接"""
        try:
            status_obj.message = "准备提取视频片段..."
            status_obj.progress = 5
            
            if not video_inputs:
                raise InputValidationError("没有提供视频输入")
            
            # 创建临时目录存储片段
            temp_segments_dir = os.path.join(self.temp_dir, f"{task_id}_segments")
            os.makedirs(temp_segments_dir, exist_ok=True)
            
            segment_files = []
            total_inputs = len(video_inputs)
            
            # 提取所有片段
            for i, video_input in enumerate(video_inputs):
                segment_file = os.path.join(temp_segments_dir, f"segment_{i:03d}.mp4")
                
                # 更新进度
                progress = 5 + int((i / total_inputs) * 60)  # 5-65%用于片段提取
                status_obj.progress = progress
                status_obj.message = f"提取片段 {i+1}/{total_inputs}"
                
                # 提取片段
                await self.extract_video_segment(
                    video_input.video_url,
                    segment_file,
                    video_input.start_time or 0.0,
                    video_input.end_time,
                    f"{task_id}_seg_{i}",
                    status_obj
                )
                
                segment_files.append(segment_file)
                status_obj.temp_files.append(segment_file)
            
            status_obj.progress = 70
            status_obj.message = "正在拼接所有片段..."
            
            # 拼接所有片段
            result = await self.concat_videos(segment_files, output_file, task_id, status_obj)
            
            logger.info(f"片段提取和拼接完成: {len(segment_files)}个片段 -> {output_file}")
            return result
            
        except Exception as e:
            logger.error(f"片段提取和拼接失败: {str(e)}")
            raise ProcessingError(f"片段提取和拼接失败: {str(e)}")
    
    async def compose_audio_video_subtitle(self, video_file: str, audio_file: str,
                                         subtitle_file: str, output_file: str,
                                         task_id: str, status_obj,
                                         audio_offset: float = 0.0) -> str:
        """音频视频字幕三合一合成"""
        try:
            status_obj.message = "开始音频视频字幕合成..."
            status_obj.progress = 5
            
            # 验证输入文件
            if not video_file or not audio_file:
                raise InputValidationError("必须提供视频文件和音频文件")
            
            # 验证视频文件
            video_info = await video_validator.validate_video_file(video_file)
            status_obj.progress = 10
            
            # 验证音频文件
            audio_info = await self._validate_audio_file(audio_file)
            status_obj.progress = 15
            
            # 获取视频和音频时长信息
            video_duration = video_info.duration
            audio_duration = audio_info['duration']
            
            logger.info(f"视频时长: {video_duration:.2f}s, 音频时长: {audio_duration:.2f}s")
            
            # 计算时长差异
            duration_diff = abs(video_duration - audio_duration)
            if duration_diff > 1.0:  # 如果差异超过1秒
                logger.warning(f"音视频时长差异较大: {duration_diff:.2f}s")
                status_obj.message = f"检测到音视频时长差异: {duration_diff:.2f}s，将进行同步处理"
            
            # 处理字幕文件（如果提供）
            processed_subtitle_file = subtitle_file
            temp_srt_file = None
            if subtitle_file:
                await self._validate_subtitle_file(subtitle_file)
                
                # 如果是TXT格式，转换为SRT
                ext = os.path.splitext(subtitle_file)[1].lower()
                if ext == '.txt':
                    temp_srt_file = os.path.join(
                        os.path.dirname(output_file),
                        f"temp_{task_id}.srt"
                    )
                    # 使用基于音频时间戳的精确方法（参考srt_merge）
                    try:
                        processed_subtitle_file = self.convert_txt_to_srt_with_audio_timing(
                            subtitle_file, audio_file, temp_srt_file
                        )
                        status_obj.message = "TXT字幕已转换为SRT格式，使用音频时间戳精确对齐"
                        logger.info(f"使用音频时间戳方法转换完成: {subtitle_file} -> {processed_subtitle_file}")
                    except Exception as e:
                        logger.warning(f"音频时间戳方法失败，回退到传统方法: {str(e)}")
                        processed_subtitle_file = self.convert_txt_to_srt_fallback(
                            subtitle_file, temp_srt_file, audio_duration
                        )
                        status_obj.message = "TXT字幕已转换为SRT格式，使用传统时间分配"
                        logger.info(f"使用传统方法转换完成: {subtitle_file} -> {processed_subtitle_file}")
            status_obj.progress = 20
            
            status_obj.message = "准备合成参数..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加视频输入
            builder.add_input(video_file)
            
            # 添加音频输入（可能有偏移）
            if audio_offset > 0:
                builder.add_input(audio_file, {'itsoffset': audio_offset})
            else:
                builder.add_input(audio_file)
            
            # 暂时简化处理逻辑，先确保基本功能正常
            video_filters = []
            
            # 记录时长差异但暂不处理，确保基本功能先正常工作
            if abs(video_duration - audio_duration) > 1.0:
                logger.info(f"检测到时长差异: 视频{video_duration:.2f}s, 音频{audio_duration:.2f}s")
                logger.info("将使用-shortest选项确保同步")
            
            logger.info(f"视频时长: {video_duration:.2f}s, 音频时长: {audio_duration:.2f}s")
            
            # 简化命令构建，参考可用代码的方式
            # 直接构建FFmpeg命令，避免复杂的构建器
            cmd = ["ffmpeg", "-y"]
            
            # 添加输入文件
            cmd.extend(["-i", video_file])
            cmd.extend(["-i", audio_file])
            
            # 如果有字幕文件，添加字幕滤镜
            if processed_subtitle_file:
                # 转义字幕文件路径中的特殊字符
                escaped_subtitle = processed_subtitle_file.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                
                # 根据系统选择合适的字体
                import platform
                system = platform.system()
                
                # 简化字体选择，使用通用字体
                if system == 'Darwin':
                    font_name = 'Arial Unicode MS' if os.path.exists('/Library/Fonts/Arial Unicode.ttf') else 'Arial'
                elif system == 'Linux':
                    font_name = 'DejaVu Sans'
                elif system == 'Windows':
                    font_name = 'Arial'
                else:
                    font_name = 'Arial'
                
                # 使用正确的ASS颜色格式，参考可用代码
                subtitle_filter = f"subtitles='{escaped_subtitle}':force_style='FontName={font_name},FontSize=36,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'"
                
                # 添加视频滤镜
                cmd.extend(["-vf", subtitle_filter])
                
                logger.info(f"使用字体: {font_name} 显示字幕")
            
            # 添加编码选项
            cmd.extend([
                "-c:v", "libx264",    # 视频编码器
                "-c:a", "aac",        # 音频编码器
                "-b:v", "2M",         # 视频比特率
                "-b:a", "128k",       # 音频比特率
                "-ar", "48000",       # 音频采样率
                "-shortest"           # 以最短流为准
            ])
            
            # 添加输出文件
            cmd.append(output_file)
            
            logger.info(f"FFmpeg命令: {' '.join(cmd)}")
            
            status_obj.progress = 30
            status_obj.message = "正在合成音频视频字幕..."
            
            # 执行合成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"音频视频字幕合成失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "音频视频字幕合成完成"
            
            logger.info(f"音频视频字幕合成成功: {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s, 包含音频: {output_info.has_audio}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"音频视频字幕合成失败: {str(e)}")
            # 清理输出文件
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"音频视频字幕合成失败: {str(e)}")
        finally:
            # 清理临时SRT文件
            if temp_srt_file and os.path.exists(temp_srt_file):
                try:
                    os.remove(temp_srt_file)
                    logger.info(f"清理临时SRT文件: {temp_srt_file}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时SRT文件失败: {cleanup_error}")
    
    async def _validate_audio_file(self, audio_file: str) -> dict:
        """验证音频文件"""
        try:
            # 使用ffprobe获取音频信息
            info_dict = await ffmpeg_executor.get_video_info(audio_file)
            
            # 检查是否包含音频流
            audio_streams = [s for s in info_dict.get('streams', []) 
                           if s.get('codec_type') == 'audio']
            
            if not audio_streams:
                raise InputValidationError(f"文件不包含音频流: {audio_file}")
            
            audio_stream = audio_streams[0]
            duration = float(info_dict.get('format', {}).get('duration', 0))
            
            # 检查音频时长
            if duration <= 0:
                raise InputValidationError(f"无效的音频时长: {duration}")
            
            if duration > 10800:  # 3小时限制
                raise ResourceLimitError(f"音频时长过长: {duration/60:.1f}分钟")
            
            logger.info(f"音频验证通过: {audio_file} - {duration:.1f}s, "
                       f"编码器: {audio_stream.get('codec_name', 'unknown')}")
            
            return {
                'duration': duration,
                'codec': audio_stream.get('codec_name', ''),
                'sample_rate': audio_stream.get('sample_rate', 0),
                'channels': audio_stream.get('channels', 0)
            }
            
        except Exception as e:
            if isinstance(e, (InputValidationError, ResourceLimitError)):
                raise
            raise InputValidationError(f"音频文件验证失败 {audio_file}: {str(e)}")
    
    async def _validate_subtitle_file(self, subtitle_file: str):
        """验证字幕文件"""
        try:
            if not os.path.exists(subtitle_file):
                raise InputValidationError(f"字幕文件不存在: {subtitle_file}")
            
            # 检查文件扩展名 - 添加 .txt 支持
            ext = os.path.splitext(subtitle_file)[1].lower()
            if ext not in ['.srt', '.ass', '.ssa', '.vtt', '.txt']:
                raise InputValidationError(f"不支持的字幕格式: {ext}")
            
            # 检查文件大小
            file_size = os.path.getsize(subtitle_file)
            if file_size > 10 * 1024 * 1024:  # 10MB限制
                raise ResourceLimitError(f"字幕文件过大: {file_size/1024/1024:.1f}MB")
            
            # 验证不同格式
            if ext == '.srt':
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # 读取前1000字符
                    if not re.search(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', content):
                        logger.warning(f"字幕文件格式可能不正确: {subtitle_file}")
            elif ext == '.txt':
                # 验证txt文件是否为有效的文本文件
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    content = f.read(100)  # 读取前100字符检查
                    if not content.strip():
                        raise InputValidationError(f"TXT字幕文件为空: {subtitle_file}")
            
            logger.info(f"字幕验证通过: {subtitle_file} - {ext}格式, {file_size}字节")
            
        except Exception as e:
            if isinstance(e, (InputValidationError, ResourceLimitError)):
                raise
            raise InputValidationError(f"字幕文件验证失败 {subtitle_file}: {str(e)}")
    
    async def burn_subtitles(self, video_file: str, subtitle_file: str,
                           output_file: str, task_id: str, status_obj,
                           subtitle_style: dict = None) -> str:
        """将字幕烧录到视频中"""
        try:
            status_obj.message = "开始字幕烧录..."
            status_obj.progress = 10
            
            # 验证输入文件
            video_info = await video_validator.validate_video_file(video_file)
            await self._validate_subtitle_file(subtitle_file)
            
            status_obj.progress = 20
            
            # 默认字幕样式
            default_style = {
                'font_name': 'Arial',
                'font_size': 24,
                'font_color': 'white',
                'outline_color': 'black',
                'outline_width': 2,
                'shadow_offset': 1,
                'margin_v': 30,  # 底部边距
                'alignment': 2   # 底部居中
            }
            
            # 合并用户样式
            style = {**default_style, **(subtitle_style or {})}
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(video_file)
            
            # 构建字幕滤镜
            subtitle_filter = self._build_subtitle_filter(subtitle_file, style)
            builder.add_filter(f"[0:v]{subtitle_filter}[v_with_sub]")
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制音频流
                'b:v': '2M',
                'map': '[v_with_sub]',
                'map': '[0:a]' if video_info.has_audio else None
            }
            
            # 移除None值
            output_options = {k: v for k, v in output_options.items() if v is not None}
            
            builder.add_output(output_file, output_options)
            
            # 构建并验证命令
            cmd = builder.build()
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg字幕烧录命令验证失败")
            
            status_obj.progress = 30
            status_obj.message = "正在烧录字幕..."
            
            # 执行烧录
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"字幕烧录失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "字幕烧录完成"
            
            logger.info(f"字幕烧录成功: {video_file} + {subtitle_file} -> {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"字幕烧录失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"字幕烧录失败: {str(e)}")
    
    def _build_subtitle_filter(self, subtitle_file: str, style: dict) -> str:
        """构建字幕滤镜字符串"""
        # 转义文件路径
        escaped_path = subtitle_file.replace('\\', '\\\\').replace(':', '\\:')
        
        # 检查字幕格式
        ext = os.path.splitext(subtitle_file)[1].lower()
        
        if ext == '.srt':
            # SRT格式使用subtitles滤镜
            filter_str = f"subtitles='{escaped_path}'"
            
            # 添加样式参数
            style_params = []
            if style.get('font_name'):
                style_params.append(f"force_style='FontName={style['font_name']}")
            if style.get('font_size'):
                style_params.append(f"FontSize={style['font_size']}")
            if style.get('font_color'):
                style_params.append(f"PrimaryColour=&H{self._color_to_hex(style['font_color'])}")
            if style.get('outline_color'):
                style_params.append(f"OutlineColour=&H{self._color_to_hex(style['outline_color'])}")
            if style.get('outline_width'):
                style_params.append(f"Outline={style['outline_width']}")
            if style.get('margin_v'):
                style_params.append(f"MarginV={style['margin_v']}")
            if style.get('alignment'):
                style_params.append(f"Alignment={style['alignment']}")
            
            if style_params:
                style_str = ','.join(style_params) + "'"
                filter_str += f":force_style='{style_str}'"
                
        elif ext in ['.ass', '.ssa']:
            # ASS/SSA格式使用ass滤镜
            filter_str = f"ass='{escaped_path}'"
        else:
            # 其他格式使用subtitles滤镜
            filter_str = f"subtitles='{escaped_path}'"
        
        return filter_str
    
    def _color_to_hex(self, color: str) -> str:
        """将颜色名称转换为十六进制"""
        color_map = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': 'FF0000',
            'green': '00FF00',
            'blue': '0000FF',
            'yellow': 'FFFF00',
            'cyan': '00FFFF',
            'magenta': 'FF00FF'
        }
        
        if color.lower() in color_map:
            return color_map[color.lower()]
        elif color.startswith('#'):
            return color[1:]  # 移除#号
        else:
            return 'FFFFFF'  # 默认白色
    
    async def picture_in_picture(self, main_video: str, overlay_video: str,
                               output_file: str, task_id: str, status_obj,
                               position: Position = None) -> str:
        """画中画合成"""
        try:
            status_obj.message = "开始画中画合成..."
            status_obj.progress = 5
            
            # 验证输入文件
            if not main_video or not overlay_video:
                raise InputValidationError("必须提供主视频和叠加视频文件")
            
            # 验证视频文件
            main_info = await video_validator.validate_video_file(main_video)
            overlay_info = await video_validator.validate_video_file(overlay_video)
            
            status_obj.progress = 15
            status_obj.message = "计算画中画布局..."
            
            # 计算画中画布局
            layout = self._calculate_pip_layout(main_info, overlay_info, position)
            
            status_obj.progress = 25
            status_obj.message = "构建FFmpeg命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加主视频输入
            builder.add_input(main_video)
            
            # 添加叠加视频输入
            builder.add_input(overlay_video)
            
            # 构建滤镜链
            filters = []
            
            # 缩放叠加视频
            if layout['needs_scaling']:
                scale_filter = f"[1:v]scale={layout['overlay_width']}:{layout['overlay_height']}[scaled]"
                filters.append(scale_filter)
                overlay_stream = "[scaled]"
            else:
                overlay_stream = "[1:v]"
            
            # 画中画叠加滤镜
            overlay_filter = f"[0:v]{overlay_stream}overlay={layout['x']}:{layout['y']}"
            if layout['opacity'] < 1.0:
                # 添加透明度
                opacity_filter = f"{overlay_stream}format=yuva420p,colorchannelmixer=aa={layout['opacity']}[overlay_alpha]"
                filters.append(opacity_filter)
                overlay_filter = f"[0:v][overlay_alpha]overlay={layout['x']}:{layout['y']}"
            
            filters.append(overlay_filter + "[pip_output]")
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制主视频的音频
                'b:v': '2M'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 手动添加映射选项
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[pip_output]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a')  # 使用主视频的音频
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg画中画命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在执行画中画合成..."
            
            # 执行合成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"画中画合成失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "画中画合成完成"
            
            logger.info(f"画中画合成成功: {main_video} + {overlay_video} -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"画中画合成失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"画中画合成失败: {str(e)}")
    
    def _calculate_pip_layout(self, main_info: VideoInfo, overlay_info: VideoInfo, 
                            position: Position = None) -> dict:
        """计算画中画布局"""
        # 默认位置设置
        if position is None:
            position = Position(x=0, y=0, width=None, height=None, opacity=1.0)
        
        main_width = main_info.width
        main_height = main_info.height
        overlay_width = overlay_info.width
        overlay_height = overlay_info.height
        
        # 计算叠加视频的目标尺寸
        if position.width and position.height:
            # 用户指定了具体尺寸
            target_width = position.width
            target_height = position.height
        elif position.width:
            # 只指定了宽度，按比例计算高度
            target_width = position.width
            target_height = int(target_width * overlay_height / overlay_width)
        elif position.height:
            # 只指定了高度，按比例计算宽度
            target_height = position.height
            target_width = int(target_height * overlay_width / overlay_height)
        else:
            # 默认为主视频的1/4大小
            target_width = main_width // 4
            target_height = int(target_width * overlay_height / overlay_width)
        
        # 确保尺寸不超过主视频
        if target_width > main_width:
            target_width = main_width
            target_height = int(target_width * overlay_height / overlay_width)
        
        if target_height > main_height:
            target_height = main_height
            target_width = int(target_height * overlay_width / overlay_height)
        
        # 计算位置
        if position.x == 0 and position.y == 0 and not (position.width or position.height):
            # 默认位置：右上角
            x = main_width - target_width - 20  # 距离右边20像素
            y = 20  # 距离顶部20像素
        else:
            x = position.x
            y = position.y
        
        # 确保位置在主视频范围内
        x = max(0, min(x, main_width - target_width))
        y = max(0, min(y, main_height - target_height))
        
        # 检查是否需要缩放
        needs_scaling = (target_width != overlay_width or target_height != overlay_height)
        
        return {
            'x': x,
            'y': y,
            'overlay_width': target_width,
            'overlay_height': target_height,
            'needs_scaling': needs_scaling,
            'opacity': position.opacity
        }
    
    def get_preset_positions(self, main_width: int, main_height: int, 
                           overlay_width: int, overlay_height: int) -> dict:
        """获取预设位置"""
        margin = 20  # 边距
        
        # 计算叠加视频的默认尺寸（主视频的1/4）
        default_width = main_width // 4
        default_height = int(default_width * overlay_height / overlay_width)
        
        return {
            'top_left': Position(x=margin, y=margin, 
                               width=default_width, height=default_height),
            'top_right': Position(x=main_width - default_width - margin, y=margin,
                                width=default_width, height=default_height),
            'bottom_left': Position(x=margin, y=main_height - default_height - margin,
                                  width=default_width, height=default_height),
            'bottom_right': Position(x=main_width - default_width - margin, 
                                   y=main_height - default_height - margin,
                                   width=default_width, height=default_height),
            'center': Position(x=(main_width - default_width) // 2,
                             y=(main_height - default_height) // 2,
                             width=default_width, height=default_height)
        }
    
    async def multi_layer_overlay(self, main_video: str, overlay_videos: List[dict],
                                 output_file: str, task_id: str, status_obj) -> str:
        """多层视频叠加"""
        try:
            status_obj.message = "开始多层视频叠加..."
            status_obj.progress = 5
            
            # 验证输入
            if not main_video or not overlay_videos:
                raise InputValidationError("必须提供主视频和至少一个叠加视频")
            
            if len(overlay_videos) > 5:
                raise InputValidationError("最多支持5个叠加视频")
            
            # 验证主视频
            main_info = await video_validator.validate_video_file(main_video)
            status_obj.progress = 10
            
            # 验证所有叠加视频
            overlay_infos = []
            for i, overlay_data in enumerate(overlay_videos):
                overlay_file = overlay_data.get('video_url')
                if not overlay_file:
                    raise InputValidationError(f"叠加视频 {i+1} 缺少video_url")
                
                overlay_info = await video_validator.validate_video_file(overlay_file)
                overlay_infos.append({
                    'info': overlay_info,
                    'file': overlay_file,
                    'position': overlay_data.get('position', Position()),
                    'z_index': overlay_data.get('z_index', i + 1)
                })
            
            # 按z_index排序
            overlay_infos.sort(key=lambda x: x['z_index'])
            
            status_obj.progress = 20
            status_obj.message = "计算多层布局..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加主视频输入
            builder.add_input(main_video)
            
            # 添加所有叠加视频输入
            for overlay_data in overlay_infos:
                builder.add_input(overlay_data['file'])
            
            # 构建复杂的滤镜链
            filters = []
            current_stream = "[0:v]"
            
            for i, overlay_data in enumerate(overlay_infos):
                overlay_info = overlay_data['info']
                position = overlay_data['position']
                
                # 计算布局
                layout = self._calculate_pip_layout(main_info, overlay_info, position)
                
                # 缩放叠加视频（如果需要）
                input_index = i + 1
                if layout['needs_scaling']:
                    scale_filter = f"[{input_index}:v]scale={layout['overlay_width']}:{layout['overlay_height']}[scaled_{i}]"
                    filters.append(scale_filter)
                    overlay_stream = f"[scaled_{i}]"
                else:
                    overlay_stream = f"[{input_index}:v]"
                
                # 处理透明度
                if layout['opacity'] < 1.0:
                    opacity_filter = f"{overlay_stream}format=yuva420p,colorchannelmixer=aa={layout['opacity']}[overlay_{i}]"
                    filters.append(opacity_filter)
                    overlay_stream = f"[overlay_{i}]"
                
                # 叠加滤镜
                if i == len(overlay_infos) - 1:
                    # 最后一层，输出到最终流
                    overlay_filter = f"{current_stream}{overlay_stream}overlay={layout['x']}:{layout['y']}[final_output]"
                else:
                    # 中间层，输出到临时流
                    overlay_filter = f"{current_stream}{overlay_stream}overlay={layout['x']}:{layout['y']}[layer_{i}]"
                    current_stream = f"[layer_{i}]"
                
                filters.append(overlay_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制主视频的音频
                'b:v': '3M'     # 多层叠加需要更高比特率
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 手动添加映射选项
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[final_output]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a')  # 使用主视频的音频
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg多层叠加命令验证失败")
            
            status_obj.progress = 30
            status_obj.message = f"正在执行多层叠加 ({len(overlay_videos)}层)..."
            
            # 执行合成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"多层叠加失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "多层视频叠加完成"
            
            logger.info(f"多层叠加成功: {main_video} + {len(overlay_videos)}层 -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"多层叠加失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"多层叠加失败: {str(e)}")
    
    def _synchronize_overlay_durations(self, main_duration: float, 
                                     overlay_infos: List[dict]) -> List[dict]:
        """同步叠加视频的时长"""
        synchronized_overlays = []
        
        for overlay_data in overlay_infos:
            overlay_info = overlay_data['info']
            overlay_duration = overlay_info.info.duration
            
            # 处理时长不匹配的情况
            if overlay_duration < main_duration:
                # 叠加视频较短，可以循环播放或延长
                overlay_data['sync_mode'] = 'loop'
                overlay_data['loop_count'] = int(main_duration / overlay_duration) + 1
            elif overlay_duration > main_duration:
                # 叠加视频较长，截断到主视频长度
                overlay_data['sync_mode'] = 'trim'
                overlay_data['trim_duration'] = main_duration
            else:
                # 时长匹配
                overlay_data['sync_mode'] = 'none'
            
            synchronized_overlays.append(overlay_data)
        
        return synchronized_overlays
    
    async def side_by_side_videos(self, videos: List[str], output_file: str,
                                 task_id: str, status_obj, layout: str = "horizontal") -> str:
        """并排视频显示"""
        try:
            status_obj.message = "开始并排视频合成..."
            status_obj.progress = 5
            
            # 验证输入
            if len(videos) < 2:
                raise InputValidationError("并排显示至少需要2个视频")
            
            if len(videos) > 4:
                raise InputValidationError("最多支持4个视频并排显示")
            
            # 验证所有视频文件
            video_infos = []
            for i, video_file in enumerate(videos):
                info = await video_validator.validate_video_file(video_file)
                video_infos.append(info)
                status_obj.progress = 5 + (i + 1) * 5
            
            status_obj.progress = 25
            status_obj.message = "计算网格布局..."
            
            # 计算网格布局
            grid_layout = self._calculate_grid_layout(video_infos, layout)
            
            status_obj.progress = 35
            status_obj.message = "构建FFmpeg命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有视频输入
            for video_file in videos:
                builder.add_input(video_file)
            
            # 构建复杂的滤镜链
            filters = []
            
            # 缩放所有视频到统一尺寸，保持宽高比
            for i, video_info in enumerate(video_infos):
                # 使用 scale 保持宽高比，然后用 pad 填充到目标尺寸
                scale_filter = f"[{i}:v]scale={grid_layout['cell_width']}:{grid_layout['cell_height']}:force_original_aspect_ratio=decrease[scaled_temp_{i}]"
                pad_filter = f"[scaled_temp_{i}]pad={grid_layout['cell_width']}:{grid_layout['cell_height']}:(ow-iw)/2:(oh-ih)/2:color=black[scaled_{i}]"
                filters.extend([scale_filter, pad_filter])
            
            # 根据布局类型构建合成滤镜
            logger.info(f"布局类型: {layout}, 视频数量: {len(videos)}")
            
            if layout == "horizontal" and len(videos) == 2:
                # 左右并排
                logger.info("使用水平并排布局")
                hstack_filter = "[scaled_0][scaled_1]hstack=inputs=2[output]"
                filters.append(hstack_filter)
            elif layout == "vertical" and len(videos) == 2:
                # 上下排列
                logger.info("使用垂直并排布局")
                vstack_filter = "[scaled_0][scaled_1]vstack=inputs=2[output]"
                filters.append(vstack_filter)
            elif layout == "grid" and len(videos) == 4:
                # 2x2网格
                logger.info("使用2x2网格布局")
                # 先创建两行
                hstack1_filter = "[scaled_0][scaled_1]hstack=inputs=2[row1]"
                hstack2_filter = "[scaled_2][scaled_3]hstack=inputs=2[row2]"
                # 然后垂直堆叠两行
                vstack_filter = "[row1][row2]vstack=inputs=2[output]"
                filters.extend([hstack1_filter, hstack2_filter, vstack_filter])
            elif len(videos) == 3:
                # 3个视频：上面1个，下面2个
                logger.info("使用3视频布局")
                hstack_filter = "[scaled_1][scaled_2]hstack=inputs=2[bottom_row]"
                # 调整上面视频的宽度以匹配下面两个视频的总宽度
                scale_top_filter = f"[scaled_0]scale={grid_layout['cell_width'] * 2}:{grid_layout['cell_height']}[top_scaled]"
                vstack_filter = "[top_scaled][bottom_row]vstack=inputs=2[output]"
                filters.extend([hstack_filter, scale_top_filter, vstack_filter])
            else:
                # 默认水平排列
                logger.info(f"使用默认水平排列布局，视频数量: {len(videos)}")
                input_streams = "[" + "][".join([f"scaled_{i}" for i in range(len(videos))]) + "]"
                hstack_filter = f"{input_streams}hstack=inputs={len(videos)}[output]"
                filters.append(hstack_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 使用第一个视频的音频
                'b:v': '3M'     # 并排显示需要更高比特率
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 手动添加映射选项
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[output]')
            
            # 查找有音频流的视频
            audio_source = None
            for i, video_info in enumerate(video_infos):
                if video_info.has_audio:
                    audio_source = f'{i}:a'
                    break
            
            if audio_source:
                cmd.insert(output_file_index + 2, '-map')
                cmd.insert(output_file_index + 3, audio_source)
            else:
                # 如果没有音频流，生成静音音频
                cmd.insert(output_file_index + 2, '-f')
                cmd.insert(output_file_index + 3, 'lavfi')
                cmd.insert(output_file_index + 4, '-i')
                cmd.insert(output_file_index + 5, 'anullsrc=channel_layout=stereo:sample_rate=48000')
                cmd.insert(output_file_index + 6, '-map')
                cmd.insert(output_file_index + 7, f'{len(videos)}:a')
                cmd.insert(output_file_index + 8, '-shortest')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg并排显示命令验证失败")
            
            status_obj.progress = 45
            status_obj.message = f"正在执行并排合成 ({len(videos)}个视频)..."
            
            # 执行合成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"并排显示失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "并排视频合成完成"
            
            logger.info(f"并排显示成功: {len(videos)}个视频 -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"并排显示失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"并排显示失败: {str(e)}")
    
    def _calculate_grid_layout(self, video_infos: List[VideoInfo], layout: str) -> dict:
        """计算网格布局，保持视频宽高比"""
        video_count = len(video_infos)
        
        # 获取所有视频的分辨率信息
        widths = [info.width for info in video_infos]
        heights = [info.height for info in video_infos]
        
        # 找到最大分辨率作为基准，而不是平均值
        max_width = max(widths)
        max_height = max(heights)
        
        # 计算合理的单元格尺寸，确保能容纳最大的视频
        base_width = max_width
        base_height = max_height
        
        if layout == "horizontal":
            if video_count == 2:
                # 左右并排：保持原始高度，宽度适当缩放
                cell_width = base_width // 2
                cell_height = base_height
                output_width = cell_width * 2
                output_height = cell_height
            else:
                # 多个视频水平排列
                cell_width = base_width // video_count
                cell_height = base_height
                output_width = cell_width * video_count
                output_height = cell_height
                
        elif layout == "vertical":
            if video_count == 2:
                # 上下排列：保持原始宽度，高度适当缩放
                cell_width = base_width
                cell_height = base_height // 2
                output_width = cell_width
                output_height = cell_height * 2
            else:
                # 多个视频垂直排列
                cell_width = base_width
                cell_height = base_height // video_count
                output_width = cell_width
                output_height = cell_height * video_count
                
        elif layout == "grid" and video_count == 4:
            # 2x2网格：每个单元格是原尺寸的一半
            cell_width = base_width // 2
            cell_height = base_height // 2
            output_width = cell_width * 2
            output_height = cell_height * 2
            
        else:
            # 默认水平布局
            cell_width = base_width // video_count
            cell_height = base_height
            output_width = cell_width * video_count
            output_height = cell_height
        
        # 确保尺寸是偶数（FFmpeg要求）
        cell_width = cell_width - (cell_width % 2)
        cell_height = cell_height - (cell_height % 2)
        output_width = output_width - (output_width % 2)
        output_height = output_height - (output_height % 2)
        
        return {
            'cell_width': cell_width,
            'cell_height': cell_height,
            'output_width': output_width,
            'output_height': output_height,
            'layout': layout,
            'video_count': video_count
        }
    
    async def side_by_side_with_audio_mix(self, videos: List[dict], output_file: str,
                                         task_id: str, status_obj, layout: str = "horizontal") -> str:
        """并排视频显示并混合音频"""
        try:
            status_obj.message = "开始并排视频合成（含音频混合）..."
            status_obj.progress = 5
            
            # 验证输入
            if len(videos) < 2:
                raise InputValidationError("并排显示至少需要2个视频")
            
            if len(videos) > 4:
                raise InputValidationError("最多支持4个视频并排显示")
            
            # 验证所有视频文件并提取音频权重
            video_infos = []
            audio_weights = []
            video_files = []
            
            for i, video_data in enumerate(videos):
                video_file = video_data.get('video_url')
                if not video_file:
                    raise InputValidationError(f"视频 {i+1} 缺少video_url")
                
                video_files.append(video_file)
                info = await video_validator.validate_video_file(video_file)
                video_infos.append(info)
                
                # 获取音频权重（默认为1.0）
                volume = video_data.get('volume', 1.0)
                audio_weights.append(max(0.0, min(2.0, volume)))  # 限制在0-2之间
                
                status_obj.progress = 5 + (i + 1) * 5
            
            status_obj.progress = 25
            status_obj.message = "计算网格布局和音频混合..."
            
            # 计算网格布局
            grid_layout = self._calculate_grid_layout(video_infos, layout)
            
            status_obj.progress = 35
            status_obj.message = "构建FFmpeg命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有视频输入
            for video_file in video_files:
                builder.add_input(video_file)
            
            # 构建复杂的滤镜链
            filters = []
            
            # 视频处理：缩放所有视频到统一尺寸，保持宽高比
            for i, video_info in enumerate(video_infos):
                # 使用 scale 保持宽高比，然后用 pad 填充到目标尺寸
                scale_filter = f"[{i}:v]scale={grid_layout['cell_width']}:{grid_layout['cell_height']}:force_original_aspect_ratio=decrease[scaled_temp_{i}]"
                pad_filter = f"[scaled_temp_{i}]pad={grid_layout['cell_width']}:{grid_layout['cell_height']}:(ow-iw)/2:(oh-ih)/2:color=black[scaled_{i}]"
                filters.extend([scale_filter, pad_filter])
            
            # 音频处理：调整音量并混合
            audio_filters = []
            for i, weight in enumerate(audio_weights):
                if weight != 1.0:
                    volume_filter = f"[{i}:a]volume={weight}[audio_{i}]"
                    filters.append(volume_filter)
                    audio_filters.append(f"[audio_{i}]")
                else:
                    audio_filters.append(f"[{i}:a]")
            
            # 音频混合
            if len(audio_filters) > 1:
                audio_mix_filter = "".join(audio_filters) + f"amix=inputs={len(audio_filters)}:duration=longest[mixed_audio]"
                filters.append(audio_mix_filter)
                audio_output = "[mixed_audio]"
            else:
                audio_output = audio_filters[0]
            
            # 视频合成：根据布局类型构建合成滤镜
            if layout == "horizontal" and len(videos) == 2:
                # 左右并排
                hstack_filter = "[scaled_0][scaled_1]hstack=inputs=2[video_output]"
                filters.append(hstack_filter)
            elif layout == "vertical" and len(videos) == 2:
                # 上下排列
                vstack_filter = "[scaled_0][scaled_1]vstack=inputs=2[video_output]"
                filters.append(vstack_filter)
            elif layout == "grid" and len(videos) == 4:
                # 2x2网格
                hstack1_filter = "[scaled_0][scaled_1]hstack=inputs=2[row1]"
                hstack2_filter = "[scaled_2][scaled_3]hstack=inputs=2[row2]"
                vstack_filter = "[row1][row2]vstack=inputs=2[video_output]"
                filters.extend([hstack1_filter, hstack2_filter, vstack_filter])
            elif len(videos) == 3:
                # 3个视频：上面1个，下面2个
                hstack_filter = "[scaled_1][scaled_2]hstack=inputs=2[bottom_row]"
                scale_top_filter = f"[scaled_0]scale={grid_layout['cell_width'] * 2}:{grid_layout['cell_height']}[top_scaled]"
                vstack_filter = "[top_scaled][bottom_row]vstack=inputs=2[video_output]"
                filters.extend([hstack_filter, scale_top_filter, vstack_filter])
            else:
                # 默认水平排列
                input_streams = "[" + "][".join([f"scaled_{i}" for i in range(len(videos))]) + "]"
                hstack_filter = f"{input_streams}hstack=inputs={len(videos)}[video_output]"
                filters.append(hstack_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'aac',
                'b:v': '3M',
                'b:a': '192k'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 手动添加映射选项
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[video_output]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, audio_output)
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg并排显示音频混合命令验证失败")
            
            status_obj.progress = 45
            status_obj.message = f"正在执行并排合成和音频混合 ({len(videos)}个视频)..."
            
            # 执行合成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"并排显示音频混合失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "并排视频合成和音频混合完成"
            
            logger.info(f"并排显示音频混合成功: {len(videos)}个视频 -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s, 音频权重: {audio_weights}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"并排显示音频混合失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"并排显示音频混合失败: {str(e)}")
    
    async def adjust_audio_volume(self, input_file: str, output_file: str, 
                                 task_id: str, status_obj, volume_factor: float = 1.0,
                                 fade_in_duration: float = 0.0, 
                                 fade_out_duration: float = 0.0,
                                 output_format: str = "wav") -> str:
        """调整音频音量并添加淡入淡出效果"""
        try:
            status_obj.message = "开始音频音量调整..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入音频文件不存在: {input_file}")
            
            if volume_factor < 0 or volume_factor > 10:
                raise InputValidationError("音量因子必须在0-10之间")
            
            if fade_in_duration < 0 or fade_out_duration < 0:
                raise InputValidationError("淡入淡出时长不能为负数")
            
            # 获取音频信息
            info_dict = await ffmpeg_executor.get_video_info(input_file)
            if not info_dict.get('streams'):
                raise ProcessingError(f"无法获取音频信息: {input_file}")
            
            # 查找音频流
            audio_stream = None
            for stream in info_dict['streams']:
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ProcessingError(f"输入文件中没有音频流: {input_file}")
            
            duration = float(audio_stream.get('duration', 0))
            
            status_obj.progress = 15
            status_obj.message = "构建音频处理命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 构建音频滤镜链
            filters = []
            
            # 音量调整
            if volume_factor != 1.0:
                filters.append(f"volume={volume_factor}")
            
            # 淡入效果
            if fade_in_duration > 0:
                filters.append(f"afade=t=in:st=0:d={fade_in_duration}")
            
            # 淡出效果
            if fade_out_duration > 0 and duration > fade_out_duration:
                fade_start = duration - fade_out_duration
                filters.append(f"afade=t=out:st={fade_start}:d={fade_out_duration}")
            
            # 组合滤镜
            if filters:
                filter_chain = ",".join(filters)
                builder.add_filter(f"[0:a]{filter_chain}[audio_out]")
            
            # 根据输出格式设置编码器
            if output_format == "mp3":
                codec = 'libmp3lame'
            elif output_format == "wav":
                codec = 'pcm_s16le'
            elif output_format == "aac":
                codec = 'aac'
            elif output_format == "flac":
                codec = 'flac'
            else:
                codec = 'aac'  # 默认
            
            # 输出选项
            output_options = {
                'c:a': codec,
                'ar': '44100'
            }
            
            # 某些格式不需要比特率
            if codec not in ['pcm_s16le', 'flac']:
                output_options['b:a'] = '128k'
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            if filters:
                output_file_index = cmd.index(output_file)
                cmd.insert(output_file_index, '-map')
                cmd.insert(output_file_index + 1, '[audio_out]')
            else:
                # 如果没有滤镜，直接映射音频流
                output_file_index = cmd.index(output_file)
                cmd.insert(output_file_index, '-map')
                cmd.insert(output_file_index + 1, '0:a')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg音频处理命令验证失败")
            
            status_obj.progress = 25
            status_obj.message = "正在处理音频..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"音频处理失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "音频处理完成"
            
            logger.info(f"音频音量调整完成: {input_file} -> {output_file}")
            logger.info(f"音量因子: {volume_factor}, 淡入: {fade_in_duration}s, 淡出: {fade_out_duration}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"音频音量调整失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"音频音量调整失败: {str(e)}")
    
    async def convert_audio_format(self, input_file: str, output_file: str,
                                  task_id: str, status_obj, 
                                  output_format: str = "aac",
                                  bitrate: str = "128k",
                                  sample_rate: int = 44100) -> str:
        """转换音频格式"""
        try:
            status_obj.message = "开始音频格式转换..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入音频文件不存在: {input_file}")
            
            # 支持的音频格式
            supported_formats = {
                'aac': {'codec': 'aac', 'ext': '.aac'},
                'mp3': {'codec': 'libmp3lame', 'ext': '.mp3'},
                'wav': {'codec': 'pcm_s16le', 'ext': '.wav'},
                'flac': {'codec': 'flac', 'ext': '.flac'},
                'ogg': {'codec': 'libvorbis', 'ext': '.ogg'}
            }
            
            if output_format not in supported_formats:
                raise InputValidationError(f"不支持的音频格式: {output_format}")
            
            # 验证比特率
            valid_bitrates = ['64k', '96k', '128k', '192k', '256k', '320k']
            if bitrate not in valid_bitrates:
                raise InputValidationError(f"不支持的比特率: {bitrate}")
            
            # 验证采样率
            valid_sample_rates = [8000, 16000, 22050, 44100, 48000, 96000]
            if sample_rate not in valid_sample_rates:
                raise InputValidationError(f"不支持的采样率: {sample_rate}")
            
            status_obj.progress = 15
            status_obj.message = f"转换为{output_format.upper()}格式..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 输出选项
            format_info = supported_formats[output_format]
            output_options = {
                'c:a': format_info['codec'],
                'ar': str(sample_rate)
            }
            
            # 某些格式不支持比特率设置
            if output_format not in ['wav', 'flac']:
                output_options['b:a'] = bitrate
            
            # 确保输出文件扩展名正确
            if not output_file.endswith(f'.{output_format}'):
                base_name = os.path.splitext(output_file)[0]
                output_file = f"{base_name}.{output_format}"
            
            builder.add_output(output_file, output_options)
            
            # 构建并验证命令
            cmd = builder.build()
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg音频转换命令验证失败")
            
            status_obj.progress = 25
            status_obj.message = "正在转换音频格式..."
            
            # 执行转换
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"音频格式转换失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "音频格式转换完成"
            
            logger.info(f"音频格式转换完成: {input_file} -> {output_file}")
            logger.info(f"格式: {output_format}, 比特率: {bitrate}, 采样率: {sample_rate}Hz")
            
            return output_file
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"音频格式转换失败: {str(e)}")
    
    async def extract_audio_from_video(self, input_file: str, output_file: str,
                                      task_id: str, status_obj,
                                      start_time: float = 0.0,
                                      duration: float = None,
                                      output_format: str = "mp3") -> str:
        """从视频中提取音频"""
        try:
            status_obj.message = "开始从视频提取音频..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入视频文件不存在: {input_file}")
            
            if start_time < 0:
                raise InputValidationError("开始时间不能为负数")
            
            if duration is not None and duration <= 0:
                raise InputValidationError("持续时间必须大于0")
            
            # 获取视频信息
            info_dict = await ffmpeg_executor.get_video_info(input_file)
            if not info_dict.get('streams'):
                raise ProcessingError(f"无法获取视频信息: {input_file}")
            
            # 查找音频流
            audio_stream = None
            for stream in info_dict['streams']:
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ProcessingError(f"视频文件中没有音频流: {input_file}")
            
            video_duration = float(audio_stream.get('duration', 0))
            
            # 验证时间范围
            if start_time >= video_duration:
                raise InputValidationError(f"开始时间({start_time}s)超过视频长度({video_duration}s)")
            
            if duration is None:
                duration = video_duration - start_time
            elif start_time + duration > video_duration:
                duration = video_duration - start_time
                logger.warning(f"持续时间超过视频长度，调整为{duration}秒")
            
            status_obj.progress = 15
            status_obj.message = "构建音频提取命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加输入选项
            input_options = {}
            if start_time > 0:
                input_options['ss'] = str(start_time)
            if duration:
                input_options['t'] = str(duration)
            
            builder.add_input(input_file, input_options)
            
            # 根据输出格式设置编码器
            if output_format == "mp3":
                codec = 'libmp3lame'
            elif output_format == "wav":
                codec = 'pcm_s16le'
            elif output_format == "aac":
                codec = 'aac'
            elif output_format == "flac":
                codec = 'flac'
            else:
                codec = 'aac'  # 默认
            
            # 输出选项
            output_options = {
                'vn': None,  # 不包含视频
                'c:a': codec,
                'ar': '44100'
            }
            
            # 某些格式不需要比特率
            if codec not in ['pcm_s16le', 'flac']:
                output_options['b:a'] = '128k'
            
            builder.add_output(output_file, output_options)
            
            # 构建并验证命令
            cmd = builder.build()
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg音频提取命令验证失败")
            
            status_obj.progress = 25
            status_obj.message = "正在提取音频..."
            
            # 执行提取
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"音频提取失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "音频提取完成"
            
            logger.info(f"音频提取完成: {input_file} -> {output_file}")
            logger.info(f"时间范围: {start_time}s - {start_time + duration}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"音频提取失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"音频提取失败: {str(e)}")
    
    async def create_slideshow_from_keyframes(self, keyframe_images: List[str], 
                                            output_file: str, task_id: str, 
                                            status_obj, duration_per_frame: float = 2.0,
                                            transition_type: str = "fade",
                                            background_audio: str = None) -> str:
        """从关键帧图片创建幻灯片视频"""
        try:
            status_obj.message = "开始创建关键帧幻灯片..."
            status_obj.progress = 5
            
            # 验证输入
            if not keyframe_images:
                raise InputValidationError("必须提供至少一张关键帧图片")
            
            if len(keyframe_images) > 100:
                raise InputValidationError("关键帧图片数量不能超过100张")
            
            # 验证所有图片文件
            for i, image_file in enumerate(keyframe_images):
                if not os.path.exists(image_file):
                    raise InputValidationError(f"图片文件不存在: {image_file}")
                
                # 检查文件格式
                ext = os.path.splitext(image_file)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                    raise InputValidationError(f"不支持的图片格式: {ext}")
            
            status_obj.progress = 15
            status_obj.message = "分析图片尺寸..."
            
            # 获取图片信息并确定统一尺寸
            target_resolution = await self._analyze_image_dimensions(keyframe_images)
            
            status_obj.progress = 25
            status_obj.message = "构建幻灯片FFmpeg命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有图片输入
            for image_file in keyframe_images:
                builder.add_input(image_file)
            
            # 构建滤镜链
            filters = []
            
            # 缩放和适配所有图片，并设置持续时间
            for i, image_file in enumerate(keyframe_images):
                # 缩放并标准化图片，设置SAR为1:1
                scale_filter = f"[{i}:v]scale={target_resolution['width']}:{target_resolution['height']}:force_original_aspect_ratio=decrease,pad={target_resolution['width']}:{target_resolution['height']}:(ow-iw)/2:(oh-ih)/2:black,setsar=1:1,fps=30[scaled_{i}]"
                filters.append(scale_filter)
                
                # 设置每帧持续时间（转换为30fps的帧数）
                frame_count = int(duration_per_frame * 30)  # 30fps
                duration_filter = f"[scaled_{i}]loop=loop={frame_count}:size=1:start=0[img_{i}]"
                filters.append(duration_filter)
            
            # 拼接所有图片
            concat_inputs = "[" + "][".join([f"img_{i}" for i in range(len(keyframe_images))]) + "]"
            concat_filter = f"{concat_inputs}concat=n={len(keyframe_images)}:v=1:a=0[slideshow]"
            filters.append(concat_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'r': '30',  # 30fps
                'pix_fmt': 'yuv420p',
                'b:v': '2M'
            }
            
            # 如果有背景音乐
            if background_audio and os.path.exists(background_audio):
                builder.add_input(background_audio)
                output_options['c:a'] = 'aac'
                output_options['b:a'] = '128k'
                output_options['shortest'] = None  # 以最短的流为准
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 手动添加映射选项
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[slideshow]')
            
            if background_audio and os.path.exists(background_audio):
                cmd.insert(output_file_index + 2, '-map')
                cmd.insert(output_file_index + 3, f'{len(keyframe_images)}:a')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg幻灯片命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = f"正在生成幻灯片 ({len(keyframe_images)}张图片)..."
            
            # 执行生成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"幻灯片生成失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "关键帧幻灯片创建完成"
            
            logger.info(f"幻灯片生成成功: {len(keyframe_images)}张图片 -> {output_file}")
            logger.info(f"输出视频信息: {output_info.width}x{output_info.height}, "
                       f"{output_info.duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"幻灯片生成失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"幻灯片生成失败: {str(e)}")
    
    async def _analyze_image_dimensions(self, image_files: List[str]) -> dict:
        """分析图片尺寸并确定目标分辨率"""
        try:
            # 使用ffprobe获取第一张图片的信息作为参考
            first_image = image_files[0]
            info_dict = await ffmpeg_executor.get_video_info(first_image)
            
            if not info_dict.get('streams'):
                raise ProcessingError(f"无法获取图片信息: {first_image}")
            
            video_stream = info_dict['streams'][0]
            width = int(video_stream.get('width', 1920))
            height = int(video_stream.get('height', 1080))
            
            # 确保尺寸是偶数（FFmpeg要求）
            width = width - (width % 2)
            height = height - (height % 2)
            
            # 如果尺寸过大，缩放到合理范围
            max_width = 1920
            max_height = 1080
            
            if width > max_width or height > max_height:
                # 保持宽高比缩放
                ratio = min(max_width / width, max_height / height)
                width = int(width * ratio)
                height = int(height * ratio)
                
                # 确保是偶数
                width = width - (width % 2)
                height = height - (height % 2)
            
            return {
                'width': width,
                'height': height
            }
            
        except Exception as e:
            logger.warning(f"分析图片尺寸失败，使用默认分辨率: {str(e)}")
            return {
                'width': 1920,
                'height': 1080
            }
    
    async def create_slideshow_with_transitions(self, keyframe_images: List[str],
                                              output_file: str, task_id: str,
                                              status_obj, frame_duration: float = 3.0,
                                              transition_duration: float = 0.5,
                                              background_audio: str = None) -> str:
        """创建带转场效果的幻灯片"""
        try:
            status_obj.message = "开始创建带转场的幻灯片..."
            status_obj.progress = 5
            
            # 验证输入
            if not keyframe_images or len(keyframe_images) < 2:
                raise InputValidationError("转场幻灯片至少需要2张图片")
            
            # 获取目标分辨率
            target_resolution = await self._analyze_image_dimensions(keyframe_images)
            
            status_obj.progress = 15
            status_obj.message = "构建转场幻灯片命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有图片输入
            for image_file in keyframe_images:
                builder.add_input(image_file)
            
            # 构建简化的转场滤镜链
            filters = []
            
            # 缩放和标准化所有图片
            for i, image_file in enumerate(keyframe_images):
                # 缩放并标准化图片，设置SAR为1:1
                scale_filter = f"[{i}:v]scale={target_resolution['width']}:{target_resolution['height']}:force_original_aspect_ratio=decrease,pad={target_resolution['width']}:{target_resolution['height']}:(ow-iw)/2:(oh-ih)/2:black,setsar=1:1,fps=30[scaled_{i}]"
                filters.append(scale_filter)
                
                # 设置每帧持续时间（包含转场时间）
                total_duration = frame_duration + (transition_duration if i < len(keyframe_images) - 1 else 0)
                frame_count = int(total_duration * 30)  # 30fps
                duration_filter = f"[scaled_{i}]loop=loop={frame_count-1}:size=1:start=0[img_{i}]"
                filters.append(duration_filter)
                
                # 添加淡入淡出效果
                if i == 0:
                    # 第一张图片只有淡出
                    fade_filter = f"[img_{i}]fade=t=out:st={frame_duration}:d={transition_duration}[faded_{i}]"
                elif i == len(keyframe_images) - 1:
                    # 最后一张图片只有淡入
                    fade_filter = f"[img_{i}]fade=t=in:st=0:d={transition_duration}[faded_{i}]"
                else:
                    # 中间图片有淡入和淡出
                    fade_filter = f"[img_{i}]fade=t=in:st=0:d={transition_duration},fade=t=out:st={frame_duration}:d={transition_duration}[faded_{i}]"
                filters.append(fade_filter)
            
            # 拼接所有带转场效果的图片
            concat_inputs = "[" + "][".join([f"faded_{i}" for i in range(len(keyframe_images))]) + "]"
            concat_filter = f"{concat_inputs}concat=n={len(keyframe_images)}:v=1:a=0[slideshow]"
            filters.append(concat_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'r': '30',
                'pix_fmt': 'yuv420p',
                'b:v': '2M'
            }
            
            # 处理背景音乐
            if background_audio and os.path.exists(background_audio):
                builder.add_input(background_audio)
                output_options['c:a'] = 'aac'
                output_options['b:a'] = '128k'
            
            builder.add_output(output_file, output_options)
            
            # 构建并执行命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[slideshow]')
            
            if background_audio and os.path.exists(background_audio):
                cmd.insert(output_file_index + 2, '-map')
                cmd.insert(output_file_index + 3, f'{len(keyframe_images)}:a')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg转场幻灯片命令验证失败")
            
            status_obj.progress = 30
            status_obj.message = "正在生成转场幻灯片..."
            
            # 执行生成
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出
            if not os.path.exists(output_file):
                raise ProcessingError(f"转场幻灯片生成失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "转场幻灯片创建完成"
            
            logger.info(f"转场幻灯片生成成功: {len(keyframe_images)}张图片 -> {output_file}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"转场幻灯片生成失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"转场幻灯片生成失败: {str(e)}")
    
    async def mix_multiple_audio_tracks(self, audio_files: List[str], 
                                       output_file: str, task_id: str, 
                                       status_obj, weights: List[float] = None,
                                       output_format: str = "mp3") -> str:
        """混合多个音频轨道"""
        try:
            status_obj.message = "开始多轨音频混合..."
            status_obj.progress = 5
            
            # 验证输入
            if not audio_files or len(audio_files) < 2:
                raise InputValidationError("多轨音频混合至少需要2个音频文件")
            
            if len(audio_files) > 10:
                raise InputValidationError("音频文件数量不能超过10个")
            
            # 验证所有音频文件
            for i, audio_file in enumerate(audio_files):
                if not os.path.exists(audio_file):
                    raise InputValidationError(f"音频文件不存在: {audio_file}")
            
            # 设置默认权重
            if weights is None:
                weights = [1.0] * len(audio_files)
            elif len(weights) != len(audio_files):
                raise InputValidationError("权重数量必须与音频文件数量相同")
            
            # 验证权重值
            for i, weight in enumerate(weights):
                if weight < 0 or weight > 10:
                    raise InputValidationError(f"权重值必须在0-10之间: {weight}")
            
            status_obj.progress = 15
            status_obj.message = "分析音频文件信息..."
            
            # 获取所有音频文件的信息
            audio_infos = []
            max_duration = 0
            
            for audio_file in audio_files:
                info_dict = await ffmpeg_executor.get_video_info(audio_file)
                if not info_dict.get('streams'):
                    raise ProcessingError(f"无法获取音频信息: {audio_file}")
                
                # 查找音频流
                audio_stream = None
                for stream in info_dict['streams']:
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                if not audio_stream:
                    raise ProcessingError(f"文件中没有音频流: {audio_file}")
                
                duration = float(audio_stream.get('duration', 0))
                max_duration = max(max_duration, duration)
                audio_infos.append({
                    'file': audio_file,
                    'duration': duration,
                    'sample_rate': int(audio_stream.get('sample_rate', 44100)),
                    'channels': int(audio_stream.get('channels', 2))
                })
            
            status_obj.progress = 25
            status_obj.message = "构建音频混合命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有音频输入
            for audio_file in audio_files:
                builder.add_input(audio_file)
            
            # 构建音频混合滤镜
            filters = []
            
            # 标准化所有音频流（统一采样率和声道数）
            normalized_streams = []
            for i, info in enumerate(audio_infos):
                # 标准化为44100Hz立体声
                normalize_filter = f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo[norm_{i}]"
                filters.append(normalize_filter)
                normalized_streams.append(f"[norm_{i}]")
            
            # 应用音量权重
            weighted_streams = []
            for i, weight in enumerate(weights):
                if weight != 1.0:
                    volume_filter = f"[norm_{i}]volume={weight}[weighted_{i}]"
                    filters.append(volume_filter)
                    weighted_streams.append(f"[weighted_{i}]")
                else:
                    weighted_streams.append(f"[norm_{i}]")
            
            # 混合所有音频流
            mix_inputs = "".join(weighted_streams)
            mix_filter = f"{mix_inputs}amix=inputs={len(audio_files)}:duration=longest:dropout_transition=2[mixed]"
            filters.append(mix_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:a': 'aac' if output_format == 'mp3' else 'aac',
                'b:a': '192k',
                'ar': '44100',
                'ac': '2'
            }
            
            if output_format == 'mp3':
                output_options['c:a'] = 'libmp3lame'
            elif output_format == 'wav':
                output_options['c:a'] = 'pcm_s16le'
            elif output_format == 'flac':
                output_options['c:a'] = 'flac'
                del output_options['b:a']  # FLAC不需要比特率
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[mixed]')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg音频混合命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = f"正在混合{len(audio_files)}个音频轨道..."
            
            # 执行混合
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"音频混合失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "多轨音频混合完成"
            
            logger.info(f"多轨音频混合完成: {len(audio_files)}个文件 -> {output_file}")
            logger.info(f"权重: {weights}, 最长时长: {max_duration:.1f}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"多轨音频混合失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"多轨音频混合失败: {str(e)}")
    
    async def create_audio_crossfade(self, audio_files: List[str], 
                                    output_file: str, task_id: str, 
                                    status_obj, crossfade_duration: float = 2.0) -> str:
        """创建音频交叉淡入淡出效果"""
        try:
            status_obj.message = "开始创建音频交叉淡入淡出..."
            status_obj.progress = 5
            
            # 验证输入
            if not audio_files or len(audio_files) < 2:
                raise InputValidationError("交叉淡入淡出至少需要2个音频文件")
            
            if crossfade_duration < 0.1 or crossfade_duration > 10.0:
                raise InputValidationError("交叉淡入淡出时长必须在0.1-10秒之间")
            
            # 验证所有音频文件
            for audio_file in audio_files:
                if not os.path.exists(audio_file):
                    raise InputValidationError(f"音频文件不存在: {audio_file}")
            
            status_obj.progress = 15
            status_obj.message = "分析音频文件..."
            
            # 获取音频信息
            audio_infos = []
            for audio_file in audio_files:
                info_dict = await ffmpeg_executor.get_video_info(audio_file)
                if not info_dict.get('streams'):
                    raise ProcessingError(f"无法获取音频信息: {audio_file}")
                
                # 查找音频流
                audio_stream = None
                for stream in info_dict['streams']:
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                if not audio_stream:
                    raise ProcessingError(f"文件中没有音频流: {audio_file}")
                
                duration = float(audio_stream.get('duration', 0))
                if duration < crossfade_duration:
                    raise InputValidationError(f"音频文件时长({duration:.1f}s)小于交叉淡入淡出时长({crossfade_duration}s): {audio_file}")
                
                audio_infos.append({
                    'file': audio_file,
                    'duration': duration
                })
            
            status_obj.progress = 25
            status_obj.message = "构建交叉淡入淡出命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            
            # 添加所有音频输入
            for audio_file in audio_files:
                builder.add_input(audio_file)
            
            # 构建交叉淡入淡出滤镜链
            filters = []
            
            # 标准化所有音频流
            for i, info in enumerate(audio_infos):
                normalize_filter = f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo[norm_{i}]"
                filters.append(normalize_filter)
            
            # 创建交叉淡入淡出效果
            current_stream = "[norm_0]"
            
            for i in range(1, len(audio_files)):
                # 为当前音频添加淡出效果
                prev_duration = audio_infos[i-1]['duration']
                fadeout_start = prev_duration - crossfade_duration
                fadeout_filter = f"{current_stream}afade=t=out:st={fadeout_start}:d={crossfade_duration}[fadeout_{i-1}]"
                filters.append(fadeout_filter)
                
                # 为下一个音频添加淡入效果
                fadein_filter = f"[norm_{i}]afade=t=in:st=0:d={crossfade_duration}[fadein_{i}]"
                filters.append(fadein_filter)
                
                # 延迟下一个音频的开始时间
                delay_time = sum(info['duration'] for info in audio_infos[:i]) - crossfade_duration * i
                delay_filter = f"[fadein_{i}]adelay={int(delay_time * 1000)}|{int(delay_time * 1000)}[delayed_{i}]"
                filters.append(delay_filter)
                
                # 混合两个音频
                if i == len(audio_files) - 1:
                    # 最后一个音频
                    mix_filter = f"[fadeout_{i-1}][delayed_{i}]amix=inputs=2:duration=longest[crossfaded]"
                else:
                    mix_filter = f"[fadeout_{i-1}][delayed_{i}]amix=inputs=2:duration=longest[mixed_{i}]"
                    current_stream = f"[mixed_{i}]"
                
                filters.append(mix_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:a': 'aac',
                'b:a': '192k',
                'ar': '44100',
                'ac': '2'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[crossfaded]')
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg交叉淡入淡出命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在创建交叉淡入淡出效果..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"交叉淡入淡出创建失败，输出文件不存在: {output_file}")
            
            status_obj.progress = 100
            status_obj.message = "音频交叉淡入淡出完成"
            
            logger.info(f"音频交叉淡入淡出完成: {len(audio_files)}个文件 -> {output_file}")
            logger.info(f"交叉淡入淡出时长: {crossfade_duration}s")
            
            return output_file
            
        except Exception as e:
            logger.error(f"音频交叉淡入淡出失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"音频交叉淡入淡出失败: {str(e)}")
    
    async def add_image_watermark(self, input_file: str, watermark_image: str,
                                 output_file: str, task_id: str, status_obj,
                                 position: str = "bottom-right", 
                                 opacity: float = 0.8,
                                 scale: float = 0.1) -> str:
        """添加图片水印"""
        try:
            status_obj.message = "开始添加图片水印..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入视频文件不存在: {input_file}")
            
            if not os.path.exists(watermark_image):
                raise InputValidationError(f"水印图片文件不存在: {watermark_image}")
            
            if opacity < 0 or opacity > 1:
                raise InputValidationError("透明度必须在0-1之间")
            
            if scale <= 0 or scale > 1:
                raise InputValidationError("缩放比例必须在0-1之间")
            
            # 支持的位置
            valid_positions = [
                "top-left", "top-right", "bottom-left", "bottom-right", 
                "center", "top-center", "bottom-center"
            ]
            if position not in valid_positions:
                raise InputValidationError(f"不支持的位置: {position}，支持的位置: {valid_positions}")
            
            status_obj.progress = 15
            status_obj.message = "获取视频信息..."
            
            # 获取视频信息
            video_info = await ffmpeg_executor.get_video_info(input_file)
            if not video_info.get('streams'):
                raise ProcessingError(f"无法获取视频信息: {input_file}")
            
            # 查找视频流
            video_stream = None
            for stream in video_info['streams']:
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ProcessingError(f"视频文件中没有视频流: {input_file}")
            
            video_width = int(video_stream.get('width', 1920))
            video_height = int(video_stream.get('height', 1080))
            
            status_obj.progress = 25
            status_obj.message = "构建水印添加命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            builder.add_input(watermark_image)
            
            # 计算水印位置
            watermark_width = f"iw*{scale}"
            watermark_height = f"ih*{scale}"
            
            # 根据位置计算坐标
            if position == "top-left":
                x_pos = "10"
                y_pos = "10"
            elif position == "top-right":
                x_pos = f"main_w-overlay_w-10"
                y_pos = "10"
            elif position == "bottom-left":
                x_pos = "10"
                y_pos = f"main_h-overlay_h-10"
            elif position == "bottom-right":
                x_pos = f"main_w-overlay_w-10"
                y_pos = f"main_h-overlay_h-10"
            elif position == "center":
                x_pos = f"(main_w-overlay_w)/2"
                y_pos = f"(main_h-overlay_h)/2"
            elif position == "top-center":
                x_pos = f"(main_w-overlay_w)/2"
                y_pos = "10"
            elif position == "bottom-center":
                x_pos = f"(main_w-overlay_w)/2"
                y_pos = f"main_h-overlay_h-10"
            
            # 构建滤镜链
            filters = []
            
            # 缩放水印图片并设置透明度
            watermark_filter = f"[1:v]scale={watermark_width}:{watermark_height},format=rgba,colorchannelmixer=aa={opacity}[watermark]"
            filters.append(watermark_filter)
            
            # 叠加水印
            overlay_filter = f"[0:v][watermark]overlay={x_pos}:{y_pos}[watermarked]"
            filters.append(overlay_filter)
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制音频流
                'preset': 'medium',
                'crf': '23'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[watermarked]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a?')  # 可选音频流
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg图片水印命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在添加图片水印..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"图片水印添加失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "图片水印添加完成"
            
            logger.info(f"图片水印添加完成: {input_file} -> {output_file}")
            logger.info(f"水印位置: {position}, 透明度: {opacity}, 缩放: {scale}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"图片水印添加失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"图片水印添加失败: {str(e)}")
    
    async def add_text_watermark(self, input_file: str, text: str,
                                output_file: str, task_id: str, status_obj,
                                position: str = "bottom-right",
                                font_size: int = 24,
                                font_color: str = "white",
                                opacity: float = 0.8,
                                font_file: str = None) -> str:
        """添加文字水印"""
        try:
            status_obj.message = "开始添加文字水印..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入视频文件不存在: {input_file}")
            
            if not text or len(text.strip()) == 0:
                raise InputValidationError("水印文字不能为空")
            
            if font_size < 8 or font_size > 200:
                raise InputValidationError("字体大小必须在8-200之间")
            
            if opacity < 0 or opacity > 1:
                raise InputValidationError("透明度必须在0-1之间")
            
            # 支持的位置
            valid_positions = [
                "top-left", "top-right", "bottom-left", "bottom-right", 
                "center", "top-center", "bottom-center"
            ]
            if position not in valid_positions:
                raise InputValidationError(f"不支持的位置: {position}，支持的位置: {valid_positions}")
            
            status_obj.progress = 15
            status_obj.message = "获取视频信息..."
            
            # 获取视频信息
            video_info = await ffmpeg_executor.get_video_info(input_file)
            if not video_info.get('streams'):
                raise ProcessingError(f"无法获取视频信息: {input_file}")
            
            # 查找视频流
            video_stream = None
            for stream in video_info['streams']:
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ProcessingError(f"视频文件中没有视频流: {input_file}")
            
            status_obj.progress = 25
            status_obj.message = "构建文字水印命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 计算文字位置
            if position == "top-left":
                x_pos = "10"
                y_pos = "10"
            elif position == "top-right":
                x_pos = f"w-tw-10"
                y_pos = "10"
            elif position == "bottom-left":
                x_pos = "10"
                y_pos = f"h-th-10"
            elif position == "bottom-right":
                x_pos = f"w-tw-10"
                y_pos = f"h-th-10"
            elif position == "center":
                x_pos = f"(w-tw)/2"
                y_pos = f"(h-th)/2"
            elif position == "top-center":
                x_pos = f"(w-tw)/2"
                y_pos = "10"
            elif position == "bottom-center":
                x_pos = f"(w-tw)/2"
                y_pos = f"h-th-10"
            
            # 构建drawtext滤镜
            drawtext_options = [
                f"text='{text}'",
                f"x={x_pos}",
                f"y={y_pos}",
                f"fontsize={font_size}",
                f"fontcolor={font_color}@{opacity}",
                "box=1",
                "boxcolor=black@0.3",
                "boxborderw=5"
            ]
            
            # 如果指定了字体文件
            if font_file and os.path.exists(font_file):
                drawtext_options.append(f"fontfile='{font_file}'")
            
            drawtext_filter = f"[0:v]drawtext={':'.join(drawtext_options)}[watermarked]"
            builder.add_filter(drawtext_filter)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制音频流
                'preset': 'medium',
                'crf': '23'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[watermarked]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a?')  # 可选音频流
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg文字水印命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在添加文字水印..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"文字水印添加失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "文字水印添加完成"
            
            logger.info(f"文字水印添加完成: {input_file} -> {output_file}")
            logger.info(f"水印文字: {text}, 位置: {position}, 字体大小: {font_size}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"文字水印添加失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"文字水印添加失败: {str(e)}")
    
    async def apply_video_filters(self, input_file: str, output_file: str,
                                 task_id: str, status_obj,
                                 brightness: float = 0.0,
                                 contrast: float = 1.0,
                                 saturation: float = 1.0,
                                 blur: float = 0.0,
                                 sharpen: float = 0.0,
                                 gamma: float = 1.0) -> str:
        """应用基础视频滤镜"""
        try:
            status_obj.message = "开始应用视频滤镜..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入视频文件不存在: {input_file}")
            
            # 验证参数范围
            if brightness < -1.0 or brightness > 1.0:
                raise InputValidationError("亮度调整范围必须在-1.0到1.0之间")
            
            if contrast < 0.0 or contrast > 3.0:
                raise InputValidationError("对比度调整范围必须在0.0到3.0之间")
            
            if saturation < 0.0 or saturation > 3.0:
                raise InputValidationError("饱和度调整范围必须在0.0到3.0之间")
            
            if blur < 0.0 or blur > 10.0:
                raise InputValidationError("模糊强度范围必须在0.0到10.0之间")
            
            if sharpen < 0.0 or sharpen > 5.0:
                raise InputValidationError("锐化强度范围必须在0.0到5.0之间")
            
            if gamma < 0.1 or gamma > 3.0:
                raise InputValidationError("伽马值范围必须在0.1到3.0之间")
            
            status_obj.progress = 15
            status_obj.message = "获取视频信息..."
            
            # 获取视频信息
            video_info = await ffmpeg_executor.get_video_info(input_file)
            if not video_info.get('streams'):
                raise ProcessingError(f"无法获取视频信息: {input_file}")
            
            # 查找视频流
            video_stream = None
            for stream in video_info['streams']:
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ProcessingError(f"视频文件中没有视频流: {input_file}")
            
            status_obj.progress = 25
            status_obj.message = "构建滤镜命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 构建滤镜链
            filters = []
            current_stream = "[0:v]"
            
            # 亮度、对比度、饱和度调整
            if brightness != 0.0 or contrast != 1.0 or saturation != 1.0:
                eq_filter = f"{current_stream}eq=brightness={brightness}:contrast={contrast}:saturation={saturation}[eq]"
                filters.append(eq_filter)
                current_stream = "[eq]"
            
            # 伽马校正
            if gamma != 1.0:
                gamma_filter = f"{current_stream}eq=gamma={gamma}[gamma]"
                filters.append(gamma_filter)
                current_stream = "[gamma]"
            
            # 模糊滤镜
            if blur > 0.0:
                blur_filter = f"{current_stream}boxblur={blur}:{blur}[blur]"
                filters.append(blur_filter)
                current_stream = "[blur]"
            
            # 锐化滤镜
            if sharpen > 0.0:
                # 使用unsharp滤镜进行锐化
                sharpen_amount = min(sharpen * 0.5, 2.0)  # 限制锐化强度
                sharpen_filter = f"{current_stream}unsharp=5:5:{sharpen_amount}:5:5:{sharpen_amount}[sharpen]"
                filters.append(sharpen_filter)
                current_stream = "[sharpen]"
            
            # 如果没有应用任何滤镜，直接复制
            if not filters:
                filters.append(f"[0:v]copy[filtered]")
                current_stream = "[filtered]"
            else:
                # 重命名最后的流
                last_filter = filters[-1]
                filters[-1] = last_filter.replace(current_stream.split(']')[0] + ']', '[filtered]')
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制音频流
                'preset': 'medium',
                'crf': '23'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[filtered]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a?')  # 可选音频流
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg视频滤镜命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在应用视频滤镜..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"视频滤镜应用失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "视频滤镜应用完成"
            
            logger.info(f"视频滤镜应用完成: {input_file} -> {output_file}")
            logger.info(f"滤镜参数: 亮度={brightness}, 对比度={contrast}, 饱和度={saturation}, "
                       f"模糊={blur}, 锐化={sharpen}, 伽马={gamma}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"视频滤镜应用失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"视频滤镜应用失败: {str(e)}")
    
    async def apply_color_correction(self, input_file: str, output_file: str,
                                    task_id: str, status_obj,
                                    temperature: float = 0.0,
                                    tint: float = 0.0,
                                    highlights: float = 0.0,
                                    shadows: float = 0.0,
                                    vibrance: float = 0.0) -> str:
        """应用色彩校正"""
        try:
            status_obj.message = "开始色彩校正..."
            status_obj.progress = 5
            
            # 验证输入
            if not os.path.exists(input_file):
                raise InputValidationError(f"输入视频文件不存在: {input_file}")
            
            # 验证参数范围
            if temperature < -100 or temperature > 100:
                raise InputValidationError("色温调整范围必须在-100到100之间")
            
            if tint < -100 or tint > 100:
                raise InputValidationError("色调调整范围必须在-100到100之间")
            
            if highlights < -100 or highlights > 100:
                raise InputValidationError("高光调整范围必须在-100到100之间")
            
            if shadows < -100 or shadows > 100:
                raise InputValidationError("阴影调整范围必须在-100到100之间")
            
            if vibrance < -100 or vibrance > 100:
                raise InputValidationError("自然饱和度调整范围必须在-100到100之间")
            
            status_obj.progress = 15
            status_obj.message = "获取视频信息..."
            
            # 获取视频信息
            video_info = await ffmpeg_executor.get_video_info(input_file)
            if not video_info.get('streams'):
                raise ProcessingError(f"无法获取视频信息: {input_file}")
            
            status_obj.progress = 25
            status_obj.message = "构建色彩校正命令..."
            
            # 构建FFmpeg命令
            builder = FFmpegCommandBuilder()
            builder.add_input(input_file)
            
            # 构建色彩校正滤镜链
            filters = []
            current_stream = "[0:v]"
            
            # 色温和色调调整（使用colortemperature滤镜）
            if temperature != 0.0 or tint != 0.0:
                # 将温度值转换为开尔文值
                kelvin = 6500 + (temperature * 20)  # 基准6500K
                temp_filter = f"{current_stream}colortemperature=temperature={kelvin}[temp]"
                filters.append(temp_filter)
                current_stream = "[temp]"
            
            # 高光和阴影调整
            if highlights != 0.0 or shadows != 0.0:
                # 使用curves滤镜进行高光阴影调整
                highlight_factor = 1.0 + (highlights / 100.0)
                shadow_factor = 1.0 + (shadows / 100.0)
                
                # 简化的曲线调整
                if highlights > 0:  # 降低高光
                    curves_filter = f"{current_stream}curves=all='0/0 0.7/{0.7/highlight_factor} 1/1'[highlights]"
                elif highlights < 0:  # 提升高光
                    curves_filter = f"{current_stream}curves=all='0/0 0.7/{0.7*abs(highlight_factor)} 1/1'[highlights]"
                else:
                    curves_filter = f"{current_stream}copy[highlights]"
                
                filters.append(curves_filter)
                current_stream = "[highlights]"
            
            # 自然饱和度调整
            if vibrance != 0.0:
                vibrance_factor = 1.0 + (vibrance / 100.0)
                vibrance_filter = f"{current_stream}eq=saturation={vibrance_factor}[vibrance]"
                filters.append(vibrance_filter)
                current_stream = "[vibrance]"
            
            # 如果没有应用任何滤镜，直接复制
            if not filters:
                filters.append(f"[0:v]copy[corrected]")
            else:
                # 重命名最后的流
                last_filter = filters[-1]
                filters[-1] = last_filter.replace(current_stream.split(']')[0] + ']', '[corrected]')
            
            # 添加滤镜到构建器
            for filter_str in filters:
                builder.add_filter(filter_str)
            
            # 输出选项
            output_options = {
                'c:v': 'libx264',
                'c:a': 'copy',  # 复制音频流
                'preset': 'medium',
                'crf': '23'
            }
            
            builder.add_output(output_file, output_options)
            
            # 构建命令
            cmd = builder.build()
            
            # 添加映射
            output_file_index = cmd.index(output_file)
            cmd.insert(output_file_index, '-map')
            cmd.insert(output_file_index + 1, '[corrected]')
            cmd.insert(output_file_index + 2, '-map')
            cmd.insert(output_file_index + 3, '0:a?')  # 可选音频流
            
            if not builder.validate_command(cmd):
                raise ProcessingError("FFmpeg色彩校正命令验证失败")
            
            status_obj.progress = 35
            status_obj.message = "正在进行色彩校正..."
            
            # 执行处理
            await ffmpeg_executor.execute_command_with_progress(
                cmd, task_id, status_obj
            )
            
            # 验证输出文件
            if not os.path.exists(output_file):
                raise ProcessingError(f"色彩校正失败，输出文件不存在: {output_file}")
            
            # 获取输出文件信息
            output_info = await video_validator.validate_video_file(output_file)
            
            status_obj.progress = 100
            status_obj.message = "色彩校正完成"
            
            logger.info(f"色彩校正完成: {input_file} -> {output_file}")
            logger.info(f"校正参数: 色温={temperature}, 色调={tint}, 高光={highlights}, "
                       f"阴影={shadows}, 自然饱和度={vibrance}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"色彩校正失败: {str(e)}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            raise ProcessingError(f"色彩校正失败: {str(e)}")

# 全局视频合成器实例
video_composer = VideoComposer()


# === 音频处理相关API端点 ===

class AudioProcessingParams(BaseModel):
    operation: str  # 操作类型: volume_adjustment, format_conversion, audio_extraction, multi_track_mixing
    input_file: Optional[str] = None  # 输入音频文件
    audio_files: Optional[List[str]] = None  # 多个音频文件（用于混合）
    output_format: str = "mp3"  # 输出格式
    
    # 音量调整参数
    volume_factor: float = 1.0
    fade_in_duration: float = 0.0
    fade_out_duration: float = 0.0
    
    # 格式转换参数
    bitrate: str = "128k"
    sample_rate: int = 44100
    
    # 音频提取参数
    start_time: float = 0.0
    duration: Optional[float] = None
    
    # 多轨混合参数
    weights: Optional[List[float]] = None

@app.post("/process_audio")
async def process_audio(request: AudioProcessingParams, background_tasks: BackgroundTasks):
    """
    启动音频处理任务
    
    支持的操作类型:
    - volume_adjustment: 音频音量调整
    - format_conversion: 音频格式转换
    - audio_extraction: 从视频提取音频
    - multi_track_mixing: 多轨音频混合
    """
    try:
        # 基本输入验证
        if request.operation == "volume_adjustment":
            if not request.input_file:
                raise HTTPException(status_code=400, detail="音量调整需要提供输入音频文件")
        elif request.operation == "format_conversion":
            if not request.input_file:
                raise HTTPException(status_code=400, detail="格式转换需要提供输入音频文件")
        elif request.operation == "audio_extraction":
            if not request.input_file:
                raise HTTPException(status_code=400, detail="音频提取需要提供输入视频文件")
        elif request.operation == "multi_track_mixing":
            if not request.audio_files or len(request.audio_files) < 2:
                raise HTTPException(status_code=400, detail="多轨混合至少需要2个音频文件")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {request.operation}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建状态对象
        status = CompositionStatus()
        status.start_time = time.time()
        composition_status[task_id] = status
        
        # 启动后台任务
        background_tasks.add_task(process_audio_async, request, task_id)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "音频处理任务已启动，请使用task_id查询进度",
            "operation": request.operation
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"启动音频处理任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动音频处理任务失败: {str(e)}")

async def process_audio_async(request: AudioProcessingParams, task_id: str):
    """异步音频处理任务"""
    status = composition_status[task_id]
    
    try:
        status.status = "processing"
        status.message = "开始音频处理..."
        status.progress = 0
        
        # 生成输出文件名
        timestamp = int(time.time())
        if request.operation == "volume_adjustment":
            output_file = f"{COMPOSITION_DIR}/{task_id}_volume_adjusted.{request.output_format}"
        elif request.operation == "format_conversion":
            output_file = f"{COMPOSITION_DIR}/{task_id}_converted.{request.output_format}"
        elif request.operation == "audio_extraction":
            output_file = f"{COMPOSITION_DIR}/{task_id}_extracted.{request.output_format}"
        elif request.operation == "multi_track_mixing":
            output_file = f"{COMPOSITION_DIR}/{task_id}_mixed.{request.output_format}"
        else:
            raise ProcessingError(f"不支持的操作类型: {request.operation}")
        
        # 确保输出目录存在
        os.makedirs(COMPOSITION_DIR, exist_ok=True)
        
        # 根据操作类型执行不同的处理
        if request.operation == "volume_adjustment":
            result = await video_composer.adjust_audio_volume(
                input_file=request.input_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                volume_factor=request.volume_factor,
                fade_in_duration=request.fade_in_duration,
                fade_out_duration=request.fade_out_duration,
                output_format=request.output_format
            )
            
        elif request.operation == "format_conversion":
            result = await video_composer.convert_audio_format(
                input_file=request.input_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                output_format=request.output_format,
                bitrate=request.bitrate,
                sample_rate=request.sample_rate
            )
            
        elif request.operation == "audio_extraction":
            result = await video_composer.extract_audio_from_video(
                input_file=request.input_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                start_time=request.start_time,
                duration=request.duration,
                output_format=request.output_format
            )
            
        elif request.operation == "multi_track_mixing":
            result = await video_composer.mix_multiple_audio_tracks(
                audio_files=request.audio_files,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                weights=request.weights,
                output_format=request.output_format
            )
        
        # 获取输出文件信息
        if os.path.exists(result):
            file_size = os.path.getsize(result)
            
            # 获取音频信息
            try:
                info_dict = await ffmpeg_executor.get_video_info(result)
                audio_stream = None
                for stream in info_dict.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                if audio_stream:
                    duration = float(audio_stream.get('duration', 0))
                    sample_rate = int(audio_stream.get('sample_rate', 0))
                    channels = int(audio_stream.get('channels', 0))
                else:
                    duration = 0
                    sample_rate = 0
                    channels = 0
            except:
                duration = 0
                sample_rate = 0
                channels = 0
        else:
            raise ProcessingError(f"输出文件不存在: {result}")
        
        # 设置完成状态
        status.status = "completed"
        status.progress = 100
        status.message = "音频处理完成"
        status.result = {
            "output_file_path": result,
            "file_size": file_size,
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "format": request.output_format,
            "operation": request.operation,
            "processing_time": time.time() - status.start_time
        }
        
        logger.info(f"音频处理任务完成: {task_id} - {request.operation}")
        
    except Exception as e:
        logger.error(f"音频处理任务失败: {task_id} - {str(e)}")
        status.status = "failed"
        status.error = str(e)
        status.message = f"音频处理失败: {str(e)}"


# === 水印和滤镜相关API端点 ===

class WatermarkParams(BaseModel):
    operation: str  # 操作类型: image_watermark, text_watermark, video_filters, color_correction
    input_file: str  # 输入视频文件
    output_format: str = "mp4"  # 输出格式
    
    # 图片水印参数
    watermark_image: Optional[str] = None
    position: str = "bottom-right"
    opacity: float = 0.8
    scale: float = 0.1
    
    # 文字水印参数
    text: Optional[str] = None
    font_size: int = 24
    font_color: str = "white"
    font_file: Optional[str] = None
    
    # 视频滤镜参数
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    blur: float = 0.0
    sharpen: float = 0.0
    gamma: float = 1.0
    
    # 色彩校正参数
    temperature: float = 0.0
    tint: float = 0.0
    highlights: float = 0.0
    shadows: float = 0.0
    vibrance: float = 0.0

@app.post("/apply_watermark_filter")
async def apply_watermark_filter(request: WatermarkParams, background_tasks: BackgroundTasks):
    """
    应用水印和滤镜
    
    支持的操作类型:
    - image_watermark: 添加图片水印
    - text_watermark: 添加文字水印
    - video_filters: 应用基础视频滤镜
    - color_correction: 色彩校正
    """
    try:
        # 基本输入验证
        if request.operation == "image_watermark":
            if not request.watermark_image:
                raise HTTPException(status_code=400, detail="图片水印需要提供水印图片文件")
        elif request.operation == "text_watermark":
            if not request.text:
                raise HTTPException(status_code=400, detail="文字水印需要提供水印文字")
        elif request.operation not in ["video_filters", "color_correction"]:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {request.operation}")
        
        if not request.input_file:
            raise HTTPException(status_code=400, detail="必须提供输入视频文件")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建状态对象
        status = CompositionStatus()
        status.start_time = time.time()
        composition_status[task_id] = status
        
        # 启动后台任务
        background_tasks.add_task(apply_watermark_filter_async, request, task_id)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "水印/滤镜应用任务已启动，请使用task_id查询进度",
            "operation": request.operation
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"启动水印/滤镜任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动水印/滤镜任务失败: {str(e)}")

async def apply_watermark_filter_async(request: WatermarkParams, task_id: str):
    """异步水印/滤镜应用任务"""
    status = composition_status[task_id]
    
    try:
        status.status = "processing"
        status.message = "开始应用水印/滤镜..."
        status.progress = 0
        
        # 生成输出文件名
        timestamp = int(time.time())
        if request.operation == "image_watermark":
            output_file = f"{COMPOSITION_DIR}/{task_id}_image_watermark.{request.output_format}"
        elif request.operation == "text_watermark":
            output_file = f"{COMPOSITION_DIR}/{task_id}_text_watermark.{request.output_format}"
        elif request.operation == "video_filters":
            output_file = f"{COMPOSITION_DIR}/{task_id}_filtered.{request.output_format}"
        elif request.operation == "color_correction":
            output_file = f"{COMPOSITION_DIR}/{task_id}_color_corrected.{request.output_format}"
        else:
            raise ProcessingError(f"不支持的操作类型: {request.operation}")
        
        # 确保输出目录存在
        os.makedirs(COMPOSITION_DIR, exist_ok=True)
        
        # 根据操作类型执行不同的处理
        if request.operation == "image_watermark":
            result = await video_composer.add_image_watermark(
                input_file=request.input_file,
                watermark_image=request.watermark_image,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                position=request.position,
                opacity=request.opacity,
                scale=request.scale
            )
            
        elif request.operation == "text_watermark":
            result = await video_composer.add_text_watermark(
                input_file=request.input_file,
                text=request.text,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                position=request.position,
                font_size=request.font_size,
                font_color=request.font_color,
                opacity=request.opacity,
                font_file=request.font_file
            )
            
        elif request.operation == "video_filters":
            result = await video_composer.apply_video_filters(
                input_file=request.input_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                brightness=request.brightness,
                contrast=request.contrast,
                saturation=request.saturation,
                blur=request.blur,
                sharpen=request.sharpen,
                gamma=request.gamma
            )
            
        elif request.operation == "color_correction":
            result = await video_composer.apply_color_correction(
                input_file=request.input_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                temperature=request.temperature,
                tint=request.tint,
                highlights=request.highlights,
                shadows=request.shadows,
                vibrance=request.vibrance
            )
        
        # 获取输出文件信息
        if os.path.exists(result):
            file_size = os.path.getsize(result)
            
            # 获取视频信息
            try:
                output_info = await video_validator.validate_video_file(result)
                duration = output_info.duration
                resolution = f"{output_info.width}x{output_info.height}"
            except:
                duration = 0
                resolution = "unknown"
        else:
            raise ProcessingError(f"输出文件不存在: {result}")
        
        # 设置完成状态
        status.status = "completed"
        status.progress = 100
        status.message = "水印/滤镜应用完成"
        status.result = {
            "output_file_path": result,
            "file_size": file_size,
            "duration": duration,
            "resolution": resolution,
            "format": request.output_format,
            "operation": request.operation,
            "processing_time": time.time() - status.start_time
        }
        
        logger.info(f"水印/滤镜任务完成: {task_id} - {request.operation}")
        
    except Exception as e:
        logger.error(f"水印/滤镜任务失败: {task_id} - {str(e)}")
        status.status = "failed"
        status.error = str(e)
        status.message = f"水印/滤镜应用失败: {str(e)}"


def check_video_duration_limit(video_metadata):
    """检查视频时长是否超过限制"""
    duration = video_metadata.get('duration', 0)
    max_duration = 10800  # 增加到3小时限制，以支持更长的视频
    
    if duration > max_duration:
        raise HTTPException(
            status_code=413, 
            detail=f"视频时长 ({duration/60:.1f}分钟) 超过限制 ({max_duration/60:.1f}分钟)"
        )
    
    return duration

def check_video_file_size_limit(video_metadata, quality="best"):
    """检查视频文件大小是否超过限制"""
    # 估算文件大小（基于时长和质量）
    duration = video_metadata.get('duration', 0)
    
    # 不同质量的大致比特率 (kbps)
    quality_bitrates = {
        "1080p": 5000,
        "720p": 2500,
        "480p": 1000,
        "best": 5000,  # 假设最高质量
        "worst": 500
    }
    
    bitrate = quality_bitrates.get(quality, 2500)
    estimated_size_mb = (duration * bitrate * 1000) / (8 * 1024 * 1024)  # 转换为MB
    max_size_mb = 2048  # 2GB限制
    
    if estimated_size_mb > max_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"预估视频文件大小 ({estimated_size_mb:.1f}MB) 超过限制 ({max_size_mb}MB)"
        )
    
    return estimated_size_mb

async def get_available_formats(video_url: str):
    """获取视频的可用格式信息"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        
        if process.returncode == 0:
            metadata = json.loads(stdout.decode())
            formats = metadata.get('formats', [])
            
            # 整理格式信息
            video_formats = []
            for fmt in formats:
                if fmt.get('vcodec') != 'none':  # 只要视频格式
                    video_formats.append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'height': fmt.get('height'),
                        'width': fmt.get('width'),
                        'filesize': fmt.get('filesize'),
                        'tbr': fmt.get('tbr'),  # 总比特率
                        'vbr': fmt.get('vbr'),  # 视频比特率
                        'format_note': fmt.get('format_note', ''),
                        'quality': fmt.get('quality', 0)
                    })
            
            return video_formats
        else:
            logger.error(f"获取格式信息失败: {stderr.decode()}")
            return []
            
    except Exception as e:
        logger.error(f"获取格式信息异常: {e}")
        return []

def select_best_format_for_quality(formats, target_quality, target_format):
    """根据目标质量选择最佳格式"""
    if not formats:
        return None
    
    # 定义质量映射
    quality_heights = {
        "480p": 480,
        "720p": 720,
        "1080p": 1080,
        "1440p": 1440,
        "2160p": 2160
    }
    
    if target_quality == "best":
        # 选择最高质量
        best_format = max(formats, key=lambda x: (x.get('height', 0), x.get('tbr', 0)))
        return best_format
    elif target_quality == "worst":
        # 选择最低质量
        worst_format = min(formats, key=lambda x: (x.get('height', 9999), x.get('tbr', 9999)))
        return worst_format
    elif target_quality in quality_heights:
        target_height = quality_heights[target_quality]
        
        # 首先尝试找到精确匹配的高度
        exact_matches = [f for f in formats if f.get('height') == target_height]
        if exact_matches:
            # 在精确匹配中选择最佳格式和比特率
            preferred_format = None
            for fmt in exact_matches:
                if fmt.get('ext') == target_format:
                    if not preferred_format or fmt.get('tbr', 0) > preferred_format.get('tbr', 0):
                        preferred_format = fmt
            
            if preferred_format:
                return preferred_format
            else:
                # 如果没有指定格式，选择比特率最高的
                return max(exact_matches, key=lambda x: x.get('tbr', 0))
        
        # 如果没有精确匹配，选择最接近且不超过目标高度的格式
        suitable_formats = [f for f in formats if f.get('height', 0) <= target_height and f.get('height', 0) > 0]
        if suitable_formats:
            # 选择最接近目标高度的格式
            closest_format = max(suitable_formats, key=lambda x: (x.get('height', 0), x.get('tbr', 0)))
            return closest_format
        
        # 如果都没有，选择最小的可用格式
        return min(formats, key=lambda x: (x.get('height', 9999), x.get('tbr', 9999)))
    
    return None

def get_download_progress_hook(task_id: str):
    """创建yt-dlp下载进度钩子"""
    def progress_hook(d):
        if task_id not in download_status:
            return
            
        status = download_status[task_id]
        
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                status.file_size = d['total_bytes']
                status.downloaded_size = d.get('downloaded_bytes', 0)
                progress = (status.downloaded_size / status.file_size) * 70  # 下载占70%进度
                status.progress = min(90, 20 + progress)
                status.message = f"下载中... {status.downloaded_size / 1024 / 1024:.1f}MB / {status.file_size / 1024 / 1024:.1f}MB"
            elif 'total_bytes_estimate' in d:
                estimated_size = d['total_bytes_estimate']
                downloaded = d.get('downloaded_bytes', 0)
                progress = (downloaded / estimated_size) * 70
                status.progress = min(90, 20 + progress)
                status.message = f"下载中... {downloaded / 1024 / 1024:.1f}MB"
        elif d['status'] == 'finished':
            status.progress = 90
            status.message = "下载完成，正在处理..."
            status.file_path = d['filename']
    
    return progress_hook

async def extract_keyframes_async(video_url: str, task_id: str, method: str = "interval", 
                                interval: int = 30, timestamps: list = None, count: int = 10,
                                width: int = 1280, height: int = 720, format: str = "jpg", quality: int = 85):
    """异步提取视频关键帧"""
    try:
        status = keyframe_status[task_id]
        status.message = "获取视频信息..."
        status.progress = 10
        
        # 获取视频元数据
        get_meta_cmd = [
            'yt-dlp',
            '-v',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *get_meta_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, get_meta_cmd, stderr.decode())
            
        video_metadata = json.loads(stdout.decode())
        
        # 检查视频时长
        video_duration = check_video_duration_limit(video_metadata)
        video_id = video_metadata.get('id', '')
        video_title = video_metadata.get('title', 'unknown')
        
        # 创建任务专用目录
        task_dir = os.path.join(KEYFRAME_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # 首先需要获取视频文件
        status.message = "准备视频文件..."
        status.progress = 20
        
        # 检查是否已有下载的视频文件
        video_file = None
        potential_files = [
            os.path.join(DOWNLOAD_DIR, f"{video_id}_best.mp4"),
            os.path.join(DOWNLOAD_DIR, f"{video_id}_720p.mp4"),
            os.path.join(DOWNLOAD_DIR, f"{video_id}_1080p.mp4"),
        ]
        
        for file_path in potential_files:
            if os.path.exists(file_path):
                video_file = file_path
                logger.info(f"任务 {task_id} 使用已存在的视频文件: {video_file}")
                break
        
        if not video_file:
            # 下载视频文件用于关键帧提取
            status.message = "下载视频文件..."
            video_file = await download_video_for_keyframes(video_url, video_id, task_dir)
        
        # 根据方法生成时间点列表
        status.message = "计算提取时间点..."
        status.progress = 30
        
        if method == "interval":
            # 按间隔提取
            time_points = list(range(0, int(video_duration), interval))
        elif method == "timestamps":
            # 指定时间点
            time_points = timestamps or []
        elif method == "count":
            # 平均分布
            if count > 1:
                step = video_duration / (count - 1)
                time_points = [i * step for i in range(count)]
            else:
                time_points = [video_duration / 2]  # 中间点
        elif method == "keyframes":
            # 真正的关键帧检测
            time_points = await detect_keyframes(video_file, video_duration)
        else:
            raise ValueError(f"不支持的提取方法: {method}")
        
        status.total_frames = len(time_points)
        logger.info(f"任务 {task_id} 将提取 {status.total_frames} 个关键帧")
        
        # 提取关键帧
        status.message = f"开始提取关键帧 (共{status.total_frames}帧)..."
        status.progress = 40
        
        frames_info = []
        
        for i, timestamp in enumerate(time_points):
            try:
                frame_filename = f"frame_{int(timestamp):06d}.{format}"
                frame_path = os.path.join(task_dir, frame_filename)
                
                # 使用FFmpeg提取单帧
                await extract_single_frame(video_file, timestamp, frame_path, width, height, format, quality)
                
                if os.path.exists(frame_path):
                    frame_size = os.path.getsize(frame_path)
                    frames_info.append({
                        "index": i,
                        "timestamp": timestamp,
                        "filename": frame_filename,
                        "path": frame_path,
                        "size": frame_size,
                        "width": width,
                        "height": height,
                        "format": format
                    })
                    
                    status.extracted_frames += 1
                    progress = 40 + (status.extracted_frames / status.total_frames) * 50
                    status.progress = min(90, progress)
                    status.message = f"已提取 {status.extracted_frames}/{status.total_frames} 帧"
                    
                    logger.info(f"任务 {task_id} 提取帧 {i+1}/{status.total_frames}: {timestamp}s")
                else:
                    logger.warning(f"任务 {task_id} 帧提取失败: {timestamp}s")
                    
            except Exception as e:
                logger.error(f"任务 {task_id} 提取帧 {timestamp}s 时出错: {e}")
                continue
        
        # 生成缩略图（可选）
        status.message = "生成缩略图..."
        status.progress = 95
        
        thumbnail_path = None
        if frames_info:
            try:
                thumbnail_path = await create_thumbnail_grid(frames_info, task_dir, width, height)
            except Exception as e:
                logger.warning(f"任务 {task_id} 生成缩略图失败: {e}")
        
        # 完成处理
        status.status = "completed"
        status.progress = 100
        status.message = f"关键帧提取完成，共提取 {len(frames_info)} 帧"
        status.frames = frames_info
        status.result = {
            "title": video_metadata.get('title', ''),
            "id": video_metadata.get('id', ''),
            "duration": round(video_duration, 2),
            "author": video_metadata.get('uploader') or video_metadata.get('channel', '未知作者'),
            "video_url": video_url,
            "method": method,
            "total_frames": len(frames_info),
            "frames": frames_info,
            "thumbnail_path": thumbnail_path,
            "task_dir": task_dir,
            "extraction_params": {
                "method": method,
                "interval": interval,
                "timestamps": timestamps,
                "count": count,
                "width": width,
                "height": height,
                "format": format,
                "quality": quality
            }
        }
        
        logger.info(f"关键帧提取任务 {task_id} 完成，提取了 {len(frames_info)} 帧")
        
    except Exception as e:
        logger.exception(f"关键帧提取任务 {task_id} 失败: {e}")
        status.status = "failed"
        status.error = str(e)
        status.message = f"关键帧提取失败: {str(e)}"

async def download_video_for_keyframes(video_url: str, video_id: str, task_dir: str):
    """为关键帧提取下载视频文件或复制本地文件"""
    # 检查是否为本地文件
    if is_local_file(video_url):
        return await prepare_local_video_for_processing(video_url, video_id, task_dir)
    
    # 在线视频下载逻辑
    output_filename = os.path.join(task_dir, f"{video_id}_keyframe_source.%(ext)s")
    
    # 对于B站等需要合并音视频流的网站，不指定格式让yt-dlp自动选择和合并
    download_cmd = [
        'yt-dlp',
        '-v',
        '--no-playlist',
        '--no-warnings',
        '-o', output_filename,
        '--force-overwrite',
        video_url
    ]
    
    process = await asyncio.create_subprocess_exec(
        *download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1800)  # 30分钟超时
    
    if process.returncode != 0:
        logger.warning(f"yt-dlp返回非零退出码: {process.returncode}, stderr: {stderr.decode()}")
        # 不立即抛出异常，先检查是否有文件生成
    
    # 查找生成的视频文件（可能是mp4, webm, mkv等格式）
    import glob
    pattern = output_filename.replace('.%(ext)s', '.*')
    found_files = glob.glob(pattern)
    
    if found_files:
        # 选择最新的文件
        found_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        actual_file = found_files[0]
        logger.info(f"找到下载的视频文件: {actual_file}")
        return actual_file
    else:
        # 如果没找到，尝试在整个任务目录中查找视频文件
        video_extensions = ['*.mp4', '*.webm', '*.mkv', '*.avi', '*.mov']
        for ext in video_extensions:
            pattern = os.path.join(task_dir, ext)
            found_files = glob.glob(pattern)
            if found_files:
                found_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
                actual_file = found_files[0]
                logger.info(f"在任务目录中找到视频文件: {actual_file}")
                return actual_file
        
        raise FileNotFoundError("视频文件下载失败")

async def prepare_local_video_for_processing(video_path: str, video_id: str, task_dir: str):
    """准备本地视频文件用于处理"""
    # 处理file://协议
    if video_path.startswith('file://'):
        video_path = video_path[7:]
    
    # 转换为绝对路径
    video_path = os.path.abspath(video_path)
    
    # 验证文件存在
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"本地视频文件不存在: {video_path}")
    
    # 获取文件扩展名
    file_extension = os.path.splitext(video_path)[1]
    
    # 在任务目录中创建符号链接或复制文件
    target_filename = f"{video_id}_local_source{file_extension}"
    target_path = os.path.join(task_dir, target_filename)
    
    try:
        # 尝试创建符号链接（更高效）
        if os.name != 'nt':  # Unix/Linux/macOS
            os.symlink(video_path, target_path)
            logger.info(f"创建本地视频符号链接: {video_path} -> {target_path}")
        else:  # Windows
            shutil.copy2(video_path, target_path)
            logger.info(f"复制本地视频文件: {video_path} -> {target_path}")
    except OSError:
        # 如果符号链接失败，则复制文件
        shutil.copy2(video_path, target_path)
        logger.info(f"复制本地视频文件: {video_path} -> {target_path}")
    
    return target_path

async def detect_keyframes(video_file: str, duration: float):
    """检测视频的真正关键帧"""
    try:
        # 使用FFprobe获取关键帧信息
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-select_streams', 'v:0',
            '-show_entries', 'frame=pkt_pts_time',
            '-of', 'csv=p=0',
            '-skip_frame', 'nokey',
            video_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        
        if process.returncode == 0:
            keyframe_times = []
            for line in stdout.decode().strip().split('\n'):
                if line.strip():
                    try:
                        timestamp = float(line.strip())
                        if 0 <= timestamp <= duration:
                            keyframe_times.append(timestamp)
                    except ValueError:
                        continue
            
            # 限制关键帧数量，避免过多
            if len(keyframe_times) > 50:
                step = len(keyframe_times) // 50
                keyframe_times = keyframe_times[::step]
            
            return keyframe_times
        else:
            logger.warning(f"关键帧检测失败，使用间隔模式: {stderr.decode()}")
            # 回退到间隔模式
            return list(range(0, int(duration), 30))
            
    except Exception as e:
        logger.error(f"关键帧检测异常: {e}")
        # 回退到间隔模式
        return list(range(0, int(duration), 30))

async def extract_single_frame(video_file: str, timestamp: float, output_path: str, 
                             width: int, height: int, format: str, quality: int):
    """提取单个帧"""
    cmd = [
        'ffmpeg',
        '-ss', str(timestamp),
        '-i', video_file,
        '-vframes', '1',
        '-vf', f'scale={width}:{height}',
        '-y'  # 覆盖输出文件
    ]
    
    # 根据格式添加质量参数
    if format.lower() == 'jpg' or format.lower() == 'jpeg':
        cmd.extend(['-q:v', str(max(1, min(31, 31 - quality // 3)))])  # FFmpeg的质量范围是1-31，数值越小质量越高
    elif format.lower() == 'png':
        cmd.extend(['-compression_level', '6'])
    
    cmd.append(output_path)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
    
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd, stderr.decode())

async def create_thumbnail_grid(frames_info: list, task_dir: str, frame_width: int, frame_height: int):
    """创建缩略图网格"""
    try:
        from PIL import Image
        import math
        
        if not frames_info:
            return None
        
        # 计算网格尺寸
        total_frames = len(frames_info)
        cols = min(4, total_frames)  # 最多4列
        rows = math.ceil(total_frames / cols)
        
        # 缩略图中每个小图的尺寸
        thumb_width = 200
        thumb_height = int(thumb_width * frame_height / frame_width)
        
        # 创建网格图片
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (0, 0, 0))
        
        for i, frame_info in enumerate(frames_info):
            try:
                frame_image = Image.open(frame_info['path'])
                frame_image = frame_image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
                
                row = i // cols
                col = i % cols
                x = col * thumb_width
                y = row * thumb_height
                
                grid_image.paste(frame_image, (x, y))
                frame_image.close()
                
            except Exception as e:
                logger.warning(f"处理缩略图帧 {i} 失败: {e}")
                continue
        
        thumbnail_path = os.path.join(task_dir, 'thumbnail_grid.jpg')
        grid_image.save(thumbnail_path, 'JPEG', quality=85)
        grid_image.close()
        
        return thumbnail_path
        
    except ImportError:
        logger.warning("PIL未安装，跳过缩略图生成")
        return None
    except Exception as e:
        logger.error(f"生成缩略图网格失败: {e}")
        return None

async def download_video_async(video_url: str, task_id: str, quality: str = "best", format: str = "mp4"):
    """异步下载视频文件"""
    try:
        status = download_status[task_id]
        
        # 检查缓存
        processing_params = {
            'quality': quality,
            'format': format,
            'operation': 'download'
        }
        
        cached_video = performance_optimizer.cache_manager.get_processed_video_cache(
            video_url, processing_params
        )
        
        if cached_video and os.path.exists(cached_video):
            logger.info(f"任务 {task_id} 命中下载缓存: {cached_video}")
            
            # 复制缓存文件到输出目录
            video_id = hashlib.md5(video_url.encode()).hexdigest()[:8]
            output_filename = os.path.join(DOWNLOAD_DIR, f"{video_id}_{quality}.{format}")
            shutil.copy2(cached_video, output_filename)
            
            status.status = "completed"
            status.progress = 100
            status.message = "下载完成 (使用缓存)"
            status.output_file = output_filename
            status.end_time = time.time()
            
            return output_filename
        
        status.message = "获取视频信息..."
        status.progress = 10
        
        # 获取视频元数据
        get_meta_cmd = [
            'yt-dlp',
            '-v',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *get_meta_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, get_meta_cmd, stderr.decode())
            
        video_metadata = json.loads(stdout.decode())
        
        # 检查视频时长和文件大小
        video_duration = check_video_duration_limit(video_metadata)
        estimated_size = check_video_file_size_limit(video_metadata, quality)
        
        video_id = video_metadata.get('id', '')
        video_title = video_metadata.get('title', 'unknown')
        
        # 获取可用格式信息
        status.message = "分析可用视频格式..."
        status.progress = 15
        
        available_formats = await get_available_formats(video_url)
        selected_format = select_best_format_for_quality(available_formats, quality, format)
        
        if selected_format:
            actual_height = selected_format.get('height', 0)
            actual_format = selected_format.get('ext', format)
            format_id = selected_format.get('format_id')
            estimated_filesize = selected_format.get('filesize', 0)
            
            logger.info(f"任务 {task_id} 选择格式: ID={format_id}, 分辨率={actual_height}p, 格式={actual_format}, 预估大小={estimated_filesize}")
            
            # 如果有确切的文件大小，使用它
            if estimated_filesize:
                estimated_size = estimated_filesize / 1024 / 1024  # 转换为MB
        else:
            logger.warning(f"任务 {task_id} 无法找到合适的格式，使用默认选择")
            actual_height = 0
            actual_format = format
            format_id = None
        
        # 构建输出文件名
        safe_title = re.sub(r'[^\w\s-]', '', video_title).strip()[:50]  # 安全的文件名
        output_filename = os.path.join(DOWNLOAD_DIR, f"{video_id}_{quality}.%(ext)s")
        
        status.message = f"开始下载视频 ({estimated_size:.1f}MB, {actual_height}p)..."
        status.progress = 20
        
        # 构建下载命令
        download_cmd = [
            'yt-dlp',
            '-v',
            '--no-playlist',
            '--no-warnings',
            '-o', output_filename,
            '--force-overwrite'
        ]
        
        # 使用更精确的格式选择
        if selected_format and format_id:
            # 直接使用格式ID，这是最精确的方式
            download_cmd.extend(['-f', format_id])
            logger.info(f"任务 {task_id} 使用格式ID: {format_id}")
        else:
            # 回退到原来的逻辑，但改进格式选择器
            if quality == "best":
                download_cmd.extend(['-f', f'best[ext={format}]/best'])
            elif quality == "worst":
                download_cmd.extend(['-f', f'worst[ext={format}]/worst'])
            elif quality in ["1080p", "720p", "480p"]:
                height = quality[:-1]  # 移除'p'
                # 使用更精确的格式选择器
                format_selector = f'best[height={height}][ext={format}]/best[height={height}]/bestvideo[height={height}]+bestaudio/best[height<={height}][ext={format}]/best[height<={height}]/best'
                download_cmd.extend(['-f', format_selector])
                logger.info(f"任务 {task_id} 使用格式选择器: {format_selector}")
        
        download_cmd.append(video_url)
        
        # 创建进度钩子
        progress_hook = get_download_progress_hook(task_id)
        
        # 设置下载超时（基于预估文件大小）
        if estimated_size > 1000:  # 大于1GB
            download_timeout = 7200  # 2小时
        elif estimated_size > 500:  # 大于500MB
            download_timeout = 3600  # 1小时
        else:
            download_timeout = 1800  # 30分钟
        
        logger.info(f"下载任务 {task_id} 开始，预估大小: {estimated_size:.1f}MB，超时: {download_timeout}秒")
        
        # 执行下载
        process = await asyncio.create_subprocess_exec(
            *download_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 监控下载进度
        async def monitor_download():
            while process.returncode is None:
                await asyncio.sleep(2)
                # 这里可以添加更多的进度监控逻辑
        
        # 等待下载完成
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=download_timeout)
        
        if process.returncode != 0:
            logger.warning(f"下载任务 {task_id} yt-dlp返回退出码 {process.returncode}, stderr: {stderr.decode()}")
            # 检查是否有文件生成
            pattern = output_filename.replace('%(ext)s', '*')
            import glob
            found_files = glob.glob(pattern)
            if not found_files:
                raise subprocess.CalledProcessError(process.returncode, download_cmd, stderr.decode())
            else:
                logger.info(f"下载任务 {task_id} 尽管有警告，但文件已成功生成")
                status.file_path = found_files[0]
        else:
            # 查找生成的文件
            pattern = output_filename.replace('%(ext)s', '*')
            import glob
            found_files = glob.glob(pattern)
            if found_files:
                status.file_path = found_files[0]
            else:
                raise FileNotFoundError("无法定位已下载的视频文件")
        
        # 获取实际文件大小
        if status.file_path and os.path.exists(status.file_path):
            actual_size = os.path.getsize(status.file_path)
            status.file_size = actual_size
        
        # 获取实际下载的文件信息
        actual_file_format = actual_format if 'actual_format' in locals() else format
        actual_resolution = f"{actual_height}p" if 'actual_height' in locals() and actual_height > 0 else quality
        
        status.status = "completed"
        status.progress = 100
        status.message = "下载完成"
        status.result = {
            "title": video_metadata.get('title', ''),
            "id": video_metadata.get('id', ''),
            "duration": round(video_duration, 2),
            "author": video_metadata.get('uploader') or video_metadata.get('channel', '未知作者'),
            "video_url": video_url,
            "description": video_metadata.get('description', ''),
            "thumbnail": video_metadata.get('thumbnail', ''),
            "file_path": status.file_path,
            "file_size": status.file_size,
            "requested_quality": quality,
            "requested_format": format,
            "actual_resolution": actual_resolution,
            "actual_format": actual_file_format,
            "format_id": format_id if 'format_id' in locals() else None,
            "available_formats_count": len(available_formats) if 'available_formats' in locals() else 0,
            "like_count": video_metadata.get('like_count', 0),
            "view_count": video_metadata.get('view_count', 0),
            "comment_count": video_metadata.get('comment_count', 0),
            "tags": video_metadata.get('tags', []),
            "timestamp": video_metadata.get('timestamp', 0)
        }
        
        logger.info(f"下载任务 {task_id} 完成，文件大小: {status.file_size / 1024 / 1024:.1f}MB")
        
        # 保存到缓存
        if status.file_path and os.path.exists(status.file_path):
            try:
                performance_optimizer.cache_manager.set_processed_video_cache(
                    video_url, processing_params, status.file_path
                )
                logger.debug(f"任务 {task_id} 已保存到下载缓存")
            except Exception as cache_error:
                logger.warning(f"保存下载缓存失败: {cache_error}")
        
    except Exception as e:
        logger.exception(f"下载任务 {task_id} 失败: {e}")
        status.status = "failed"
        status.error = str(e)
        status.message = f"下载失败: {str(e)}"

async def process_video_async(video_url: str, task_id: str):
    """异步处理视频转录"""
    try:
        status = processing_status[task_id]
        status.message = "获取视频元数据..."
        status.progress = 10
        
        # 获取视频元数据
        get_meta_cmd = [
            'yt-dlp',
            '-v',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        # 使用异步subprocess，增加元数据获取超时
        process = await asyncio.create_subprocess_exec(
            *get_meta_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)  # 增加到3分钟
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, get_meta_cmd, stderr.decode())
            
        video_metadata = json.loads(stdout.decode())
        
        # 检查视频时长
        video_duration = check_video_duration_limit(video_metadata)
        
        output_filename = os.path.join(OUTPUT_DIR, f"{video_metadata.get('id', '')}.mp3")
        
        status.message = "下载音频..."
        status.progress = 30
        
        # 下载音频
        filename_template = os.path.join(OUTPUT_DIR, '%(id)s.%(ext)s')
        download_cmd = [
            'yt-dlp',
            '-v',
            '-f', 'bestaudio/best',
            '--extract-audio',
            '--audio-format', 'mp3',
            '-o', filename_template,
            '--force-overwrite',
            '--no-playlist',
            '--no-warnings',
            video_url
        ]
        
        # 根据视频长度动态调整下载超时时间
        if video_duration > 7200:  # 超过2小时
            download_timeout = 3600  # 1小时下载超时
        elif video_duration > 3600:  # 超过1小时
            download_timeout = 2400  # 40分钟下载超时  
        else:
            download_timeout = min(1800, max(600, video_duration * 0.5))  # 最少10分钟，最多30分钟
        
        logger.info(f"任务 {task_id} 开始下载，视频时长: {video_duration/60:.1f}分钟，下载超时: {download_timeout}秒")
        
        # 使用异步subprocess
        process = await asyncio.create_subprocess_exec(
            *download_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=download_timeout)
        
        # 改进的错误处理：检查文件是否生成，即使yt-dlp返回非零退出码
        if process.returncode != 0:
            logger.warning(f"任务 {task_id} yt-dlp返回退出码 {process.returncode}, stderr: {stderr.decode()}")
            # 检查文件是否实际生成（yt-dlp有时会报警告但仍成功）
            if not os.path.exists(output_filename):
                # 尝试查找最新生成的音频文件
                found_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp3') and video_metadata.get('id', '') in f]
                if not found_files:
                    # 只有在确实没有文件生成时才抛出异常
                    raise subprocess.CalledProcessError(process.returncode, download_cmd, stderr.decode())
                else:
                    logger.info(f"任务 {task_id} 尽管yt-dlp报警告，但文件已成功生成")
                    found_files.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
                    output_filename = os.path.join(OUTPUT_DIR, found_files[0])
        
        if not os.path.exists(output_filename):
            found_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp3')]
            if found_files:
                found_files.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
                output_filename = os.path.join(OUTPUT_DIR, found_files[0])
            else:
                raise FileNotFoundError("无法定位已下载的音频文件。")
        
        status.message = "开始转录..."
        status.progress = 50
        
        logger.info(f"任务 {task_id} 开始转录，视频时长: {video_duration/60:.1f}分钟")
        
        # 根据视频时长优化转录设置
        if video_duration > 7200:  # 超过2小时
            beam_size = 1  # 最小beam_size以节省时间和内存
            chunk_length = 30
        elif video_duration > 3600:  # 超过1小时  
            beam_size = 2
            chunk_length = 30
        elif video_duration > 1800:  # 超过30分钟
            beam_size = 3
            chunk_length = 30
        else:
            beam_size = 5
            chunk_length = 30
        
        # 执行转录（使用线程池，但加强隔离）
        import concurrent.futures
        
        def safe_transcribe():
            """安全的转录函数，包含完整的错误处理"""
            try:
                logger.info(f"任务 {task_id} 线程开始Whisper转录")
                
                # 确保模型已加载
                model = load_whisper_model()
                
                # 执行转录
                segments, info = model.transcribe(
                    output_filename,
                    beam_size=beam_size,
                    chunk_length=chunk_length,
                    initial_prompt="输出中文简体的句子"
                )
                
                logger.info(f"任务 {task_id} 线程Whisper转录完成")
                return segments, info
                
            except Exception as e:
                logger.error(f"任务 {task_id} 线程转录失败: {e}")
                raise
        
        # 在线程池中执行转录
        loop = asyncio.get_running_loop()
        
        # 动态设置转录超时时间（基于视频长度）
        if video_duration > 7200:  # 超过2小时
            transcribe_timeout = 7200  # 2小时转录超时
        elif video_duration > 3600:  # 超过1小时
            transcribe_timeout = 3600  # 1小时转录超时
        else:
            transcribe_timeout = min(3600, max(600, video_duration * 2))  # 最少10分钟，最多1小时
        
        try:
            logger.info(f"任务 {task_id} 开始Whisper转录（线程池模式），超时: {transcribe_timeout}秒")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(executor, safe_transcribe)
                segments, info = await asyncio.wait_for(future, timeout=transcribe_timeout)
            
            logger.info(f"任务 {task_id} Whisper转录完成")
            
        except asyncio.TimeoutError:
            logger.error(f"任务 {task_id} 转录超时 ({transcribe_timeout}秒)")
            raise Exception(f"转录超时，视频时长: {video_duration/60:.1f}分钟，建议减少视频长度或联系管理员")
        except Exception as e:
            logger.error(f"任务 {task_id} 转录过程中发生错误: {e}")
            raise
        
        status.message = "处理转录结果..."
        status.progress = 80
        
        # 处理转录结果
        srt_content = []
        txt_content = []
        segment_index = 1
        processed_segments = 0
        
        # 添加内存监控
        initial_memory = check_memory_usage()
        
        for segment in segments:
            start_time = format_srt_timestamp(segment.start)
            end_time = format_srt_timestamp(segment.end)
            text = segment.text.strip()
            txt_content.append(text)
            srt_block = f"{segment_index}\n{start_time} --> {end_time}\n{text}\n"
            srt_content.append(srt_block)
            segment_index += 1
            processed_segments += 1
            
            # 每处理100个片段检查一次内存并更新进度
            if processed_segments % 100 == 0:
                current_memory = check_memory_usage()
                if current_memory > 85:
                    cleanup_memory()
                status.progress = min(95, 80 + (processed_segments / max(1, segment_index - 1)) * 15)
                
                # 对于非常长的视频，定期输出进度日志
                if processed_segments % 500 == 0:
                    logger.info(f"任务 {task_id} 已处理 {processed_segments} 个片段")
        
        # 保存文件
        base_filename = os.path.splitext(output_filename)[0]
        srt_filename = base_filename + ".srt"
        txt_filename = base_filename + ".txt"
        
        with open(srt_filename, 'w', encoding='utf-8') as f_srt:
            f_srt.write("\n".join(srt_content))
        with open(txt_filename, 'w', encoding='utf-8') as f_txt:
            f_txt.write("\n".join(txt_content))
        
        # 最终清理内存
        final_memory = check_memory_usage()
        if final_memory > initial_memory + 20:  # 内存增长超过20%
            cleanup_memory()
            logger.info(f"任务 {task_id} 完成后执行内存清理")
        
        # 完成处理
        status.status = "completed"
        status.progress = 100
        status.message = "转录完成"
        status.result = {
            "title": video_metadata.get('title', ''),
            "id": video_metadata.get('id', ''),
            "duration": round(info.duration, 2),
            "author": video_metadata.get('uploader') or video_metadata.get('channel', '未知作者'),
            "video_url": video_url,
            "description": video_metadata.get('description', ''),
            "thumbnail": video_metadata.get('thumbnail', ''),
            "text": "\n".join(txt_content),
            "srt": "\n".join(srt_content),
            "language": info.language,
            "like_count": video_metadata.get('like_count', 0),
            "view_count": video_metadata.get('view_count', 0),
            "comment_count": video_metadata.get('comment_count', 0),
            "tags": video_metadata.get('tags', []),
            "timestamp": video_metadata.get('timestamp', 0)
        }
        
        logger.info(f"转录任务 {task_id} 完成，总片段数: {processed_segments}")
        
    except Exception as e:
        logger.exception(f"转录任务 {task_id} 失败: {e}")
        status.status = "failed"
        status.error = str(e)
        status.message = f"转录失败: {str(e)}"

@app.post("/generate_text_from_video")
async def generate_text_from_video(request: RequestParams, background_tasks: BackgroundTasks):
    """
    接收视频 URL，启动异步转录任务，并返回任务ID。
    """
    # 检查系统资源限制
    can_accept_task, resource_message = resource_monitor.check_resource_limits()
    if not can_accept_task:
        raise HTTPException(
            status_code=503, 
            detail=f"系统资源不足，无法接受新任务: {resource_message}"
        )

    # 尝试加载模型（如果尚未加载）
    try:
        load_whisper_model()
    except Exception as e:
        logger.error(f"转录请求失败，无法加载 Whisper 模型: {e}")
        raise HTTPException(status_code=503, detail=f"转录服务不可用：{str(e)}")

    video_url = request.video_url.strip()
    if not video_url:
        logger.warning("收到 video_url 为空的请求。")
        raise HTTPException(status_code=400, detail="必须提供 video_url 字段。")
    
    # 验证和清理URL
    video_url = validate_and_clean_url(video_url)

    # 检查初始内存使用情况
    initial_memory = check_memory_usage()
    if initial_memory > 80:
        logger.warning(f"内存使用率过高 ({initial_memory}%)，执行垃圾回收")
        cleanup_memory()

    # 生成任务ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # 创建处理状态
    processing_status[task_id] = ProcessingStatus()
    
    logger.info(f"收到 URL 的转录请求: {video_url}，任务ID: {task_id}")
    
    # 启动后台任务
    background_tasks.add_task(process_video_async, video_url, task_id)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "转录任务已启动，请使用task_id查询进度"
    }

@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态（轻量级，不包含完整结果）"""
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    status = processing_status[task_id]
    
    response = {
        "task_id": task_id,
        "status": status.status,
        "progress": status.progress,
        "message": status.message
    }
    
    if status.status == "completed":
        # 只返回基本信息，不计算长度以避免性能问题
        response["result_available"] = True
        if status.result:
            response["result_summary"] = {
                "title": status.result.get("title", "")[:100],  # 限制长度
                "duration": status.result.get("duration", 0),
                "language": status.result.get("language", "")
            }
    elif status.status == "failed":
        response["error"] = status.error
    
    return response

@app.get("/task_result/{task_id}")
async def get_task_result(task_id: str):
    """获取任务完整结果"""
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    
    status = processing_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {status.status}")
    
    if not status.result:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    
    result = status.result.copy()
    
    # 获取结果后清理任务状态
    del processing_status[task_id]
    
    return {
        "task_id": task_id,
        "result": result
    }

# === 视频下载相关API端点 ===

@app.post("/download_video")
async def download_video(request: DownloadRequestParams, background_tasks: BackgroundTasks):
    """
    启动视频下载任务
    """
    # 检查系统资源限制
    can_accept_task, resource_message = resource_monitor.check_resource_limits()
    if not can_accept_task:
        raise HTTPException(
            status_code=503, 
            detail=f"系统资源不足，无法接受新任务: {resource_message}"
        )

    video_url = request.video_url.strip()
    if not video_url:
        logger.warning("收到 video_url 为空的下载请求。")
        raise HTTPException(status_code=400, detail="必须提供 video_url 字段。")
    
    # 验证和清理URL
    video_url = validate_and_clean_url(video_url)
    
    # 验证质量和格式参数
    valid_qualities = ["best", "worst", "1080p", "720p", "480p"]
    valid_formats = ["mp4", "webm", "mkv"]
    
    if request.quality not in valid_qualities:
        raise HTTPException(status_code=400, detail=f"不支持的质量设置: {request.quality}，支持的选项: {valid_qualities}")
    
    if request.format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {request.format}，支持的选项: {valid_formats}")

    # 检查内存使用情况
    initial_memory = check_memory_usage()
    if initial_memory > 80:
        logger.warning(f"内存使用率过高 ({initial_memory}%)，执行垃圾回收")
        cleanup_memory()

    # 生成任务ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # 创建下载状态
    download_status[task_id] = DownloadStatus()
    
    logger.info(f"收到视频下载请求: {video_url}，质量: {request.quality}，格式: {request.format}，任务ID: {task_id}")
    
    # 启动后台任务
    background_tasks.add_task(download_video_async, video_url, task_id, request.quality, request.format)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "视频下载任务已启动，请使用task_id查询进度",
        "quality": request.quality,
        "format": request.format
    }

@app.get("/download_status/{task_id}")
async def get_download_status(task_id: str):
    """获取下载任务状态（轻量级，不包含完整结果）"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    
    status = download_status[task_id]
    
    response = {
        "task_id": task_id,
        "status": status.status,
        "progress": status.progress,
        "message": status.message,
        "file_size": status.file_size,
        "downloaded_size": status.downloaded_size
    }
    
    if status.status == "completed":
        response["result_available"] = True
        if status.result:
            response["result_summary"] = {
                "title": status.result.get("title", "")[:100],
                "duration": status.result.get("duration", 0),
                "file_size": status.result.get("file_size", 0),
                "quality": status.result.get("quality", ""),
                "format": status.result.get("format", "")
            }
    elif status.status == "failed":
        response["error"] = status.error
    
    return response

@app.get("/download_result/{task_id}")
async def get_download_result(task_id: str):
    """获取下载任务完整结果"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="下载任务不存在或已过期")
    
    status = download_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"下载任务尚未完成，当前状态: {status.status}")
    
    if not status.result:
        raise HTTPException(status_code=404, detail="下载结果不存在")
    
    result = status.result.copy()
    
    # 获取结果后清理任务状态
    del download_status[task_id]
    
    return {
        "task_id": task_id,
        "result": result
    }

@app.get("/download_file/{task_id}")
async def download_file(task_id: str):
    """下载视频文件"""
    from fastapi.responses import FileResponse
    
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    
    status = download_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"下载任务尚未完成，当前状态: {status.status}")
    
    if not status.file_path or not os.path.exists(status.file_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    filename = os.path.basename(status.file_path)
    
    return FileResponse(
        path=status.file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

# === 关键帧提取相关API端点 ===

@app.post("/extract_keyframes")
async def extract_keyframes(request: KeyframeRequestParams, background_tasks: BackgroundTasks):
    """
    启动关键帧提取任务
    """
    # 检查系统资源限制
    can_accept_task, resource_message = resource_monitor.check_resource_limits()
    if not can_accept_task:
        raise HTTPException(
            status_code=503, 
            detail=f"系统资源不足，无法接受新任务: {resource_message}"
        )

    video_url = request.video_url.strip()
    if not video_url:
        logger.warning("收到 video_url 为空的关键帧提取请求。")
        raise HTTPException(status_code=400, detail="必须提供 video_url 字段。")
    
    # 验证和清理URL
    video_url = validate_and_clean_url(video_url)
    
    # 验证参数
    valid_methods = ["interval", "timestamps", "keyframes", "count"]
    if request.method not in valid_methods:
        raise HTTPException(status_code=400, detail=f"不支持的提取方法: {request.method}，支持的选项: {valid_methods}")
    
    valid_formats = ["jpg", "jpeg", "png"]
    if request.format.lower() not in valid_formats:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {request.format}，支持的选项: {valid_formats}")
    
    if request.method == "timestamps" and not request.timestamps:
        raise HTTPException(status_code=400, detail="使用timestamps方法时必须提供timestamps列表")
    
    if request.interval <= 0:
        raise HTTPException(status_code=400, detail="interval必须大于0")
    
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="count必须大于0")
    
    if not (100 <= request.width <= 3840 and 100 <= request.height <= 2160):
        raise HTTPException(status_code=400, detail="图片尺寸必须在100x100到3840x2160之间")
    
    if not (1 <= request.quality <= 100):
        raise HTTPException(status_code=400, detail="图片质量必须在1-100之间")

    # 检查内存使用情况
    initial_memory = check_memory_usage()
    if initial_memory > 80:
        logger.warning(f"内存使用率过高 ({initial_memory}%)，执行垃圾回收")
        cleanup_memory()

    # 生成任务ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # 创建关键帧提取状态
    keyframe_status[task_id] = KeyframeStatus()
    
    logger.info(f"收到关键帧提取请求: {video_url}，方法: {request.method}，任务ID: {task_id}")
    
    # 启动后台任务
    background_tasks.add_task(
        extract_keyframes_async, 
        video_url, task_id, request.method, request.interval, 
        request.timestamps, request.count, request.width, request.height, 
        request.format, request.quality
    )
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "关键帧提取任务已启动，请使用task_id查询进度",
        "method": request.method,
        "parameters": {
            "interval": request.interval if request.method == "interval" else None,
            "timestamps": request.timestamps if request.method == "timestamps" else None,
            "count": request.count if request.method == "count" else None,
            "width": request.width,
            "height": request.height,
            "format": request.format,
            "quality": request.quality
        }
    }

@app.get("/keyframe_status/{task_id}")
async def get_keyframe_status(task_id: str):
    """获取关键帧提取任务状态（轻量级，不包含完整结果）"""
    if task_id not in keyframe_status:
        raise HTTPException(status_code=404, detail="关键帧提取任务不存在")
    
    status = keyframe_status[task_id]
    
    response = {
        "task_id": task_id,
        "status": status.status,
        "progress": status.progress,
        "message": status.message,
        "total_frames": status.total_frames,
        "extracted_frames": status.extracted_frames
    }
    
    if status.status == "completed":
        response["result_available"] = True
        if status.result:
            response["result_summary"] = {
                "title": status.result.get("title", "")[:100],
                "total_frames": status.result.get("total_frames", 0),
                "method": status.result.get("method", ""),
                "duration": status.result.get("duration", 0)
            }
    elif status.status == "failed":
        response["error"] = status.error
    
    return response

@app.get("/keyframe_result/{task_id}")
async def get_keyframe_result(task_id: str):
    """获取关键帧提取任务完整结果"""
    if task_id not in keyframe_status:
        raise HTTPException(status_code=404, detail="关键帧提取任务不存在或已过期")
    
    status = keyframe_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"关键帧提取任务尚未完成，当前状态: {status.status}")
    
    if not status.result:
        raise HTTPException(status_code=404, detail="关键帧提取结果不存在")
    
    result = status.result.copy()
    
    # 获取结果后清理任务状态
    del keyframe_status[task_id]
    
    return {
        "task_id": task_id,
        "result": result
    }

@app.get("/keyframe_image/{task_id}/{frame_index}")
async def get_keyframe_image(task_id: str, frame_index: int):
    """下载特定的关键帧图片"""
    from fastapi.responses import FileResponse
    
    if task_id not in keyframe_status:
        raise HTTPException(status_code=404, detail="关键帧提取任务不存在")
    
    status = keyframe_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"关键帧提取任务尚未完成，当前状态: {status.status}")
    
    if not status.frames or frame_index < 0 or frame_index >= len(status.frames):
        raise HTTPException(status_code=404, detail="指定的帧索引不存在")
    
    frame_info = status.frames[frame_index]
    frame_path = frame_info["path"]
    
    if not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail="关键帧图片文件不存在")
    
    filename = frame_info["filename"]
    media_type = "image/jpeg" if frame_info["format"].lower() in ["jpg", "jpeg"] else "image/png"
    
    return FileResponse(
        path=frame_path,
        filename=filename,
        media_type=media_type
    )

@app.get("/keyframe_thumbnail/{task_id}")
async def get_keyframe_thumbnail(task_id: str):
    """下载关键帧缩略图网格"""
    from fastapi.responses import FileResponse
    
    if task_id not in keyframe_status:
        raise HTTPException(status_code=404, detail="关键帧提取任务不存在")
    
    status = keyframe_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"关键帧提取任务尚未完成，当前状态: {status.status}")
    
    if not status.result or not status.result.get("thumbnail_path"):
        raise HTTPException(status_code=404, detail="缩略图不存在")
    
    thumbnail_path = status.result["thumbnail_path"]
    
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="缩略图文件不存在")
    
    return FileResponse(
        path=thumbnail_path,
        filename="thumbnail_grid.jpg",
        media_type="image/jpeg"
    )

# === 视频合成相关API端点 ===

@app.post("/compose_video")
async def compose_video(request: VideoCompositionParams, background_tasks: BackgroundTasks):
    """
    启动视频合成任务
    
    支持的合成类型:
    - concat: 视频拼接
    - audio_video_subtitle: 音频视频字幕三合一合成
    - pip: 画中画合成
    - side_by_side: 并排显示
    - slideshow: 关键帧幻灯片
    """
    try:
        # 检查系统资源限制
        can_accept_task, resource_message = resource_monitor.check_resource_limits()
        if not can_accept_task:
            raise HTTPException(
                status_code=503, 
                detail=f"系统资源不足，无法接受新任务: {resource_message}"
            )
        
        # 验证合成类型
        valid_composition_types = [
            "concat", "audio_video_subtitle", "pip", "side_by_side", 
            "slideshow", "multi_overlay", "side_by_side_audio_mix"
        ]
        if request.composition_type not in valid_composition_types:
            raise HTTPException(
                status_code=400, 
                detail=f"暂不支持的合成类型: {request.composition_type}，支持的类型: {valid_composition_types}"
            )
        
        # 基本输入验证
        if request.composition_type == "slideshow":
            if not request.videos or len(request.videos) < 1:
                raise HTTPException(status_code=400, detail="幻灯片制作至少需要1个图片文件")
        elif request.composition_type == "concat":
            if len(request.videos) < 2:
                raise HTTPException(status_code=400, detail="视频拼接至少需要2个视频文件")
        elif request.composition_type == "pip":
            if len(request.videos) != 2:
                raise HTTPException(status_code=400, detail="画中画合成需要提供2个视频文件")
        elif request.composition_type == "side_by_side":
            if len(request.videos) < 2:
                raise HTTPException(status_code=400, detail="并排显示至少需要2个视频文件")
        elif request.composition_type == "audio_video_subtitle":
            if not request.videos or len(request.videos) != 1:
                raise HTTPException(status_code=400, detail="音频视频字幕合成需要提供一个视频文件")
            if not request.audio_file:
                raise HTTPException(status_code=400, detail="音频视频字幕合成需要提供音频文件")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建状态对象
        status = CompositionStatus()
        status.start_time = time.time()
        composition_status[task_id] = status
        
        # 启动后台任务
        background_tasks.add_task(compose_video_async, request, task_id)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "视频合成任务已启动，请使用task_id查询进度",
            "composition_type": request.composition_type
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"启动视频合成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动视频合成任务失败: {str(e)}")

async def compose_video_async(request: VideoCompositionParams, task_id: str):
    """异步视频合成任务"""
    try:
        status = composition_status[task_id]
        status.message = "开始视频合成..."
        status.progress = 5
        
        # 创建任务专用临时目录
        task_temp_dir = os.path.join(TEMP_COMPOSITION_DIR, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)
        status.temp_files.append(task_temp_dir)
        
        # 生成输出文件路径
        output_filename = f"{task_id}_{request.composition_type}.{request.output_format}"
        output_file = os.path.join(COMPOSITION_DIR, output_filename)
        
        # 根据合成类型执行不同的合成逻辑
        if request.composition_type == "audio_video_subtitle":
            # 音频视频字幕三合一合成
            if not request.videos or len(request.videos) != 1:
                raise InputValidationError("音频视频字幕合成需要提供一个视频文件")
            
            if not request.audio_file:
                raise InputValidationError("音频视频字幕合成需要提供音频文件")
            
            video_input = request.videos[0]
            
            result = await video_composer.compose_audio_video_subtitle(
                video_file=video_input.video_url,
                audio_file=request.audio_file,
                subtitle_file=request.subtitle_file,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                audio_offset=0.0  # 可以后续支持用户自定义
            )
            
        elif request.composition_type == "concat":
            # 视频拼接
            if len(request.videos) < 2:
                raise InputValidationError("视频拼接至少需要2个视频文件")
            
            video_files = [v.video_url for v in request.videos]
            result = await video_composer.concat_videos(
                video_files=video_files,
                output_file=output_file,
                task_id=task_id,
                status_obj=status
            )
            
        elif request.composition_type == "pip":
            # 画中画合成
            if len(request.videos) != 2:
                raise InputValidationError("画中画合成需要提供2个视频文件（主视频和叠加视频）")
            
            main_video = request.videos[0].video_url
            overlay_video = request.videos[1].video_url
            position = request.videos[1].position  # 叠加视频的位置信息
            
            result = await video_composer.picture_in_picture(
                main_video=main_video,
                overlay_video=overlay_video,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                position=position
            )
            
        elif request.composition_type == "multi_overlay":
            # 多层视频叠加
            if len(request.videos) < 2:
                raise InputValidationError("多层叠加至少需要2个视频文件")
            
            main_video = request.videos[0].video_url
            overlay_videos = []
            
            for i, video_input in enumerate(request.videos[1:], 1):
                overlay_videos.append({
                    'video_url': video_input.video_url,
                    'position': video_input.position or Position(),
                    'z_index': i
                })
            
            result = await video_composer.multi_layer_overlay(
                main_video=main_video,
                overlay_videos=overlay_videos,
                output_file=output_file,
                task_id=task_id,
                status_obj=status
            )
            
        elif request.composition_type == "side_by_side":
            # 并排视频显示
            if len(request.videos) < 2:
                raise InputValidationError("并排显示至少需要2个视频文件")
            
            video_files = [v.video_url for v in request.videos]
            layout = request.layout  # 使用请求中的布局参数
            
            result = await video_composer.side_by_side_videos(
                videos=video_files,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                layout=layout
            )
            
        elif request.composition_type == "side_by_side_audio_mix":
            # 并排视频显示并混合音频
            if len(request.videos) < 2:
                raise InputValidationError("并排显示音频混合至少需要2个视频文件")
            
            videos_with_audio = []
            for video_input in request.videos:
                videos_with_audio.append({
                    'video_url': video_input.video_url,
                    'volume': video_input.volume
                })
            
            layout = request.layout  # 使用请求中的布局参数
            
            result = await video_composer.side_by_side_with_audio_mix(
                videos=videos_with_audio,
                output_file=output_file,
                task_id=task_id,
                status_obj=status,
                layout=layout
            )
            
        elif request.composition_type == "slideshow":
            # 关键帧幻灯片制作
            if not request.videos or len(request.videos) < 1:
                raise InputValidationError("幻灯片制作至少需要1个图片文件")
            
            # 这里假设用户提供的是图片文件路径列表
            # 实际使用中可能需要先从视频中提取关键帧
            keyframe_images = [v.video_url for v in request.videos]  # 临时使用video_url作为图片路径
            
            # 检查是否有背景音乐
            background_audio = request.audio_file
            
            # 根据是否需要转场效果选择不同的函数
            transition_type = getattr(request, 'transition_type', 'none')
            
            if transition_type == 'fade':
                result = await video_composer.create_slideshow_with_transitions(
                    keyframe_images=keyframe_images,
                    output_file=output_file,
                    task_id=task_id,
                    status_obj=status,
                    frame_duration=3.0,
                    transition_duration=0.5,
                    background_audio=background_audio
                )
            else:
                result = await video_composer.create_slideshow_from_keyframes(
                    keyframe_images=keyframe_images,
                    output_file=output_file,
                    task_id=task_id,
                    status_obj=status,
                    duration_per_frame=3.0,
                    transition_type='none',
                    background_audio=background_audio
                )
            
        else:
            raise InputValidationError(f"暂不支持的合成类型: {request.composition_type}")
        
        # 获取输出文件信息
        output_info = await video_validator.validate_video_file(result)
        
        # 设置完成状态
        status.status = "completed"
        status.progress = 100
        status.message = "视频合成完成"
        status.result = {
            "output_file_path": result,
            "file_size": os.path.getsize(result),
            "duration": output_info.duration,
            "resolution": f"{output_info.width}x{output_info.height}",
            "format": request.output_format,
            "composition_type": request.composition_type,
            "processing_time": time.time() - status.start_time
        }
        
        logger.info(f"视频合成任务完成: {task_id} - {request.composition_type}")
        
    except Exception as e:
        # 使用统一错误处理机制
        error_info = error_handler.handle_error(
            e, 
            task_id, 
            {
                'operation': 'video_composition',
                'composition_type': request.composition_type,
                'video_count': len(request.videos)
            }
        )
        logger.error(f"视频合成任务失败: {task_id} - {error_info['message']}")
    
    finally:
        # 注销进程（如果有的话）
        task_manager.unregister_process(task_id)
        
        # 清理临时文件
        status = composition_status.get(task_id)
        if status and hasattr(status, 'temp_files') and status.temp_files:
            try:
                for temp_file in status.temp_files:
                    if os.path.exists(temp_file):
                        if os.path.isfile(temp_file):
                            os.remove(temp_file)
                        elif os.path.isdir(temp_file):
                            import shutil
                            shutil.rmtree(temp_file)
                        logger.debug(f"清理临时文件: {temp_file}")
                status.temp_files.clear()
            except Exception as cleanup_error:
                logger.warning(f"清理临时文件失败 (任务ID: {task_id}): {str(cleanup_error)}")

def cleanup_temp_files(temp_files: List[str]):
    """清理临时文件"""
    for temp_file in temp_files:
        try:
            if os.path.isfile(temp_file):
                os.remove(temp_file)
                logger.debug(f"删除临时文件: {temp_file}")
            elif os.path.isdir(temp_file):
                import shutil
                shutil.rmtree(temp_file)
                logger.debug(f"删除临时目录: {temp_file}")
        except Exception as e:
            logger.warning(f"清理临时文件失败 {temp_file}: {str(e)}")

@app.get("/composition_status/{task_id}")
async def get_composition_status(task_id: str):
    """获取视频合成任务状态"""
    if task_id not in composition_status:
        raise HTTPException(status_code=404, detail="视频合成任务不存在")
    
    status = composition_status[task_id]
    
    response = {
        "task_id": task_id,
        "status": status.status,
        "progress": status.progress,
        "message": status.message,
        "current_stage": status.current_stage
    }
    
    if status.start_time:
        elapsed_time = time.time() - status.start_time
        response["elapsed_time"] = elapsed_time
        
        if status.estimated_duration > 0 and status.progress > 0:
            remaining_time = (elapsed_time / status.progress * 100) - elapsed_time
            response["estimated_remaining_time"] = max(0, remaining_time)
    
    if status.status == "completed":
        response["result_available"] = True
        if status.result:
            response["result_summary"] = {
                "file_size": status.result.get("file_size", 0),
                "duration": status.result.get("duration", 0),
                "composition_type": status.result.get("composition_type", ""),
                "processing_time": status.result.get("processing_time", 0)
            }
    elif status.status == "failed":
        response["error"] = status.error
    
    return response

@app.get("/composition_result/{task_id}")
async def get_composition_result(task_id: str):
    """获取视频合成任务完整结果"""
    if task_id not in composition_status:
        raise HTTPException(status_code=404, detail="视频合成任务不存在或已过期")
    
    status = composition_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"视频合成任务尚未完成，当前状态: {status.status}")
    
    if not status.result:
        raise HTTPException(status_code=404, detail="视频合成结果不存在")
    
    result = status.result.copy()
    
    return {
        "task_id": task_id,
        "result": result
    }

@app.get("/composition_file/{task_id}")
async def download_composition_file(task_id: str):
    """下载合成的视频文件"""
    if task_id not in composition_status:
        raise HTTPException(status_code=404, detail="视频合成任务不存在")
    
    status = composition_status[task_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"视频合成任务尚未完成，当前状态: {status.status}")
    
    if not status.result or not status.result.get("output_file_path"):
        raise HTTPException(status_code=404, detail="合成视频文件不存在")
    
    file_path = status.result["output_file_path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="合成视频文件不存在")
    
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )