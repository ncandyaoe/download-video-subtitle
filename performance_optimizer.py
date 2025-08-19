#!/usr/bin/env python3
"""
性能优化模块
包括缓存管理、硬件加速检测和内存优化处理
"""

import os
import json
import hashlib
import time
import shutil
import subprocess
import psutil
import gc
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timedelta
import threading
import tempfile
from loguru import logger

class CacheManager:
    """视频预处理缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size_gb: float = 5.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存子目录
        self.metadata_cache_dir = self.cache_dir / "metadata"
        self.video_cache_dir = self.cache_dir / "videos"
        self.thumbnail_cache_dir = self.cache_dir / "thumbnails"
        
        for cache_subdir in [self.metadata_cache_dir, self.video_cache_dir, self.thumbnail_cache_dir]:
            cache_subdir.mkdir(exist_ok=True)
        
        self.max_cache_size_bytes = int(max_cache_size_gb * 1024 * 1024 * 1024)
        self.cache_index_file = self.cache_dir / "cache_index.json"
        
        # LRU缓存索引
        self.cache_index = self._load_cache_index()
        self.lock = threading.RLock()
        
        logger.info(f"缓存管理器初始化完成，缓存目录: {self.cache_dir}, 最大大小: {max_cache_size_gb}GB")
    
    def _load_cache_index(self) -> OrderedDict:
        """加载缓存索引"""
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 按访问时间排序（最近访问的在后面）
                    sorted_items = sorted(data.items(), key=lambda x: x[1].get('last_access', 0))
                    return OrderedDict(sorted_items)
            except Exception as e:
                logger.warning(f"加载缓存索引失败: {e}")
        
        return OrderedDict()
    
    def _save_cache_index(self):
        """保存缓存索引"""
        try:
            with open(self.cache_index_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.cache_index), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存缓存索引失败: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        
        # 对于大文件，只读取开头、中间和结尾的部分来计算哈希
        file_size = os.path.getsize(file_path)
        chunk_size = 8192
        
        with open(file_path, "rb") as f:
            # 读取开头
            chunk = f.read(chunk_size)
            hash_md5.update(chunk)
            
            if file_size > chunk_size * 3:
                # 读取中间
                f.seek(file_size // 2)
                chunk = f.read(chunk_size)
                hash_md5.update(chunk)
                
                # 读取结尾
                f.seek(-chunk_size, 2)
                chunk = f.read(chunk_size)
                hash_md5.update(chunk)
        
        # 加入文件大小和修改时间
        stat = os.stat(file_path)
        hash_md5.update(str(stat.st_size).encode())
        hash_md5.update(str(int(stat.st_mtime)).encode())
        
        return hash_md5.hexdigest()
    
    def _cleanup_old_cache(self):
        """清理过期和超出大小限制的缓存"""
        with self.lock:
            current_size = self._get_cache_size()
            
            # 如果缓存大小超出限制，删除最旧的缓存
            while current_size > self.max_cache_size_bytes and self.cache_index:
                # 获取最旧的缓存项
                oldest_key = next(iter(self.cache_index))
                oldest_item = self.cache_index[oldest_key]
                
                # 删除缓存文件
                self._remove_cache_item(oldest_key, oldest_item)
                
                # 从索引中移除
                del self.cache_index[oldest_key]
                
                current_size = self._get_cache_size()
                logger.info(f"清理缓存项: {oldest_key}, 当前缓存大小: {current_size / 1024 / 1024:.1f}MB")
            
            # 清理过期缓存（7天未访问）
            cutoff_time = time.time() - 7 * 24 * 3600
            expired_keys = []
            
            for key, item in self.cache_index.items():
                if item.get('last_access', 0) < cutoff_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                item = self.cache_index[key]
                self._remove_cache_item(key, item)
                del self.cache_index[key]
                logger.info(f"清理过期缓存项: {key}")
            
            self._save_cache_index()
    
    def _remove_cache_item(self, key: str, item: Dict[str, Any]):
        """删除缓存项的所有文件"""
        try:
            if 'metadata_file' in item:
                metadata_file = Path(item['metadata_file'])
                if metadata_file.exists():
                    metadata_file.unlink()
            
            if 'video_file' in item:
                video_file = Path(item['video_file'])
                if video_file.exists():
                    video_file.unlink()
            
            if 'thumbnail_file' in item:
                thumbnail_file = Path(item['thumbnail_file'])
                if thumbnail_file.exists():
                    thumbnail_file.unlink()
        except Exception as e:
            logger.error(f"删除缓存项文件失败: {e}")
    
    def _get_cache_size(self) -> int:
        """获取缓存总大小"""
        total_size = 0
        for cache_subdir in [self.metadata_cache_dir, self.video_cache_dir, self.thumbnail_cache_dir]:
            for file_path in cache_subdir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size
    
    def get_video_metadata_cache(self, video_path: str) -> Optional[Dict[str, Any]]:
        """获取视频元数据缓存"""
        try:
            file_hash = self._get_file_hash(video_path)
            
            with self.lock:
                if file_hash in self.cache_index:
                    cache_item = self.cache_index[file_hash]
                    metadata_file = Path(cache_item.get('metadata_file', ''))
                    
                    if metadata_file.exists():
                        # 更新访问时间
                        cache_item['last_access'] = time.time()
                        # 移到末尾（最近访问）
                        self.cache_index.move_to_end(file_hash)
                        
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        logger.debug(f"命中元数据缓存: {video_path}")
                        return metadata
            
            return None
            
        except Exception as e:
            logger.error(f"获取元数据缓存失败: {e}")
            return None
    
    def set_video_metadata_cache(self, video_path: str, metadata: Dict[str, Any]):
        """设置视频元数据缓存"""
        try:
            file_hash = self._get_file_hash(video_path)
            metadata_file = self.metadata_cache_dir / f"{file_hash}.json"
            
            # 保存元数据
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            with self.lock:
                # 更新缓存索引
                self.cache_index[file_hash] = {
                    'type': 'metadata',
                    'original_path': video_path,
                    'metadata_file': str(metadata_file),
                    'created_time': time.time(),
                    'last_access': time.time(),
                    'size': metadata_file.stat().st_size
                }
                
                # 移到末尾（最近访问）
                self.cache_index.move_to_end(file_hash)
                
                self._save_cache_index()
                self._cleanup_old_cache()
            
            logger.debug(f"保存元数据缓存: {video_path}")
            
        except Exception as e:
            logger.error(f"设置元数据缓存失败: {e}")
    
    def get_processed_video_cache(self, video_path: str, processing_params: Dict[str, Any]) -> Optional[str]:
        """获取预处理视频缓存"""
        try:
            # 生成包含处理参数的缓存键
            file_hash = self._get_file_hash(video_path)
            params_hash = hashlib.md5(json.dumps(processing_params, sort_keys=True).encode()).hexdigest()
            cache_key = f"{file_hash}_{params_hash}"
            
            with self.lock:
                if cache_key in self.cache_index:
                    cache_item = self.cache_index[cache_key]
                    video_file = Path(cache_item.get('video_file', ''))
                    
                    if video_file.exists():
                        # 更新访问时间
                        cache_item['last_access'] = time.time()
                        self.cache_index.move_to_end(cache_key)
                        
                        logger.debug(f"命中预处理视频缓存: {video_path}")
                        return str(video_file)
            
            return None
            
        except Exception as e:
            logger.error(f"获取预处理视频缓存失败: {e}")
            return None
    
    def set_processed_video_cache(self, video_path: str, processing_params: Dict[str, Any], processed_video_path: str):
        """设置预处理视频缓存"""
        try:
            file_hash = self._get_file_hash(video_path)
            params_hash = hashlib.md5(json.dumps(processing_params, sort_keys=True).encode()).hexdigest()
            cache_key = f"{file_hash}_{params_hash}"
            
            # 复制处理后的视频到缓存目录
            cached_video_file = self.video_cache_dir / f"{cache_key}.mp4"
            shutil.copy2(processed_video_path, cached_video_file)
            
            with self.lock:
                # 更新缓存索引
                self.cache_index[cache_key] = {
                    'type': 'processed_video',
                    'original_path': video_path,
                    'processing_params': processing_params,
                    'video_file': str(cached_video_file),
                    'created_time': time.time(),
                    'last_access': time.time(),
                    'size': cached_video_file.stat().st_size
                }
                
                self.cache_index.move_to_end(cache_key)
                self._save_cache_index()
                self._cleanup_old_cache()
            
            logger.debug(f"保存预处理视频缓存: {video_path}")
            
        except Exception as e:
            logger.error(f"设置预处理视频缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_size = self._get_cache_size()
            
            stats = {
                'total_items': len(self.cache_index),
                'total_size_mb': total_size / 1024 / 1024,
                'max_size_mb': self.max_cache_size_bytes / 1024 / 1024,
                'usage_percent': (total_size / self.max_cache_size_bytes) * 100,
                'cache_dir': str(self.cache_dir),
                'items_by_type': {}
            }
            
            # 按类型统计
            for item in self.cache_index.values():
                item_type = item.get('type', 'unknown')
                if item_type not in stats['items_by_type']:
                    stats['items_by_type'][item_type] = {'count': 0, 'size_mb': 0}
                
                stats['items_by_type'][item_type]['count'] += 1
                stats['items_by_type'][item_type]['size_mb'] += item.get('size', 0) / 1024 / 1024
            
            return stats
    
    def clear_cache(self):
        """清空所有缓存"""
        with self.lock:
            try:
                # 删除所有缓存文件
                for cache_subdir in [self.metadata_cache_dir, self.video_cache_dir, self.thumbnail_cache_dir]:
                    for file_path in cache_subdir.rglob('*'):
                        if file_path.is_file():
                            file_path.unlink()
                
                # 清空索引
                self.cache_index.clear()
                self._save_cache_index()
                
                logger.info("已清空所有缓存")
                
            except Exception as e:
                logger.error(f"清空缓存失败: {e}")

class HardwareAccelerationDetector:
    """硬件加速检测器"""
    
    def __init__(self):
        self.available_encoders = {}
        self.preferred_encoder = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保硬件检测已完成"""
        if not self._initialized:
            self._detect_hardware_encoders()
            self._initialized = True
    
    def _detect_hardware_encoders(self):
        """检测可用的硬件编码器"""
        logger.info("开始检测硬件编码器...")
        
        # 定义硬件编码器列表（按优先级排序）
        encoders_to_test = [
            # NVIDIA GPU
            {'name': 'h264_nvenc', 'type': 'nvidia', 'codec': 'h264'},
            {'name': 'hevc_nvenc', 'type': 'nvidia', 'codec': 'hevc'},
            
            # Intel QuickSync
            {'name': 'h264_qsv', 'type': 'intel', 'codec': 'h264'},
            {'name': 'hevc_qsv', 'type': 'intel', 'codec': 'hevc'},
            
            # AMD AMF
            {'name': 'h264_amf', 'type': 'amd', 'codec': 'h264'},
            {'name': 'hevc_amf', 'type': 'amd', 'codec': 'hevc'},
            
            # macOS VideoToolbox
            {'name': 'h264_videotoolbox', 'type': 'videotoolbox', 'codec': 'h264'},
            {'name': 'hevc_videotoolbox', 'type': 'videotoolbox', 'codec': 'hevc'},
        ]
        
        for encoder in encoders_to_test:
            if self._test_encoder(encoder['name']):
                self.available_encoders[encoder['name']] = encoder
                if not self.preferred_encoder:
                    self.preferred_encoder = encoder['name']
                logger.info(f"检测到硬件编码器: {encoder['name']} ({encoder['type']})")
        
        if not self.available_encoders:
            logger.warning("未检测到可用的硬件编码器，将使用软件编码")
        else:
            logger.info(f"首选硬件编码器: {self.preferred_encoder}")
    
    def _test_encoder(self, encoder_name: str) -> bool:
        """测试编码器是否可用"""
        try:
            # 创建一个简单的测试视频
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            try:
                # 使用FFmpeg测试编码器
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'lavfi',
                    '-i', 'testsrc=duration=1:size=320x240:rate=1',
                    '-c:v', encoder_name,
                    '-t', '1',
                    '-f', 'mp4',
                    temp_output_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                success = result.returncode == 0 and os.path.exists(temp_output_path)
                
                if success:
                    # 验证输出文件是否有效
                    file_size = os.path.getsize(temp_output_path)
                    success = file_size > 0
                
                return success
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)
                    
        except Exception as e:
            logger.debug(f"测试编码器 {encoder_name} 失败: {e}")
            return False
    
    def get_encoder_params(self, codec: str = 'h264', quality: str = 'medium') -> List[str]:
        """获取编码器参数"""
        self._ensure_initialized()
        
        params = []
        
        # 选择编码器
        encoder = None
        for enc_name, enc_info in self.available_encoders.items():
            if enc_info['codec'] == codec:
                encoder = enc_name
                break
        
        if not encoder:
            # 回退到软件编码
            encoder = 'libx264' if codec == 'h264' else 'libx265'
            logger.debug(f"使用软件编码器: {encoder}")
        else:
            logger.debug(f"使用硬件编码器: {encoder}")
        
        params.extend(['-c:v', encoder])
        
        # 根据编码器类型设置参数
        if 'nvenc' in encoder:
            # NVIDIA编码器参数
            quality_map = {
                'fast': 'fast',
                'medium': 'medium',
                'slow': 'slow'
            }
            params.extend([
                '-preset', quality_map.get(quality, 'medium'),
                '-rc', 'vbr',
                '-cq', '23',
                '-b:v', '0'
            ])
            
        elif 'qsv' in encoder:
            # Intel QuickSync参数
            quality_map = {
                'fast': 'fast',
                'medium': 'medium',
                'slow': 'slow'
            }
            params.extend([
                '-preset', quality_map.get(quality, 'medium'),
                '-global_quality', '23'
            ])
            
        elif 'amf' in encoder:
            # AMD AMF参数
            quality_map = {
                'fast': 'speed',
                'medium': 'balanced',
                'slow': 'quality'
            }
            params.extend([
                '-usage', quality_map.get(quality, 'balanced'),
                '-rc', 'cqp',
                '-qp_i', '23',
                '-qp_p', '23'
            ])
            
        elif 'videotoolbox' in encoder:
            # VideoToolbox参数
            params.extend([
                '-q:v', '23'
            ])
            
        else:
            # 软件编码器参数
            quality_map = {
                'fast': 'fast',
                'medium': 'medium',
                'slow': 'slow'
            }
            params.extend([
                '-preset', quality_map.get(quality, 'medium'),
                '-crf', '23'
            ])
        
        return params
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """获取硬件信息"""
        self._ensure_initialized()
        
        return {
            'available_encoders': list(self.available_encoders.keys()),
            'preferred_encoder': self.preferred_encoder,
            'encoder_details': self.available_encoders,
            'has_hardware_acceleration': len(self.available_encoders) > 0
        }

class MemoryOptimizedProcessor:
    """内存优化处理器"""
    
    def __init__(self, max_memory_usage_percent: float = 80.0, chunk_size_mb: int = 100):
        self.max_memory_usage_percent = max_memory_usage_percent
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.temp_dir = Path(tempfile.gettempdir()) / "video_processing"
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"内存优化处理器初始化，最大内存使用: {max_memory_usage_percent}%, 块大小: {chunk_size_mb}MB")
    
    def check_memory_usage(self) -> Dict[str, float]:
        """检查当前内存使用情况"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / 1024 / 1024 / 1024,
            'available_gb': memory.available / 1024 / 1024 / 1024,
            'used_percent': memory.percent,
            'free_percent': 100 - memory.percent
        }
    
    def is_memory_available(self, required_mb: float = 500) -> bool:
        """检查是否有足够的内存"""
        memory = psutil.virtual_memory()
        available_mb = memory.available / 1024 / 1024
        current_usage_percent = memory.percent
        
        # 检查当前使用率和所需内存
        return (current_usage_percent < self.max_memory_usage_percent and 
                available_mb > required_mb)
    
    def trigger_memory_cleanup(self):
        """触发内存清理"""
        logger.info("触发内存清理...")
        
        # 强制垃圾回收
        gc.collect()
        
        # 清理临时文件
        self._cleanup_temp_files()
        
        memory_info = self.check_memory_usage()
        logger.info(f"内存清理完成，当前使用率: {memory_info['used_percent']:.1f}%")
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_files_cleaned = 0
            for temp_file in self.temp_dir.rglob('*'):
                if temp_file.is_file():
                    # 删除超过1小时的临时文件
                    if time.time() - temp_file.stat().st_mtime > 3600:
                        temp_file.unlink()
                        temp_files_cleaned += 1
            
            if temp_files_cleaned > 0:
                logger.info(f"清理了 {temp_files_cleaned} 个临时文件")
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def process_large_video_in_chunks(self, input_path: str, output_path: str, 
                                    processing_func, chunk_duration: int = 60) -> bool:
        """分块处理大视频文件"""
        try:
            logger.info(f"开始分块处理大视频: {input_path}")
            
            # 获取视频信息
            video_info = self._get_video_info(input_path)
            if not video_info:
                return False
            
            total_duration = float(video_info.get('duration', 0))
            if total_duration <= chunk_duration:
                # 视频不够大，直接处理
                return processing_func(input_path, output_path)
            
            # 计算分块数量
            num_chunks = int(total_duration / chunk_duration) + 1
            chunk_files = []
            
            logger.info(f"视频时长: {total_duration:.1f}秒, 分为 {num_chunks} 块处理")
            
            try:
                # 分块处理
                for i in range(num_chunks):
                    start_time = i * chunk_duration
                    end_time = min((i + 1) * chunk_duration, total_duration)
                    
                    # 检查内存使用
                    if not self.is_memory_available():
                        self.trigger_memory_cleanup()
                        if not self.is_memory_available():
                            logger.error("内存不足，无法继续处理")
                            return False
                    
                    # 提取块
                    chunk_input = self.temp_dir / f"chunk_{i}_input.mp4"
                    chunk_output = self.temp_dir / f"chunk_{i}_output.mp4"
                    
                    # 提取视频块
                    extract_cmd = [
                        'ffmpeg', '-y',
                        '-i', input_path,
                        '-ss', str(start_time),
                        '-t', str(end_time - start_time),
                        '-c', 'copy',
                        str(chunk_input)
                    ]
                    
                    result = subprocess.run(extract_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"提取视频块 {i} 失败: {result.stderr}")
                        continue
                    
                    # 处理块
                    if processing_func(str(chunk_input), str(chunk_output)):
                        chunk_files.append(str(chunk_output))
                        logger.info(f"完成块 {i+1}/{num_chunks} 处理")
                    else:
                        logger.error(f"处理块 {i} 失败")
                    
                    # 清理输入块文件
                    if chunk_input.exists():
                        chunk_input.unlink()
                
                # 合并所有块
                if chunk_files:
                    return self._merge_video_chunks(chunk_files, output_path)
                else:
                    logger.error("没有成功处理的视频块")
                    return False
                    
            finally:
                # 清理临时文件
                for chunk_file in chunk_files:
                    chunk_path = Path(chunk_file)
                    if chunk_path.exists():
                        chunk_path.unlink()
                        
        except Exception as e:
            logger.error(f"分块处理视频失败: {e}")
            return False
    
    def _get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout).get('format', {})
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
        
        return None
    
    def _merge_video_chunks(self, chunk_files: List[str], output_path: str) -> bool:
        """合并视频块"""
        try:
            # 创建concat文件列表
            concat_file = self.temp_dir / "concat_list.txt"
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for chunk_file in chunk_files:
                    f.write(f"file '{chunk_file}'\n")
            
            # 合并视频
            merge_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(merge_cmd, capture_output=True, text=True)
            
            # 清理concat文件
            if concat_file.exists():
                concat_file.unlink()
            
            if result.returncode == 0:
                logger.info(f"成功合并 {len(chunk_files)} 个视频块")
                return True
            else:
                logger.error(f"合并视频块失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"合并视频块失败: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        memory_info = self.check_memory_usage()
        
        return {
            'memory_info': memory_info,
            'max_usage_percent': self.max_memory_usage_percent,
            'chunk_size_mb': self.chunk_size_bytes / 1024 / 1024,
            'temp_dir': str(self.temp_dir),
            'is_memory_available': self.is_memory_available()
        }

class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size_gb: float = 5.0,
                 max_memory_usage_percent: float = 80.0):
        self.cache_manager = CacheManager(cache_dir, max_cache_size_gb)
        self.hardware_detector = HardwareAccelerationDetector()
        self.memory_processor = MemoryOptimizedProcessor(max_memory_usage_percent)
        
        logger.info("性能优化器初始化完成")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            'cache_stats': self.cache_manager.get_cache_stats(),
            'hardware_info': self.hardware_detector.get_hardware_info(),
            'memory_stats': self.memory_processor.get_memory_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """获取硬件信息"""
        return self.hardware_detector.get_hardware_info()
    
    def optimize_ffmpeg_command(self, base_cmd: List[str], quality: str = 'medium') -> List[str]:
        """优化FFmpeg命令"""
        optimized_cmd = base_cmd.copy()
        
        # 查找视频编码器参数的位置
        if '-c:v' in optimized_cmd:
            codec_index = optimized_cmd.index('-c:v')
            # 替换为硬件加速编码器参数
            hardware_params = self.hardware_detector.get_encoder_params('h264', quality)
            
            # 移除原有的编码器参数
            if codec_index + 1 < len(optimized_cmd):
                optimized_cmd.pop(codec_index + 1)  # 移除编码器名称
                optimized_cmd.pop(codec_index)      # 移除-c:v
            
            # 插入硬件加速参数
            for i, param in enumerate(hardware_params):
                optimized_cmd.insert(codec_index + i, param)
        
        return optimized_cmd
    
    def cleanup_all(self):
        """清理所有资源"""
        logger.info("开始清理所有优化器资源...")
        
        # 清理缓存
        self.cache_manager.clear_cache()
        
        # 清理内存
        self.memory_processor.trigger_memory_cleanup()
        
        logger.info("优化器资源清理完成")

# 全局性能优化器实例
performance_optimizer = PerformanceOptimizer()

def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    return performance_optimizer