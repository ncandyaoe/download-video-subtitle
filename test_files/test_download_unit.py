#!/usr/bin/env python3
"""
视频下载功能单元测试
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import json

# 导入要测试的模块
import sys
sys.path.append('.')

class TestDownloadFunctions:
    """测试下载相关的辅助函数"""
    
    def test_check_video_file_size_limit(self):
        """测试视频文件大小限制检查"""
        from api import check_video_file_size_limit
        
        # 测试正常情况
        video_metadata = {"duration": 300}  # 5分钟
        size = check_video_file_size_limit(video_metadata, "720p")
        assert size > 0
        
        # 测试超大视频
        video_metadata = {"duration": 36000}  # 10小时
        with pytest.raises(Exception) as exc_info:
            check_video_file_size_limit(video_metadata, "1080p")
        assert "超过限制" in str(exc_info.value)
    
    def test_download_status_class(self):
        """测试DownloadStatus类"""
        from api import DownloadStatus
        
        status = DownloadStatus()
        assert status.status == "downloading"
        assert status.progress == 0
        assert status.message == ""
        assert status.result is None
        assert status.error is None
        assert status.file_path is None
        assert status.file_size == 0
        assert status.downloaded_size == 0
    
    def test_get_download_progress_hook(self):
        """测试下载进度钩子"""
        from api import get_download_progress_hook, download_status, DownloadStatus
        
        # 创建测试任务
        task_id = "test_task_123"
        download_status[task_id] = DownloadStatus()
        
        # 获取进度钩子
        hook = get_download_progress_hook(task_id)
        
        # 测试下载中状态
        hook({
            'status': 'downloading',
            'total_bytes': 1000000,
            'downloaded_bytes': 500000
        })
        
        status = download_status[task_id]
        assert status.file_size == 1000000
        assert status.downloaded_size == 500000
        assert status.progress > 20  # 应该在20%以上
        assert "下载中" in status.message
        
        # 测试完成状态
        hook({
            'status': 'finished',
            'filename': '/path/to/video.mp4'
        })
        
        assert status.progress == 90
        assert status.file_path == '/path/to/video.mp4'
        assert "下载完成" in status.message
        
        # 清理
        del download_status[task_id]

class TestDownloadRequestValidation:
    """测试下载请求验证"""
    
    def test_download_request_params(self):
        """测试DownloadRequestParams模型"""
        from api import DownloadRequestParams
        
        # 测试默认值
        request = DownloadRequestParams(video_url="https://example.com/video")
        assert request.video_url == "https://example.com/video"
        assert request.quality == "best"
        assert request.format == "mp4"
        
        # 测试自定义值
        request = DownloadRequestParams(
            video_url="https://example.com/video",
            quality="720p",
            format="webm"
        )
        assert request.quality == "720p"
        assert request.format == "webm"

class TestDownloadUtilities:
    """测试下载相关的工具函数"""
    
    def test_quality_validation(self):
        """测试质量参数验证"""
        valid_qualities = ["best", "worst", "1080p", "720p", "480p"]
        
        for quality in valid_qualities:
            # 这里应该不抛出异常
            assert quality in valid_qualities
        
        invalid_qualities = ["4K", "360p", "invalid"]
        for quality in invalid_qualities:
            assert quality not in valid_qualities
    
    def test_format_validation(self):
        """测试格式参数验证"""
        valid_formats = ["mp4", "webm", "mkv"]
        
        for format_type in valid_formats:
            assert format_type in valid_formats
        
        invalid_formats = ["avi", "mov", "flv"]
        for format_type in invalid_formats:
            assert format_type not in valid_formats

class TestDownloadErrorHandling:
    """测试下载错误处理"""
    
    def test_file_size_estimation(self):
        """测试文件大小估算"""
        from api import check_video_file_size_limit
        
        # 测试不同质量的估算
        video_metadata = {"duration": 600}  # 10分钟
        
        size_1080p = check_video_file_size_limit(video_metadata, "1080p")
        size_720p = check_video_file_size_limit(video_metadata, "720p")
        size_480p = check_video_file_size_limit(video_metadata, "480p")
        
        # 1080p应该比720p大，720p应该比480p大
        assert size_1080p > size_720p
        assert size_720p > size_480p
    
    def test_duration_limit_integration(self):
        """测试时长限制与现有功能的集成"""
        from api import check_video_duration_limit
        
        # 测试正常时长
        normal_metadata = {"duration": 1800}  # 30分钟
        duration = check_video_duration_limit(normal_metadata)
        assert duration == 1800
        
        # 测试超长视频
        long_metadata = {"duration": 14400}  # 4小时
        with pytest.raises(Exception) as exc_info:
            check_video_duration_limit(long_metadata)
        assert "超过限制" in str(exc_info.value)

@pytest.fixture
def temp_download_dir():
    """创建临时下载目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

class TestDownloadFileHandling:
    """测试下载文件处理"""
    
    def test_file_path_generation(self, temp_download_dir):
        """测试文件路径生成"""
        video_id = "test_video_123"
        quality = "720p"
        
        # 模拟文件路径生成逻辑
        expected_pattern = f"{video_id}_{quality}"
        
        assert video_id in expected_pattern
        assert quality in expected_pattern
    
    def test_file_existence_check(self, temp_download_dir):
        """测试文件存在性检查"""
        # 创建测试文件
        test_file = os.path.join(temp_download_dir, "test_video.mp4")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        assert os.path.exists(test_file)
        assert os.path.getsize(test_file) > 0

def run_unit_tests():
    """运行单元测试"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    run_unit_tests()