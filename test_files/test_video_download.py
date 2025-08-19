#!/usr/bin/env python3
"""
视频下载功能测试用例
"""

import pytest
import requests
import time
import json
import os
from typing import Dict, Any

# 测试配置
API_BASE_URL = "http://localhost:7878"
TEST_VIDEO_URLS = {
    "short_video": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # 短视频测试
    "medium_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # 中等长度视频
    # 注意：使用真实可访问的视频URL进行测试
}

class TestVideoDownload:
    """视频下载功能测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.session = requests.Session()
        self.session.timeout = 30
        
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        self.session.close()
    
    def test_health_check(self):
        """测试健康检查端点"""
        response = self.session.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "active_transcription_tasks" in data
        assert "active_download_tasks" in data
        assert data["status"] == "healthy"
    
    def test_download_video_invalid_url(self):
        """测试无效URL的处理"""
        invalid_urls = [
            "",
            "not_a_url",
            "http://invalid-domain.com/video",
            "ftp://example.com/video.mp4"
        ]
        
        for url in invalid_urls:
            response = self.session.post(
                f"{API_BASE_URL}/download_video",
                json={"video_url": url}
            )
            assert response.status_code == 400
    
    def test_download_video_invalid_quality(self):
        """测试无效质量参数的处理"""
        response = self.session.post(
            f"{API_BASE_URL}/download_video",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "quality": "invalid_quality"
            }
        )
        assert response.status_code == 400
        assert "不支持的质量设置" in response.json()["detail"]
    
    def test_download_video_invalid_format(self):
        """测试无效格式参数的处理"""
        response = self.session.post(
            f"{API_BASE_URL}/download_video",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "format": "invalid_format"
            }
        )
        assert response.status_code == 400
        assert "不支持的格式" in response.json()["detail"]
    
    def test_download_video_success(self):
        """测试成功的视频下载流程"""
        # 1. 启动下载任务
        response = self.session.post(
            f"{API_BASE_URL}/download_video",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "quality": "720p",
                "format": "mp4"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_id" in data
        assert data["status"] == "started"
        assert data["quality"] == "720p"
        assert data["format"] == "mp4"
        
        task_id = data["task_id"]
        
        # 2. 轮询任务状态直到完成
        max_attempts = 60  # 最多等待5分钟
        for attempt in range(max_attempts):
            response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
            assert response.status_code == 200
            
            status_data = response.json()
            assert "status" in status_data
            assert "progress" in status_data
            
            print(f"下载进度: {status_data['progress']}% - {status_data['message']}")
            
            if status_data["status"] == "completed":
                assert status_data["result_available"] is True
                assert "result_summary" in status_data
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"下载失败: {status_data.get('error', '未知错误')}")
            
            time.sleep(5)  # 等待5秒后重试
        else:
            pytest.fail("下载超时")
        
        # 3. 获取完整结果
        response = self.session.get(f"{API_BASE_URL}/download_result/{task_id}")
        assert response.status_code == 200
        
        result_data = response.json()
        assert "result" in result_data
        
        result = result_data["result"]
        assert "title" in result
        assert "file_path" in result
        assert "file_size" in result
        assert result["requested_quality"] == "720p"
        assert result["requested_format"] == "mp4"
        assert result["file_size"] > 0
        
        # 检查实际格式信息
        assert "actual_resolution" in result
        assert "actual_format" in result
        assert "format_id" in result
        
        print(f"请求质量: {result['requested_quality']}, 实际分辨率: {result['actual_resolution']}")
        print(f"请求格式: {result['requested_format']}, 实际格式: {result['actual_format']}")
        print(f"格式ID: {result['format_id']}")
        print(f"可用格式数: {result['available_formats_count']}")
        
        # 验证文件确实存在
        file_path = result["file_path"]
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) == result["file_size"]
        
        print(f"下载成功: {result['title']}, 文件大小: {result['file_size'] / 1024 / 1024:.1f}MB")
    
    def test_download_status_nonexistent_task(self):
        """测试查询不存在任务的状态"""
        fake_task_id = "00000000-0000-0000-0000-000000000000"
        response = self.session.get(f"{API_BASE_URL}/download_status/{fake_task_id}")
        assert response.status_code == 404
        assert "下载任务不存在" in response.json()["detail"]
    
    def test_download_result_nonexistent_task(self):
        """测试获取不存在任务的结果"""
        fake_task_id = "00000000-0000-0000-0000-000000000000"
        response = self.session.get(f"{API_BASE_URL}/download_result/{fake_task_id}")
        assert response.status_code == 404
        assert "下载任务不存在或已过期" in response.json()["detail"]
    
    def test_download_different_qualities(self):
        """测试不同质量的下载"""
        qualities = ["best", "worst", "480p"]
        
        for quality in qualities:
            print(f"\n测试质量: {quality}")
            
            # 启动下载任务
            response = self.session.post(
                f"{API_BASE_URL}/download_video",
                json={
                    "video_url": TEST_VIDEO_URLS["short_video"],
                    "quality": quality,
                    "format": "mp4"
                }
            )
            
            assert response.status_code == 200
            task_id = response.json()["task_id"]
            
            # 等待完成（简化版，只等待30秒）
            for _ in range(6):
                response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
                if response.status_code == 200:
                    status = response.json()["status"]
                    if status in ["completed", "failed"]:
                        break
                time.sleep(5)
            
            # 验证任务状态
            response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"质量 {quality} 测试结果: {status_data['status']}")
    
    def test_download_different_formats(self):
        """测试不同格式的下载"""
        formats = ["mp4", "webm"]
        
        for format_type in formats:
            print(f"\n测试格式: {format_type}")
            
            # 启动下载任务
            response = self.session.post(
                f"{API_BASE_URL}/download_video",
                json={
                    "video_url": TEST_VIDEO_URLS["short_video"],
                    "quality": "720p",
                    "format": format_type
                }
            )
            
            assert response.status_code == 200
            task_id = response.json()["task_id"]
            
            # 等待完成（简化版）
            for _ in range(6):
                response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
                if response.status_code == 200:
                    status = response.json()["status"]
                    if status in ["completed", "failed"]:
                        break
                time.sleep(5)
            
            # 验证任务状态
            response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"格式 {format_type} 测试结果: {status_data['status']}")

class TestVideoDownloadIntegration:
    """视频下载集成测试"""
    
    def setup_method(self):
        self.session = requests.Session()
        self.session.timeout = 30
    
    def teardown_method(self):
        self.session.close()
    
    def test_concurrent_downloads(self):
        """测试并发下载"""
        task_ids = []
        
        # 启动多个下载任务
        for i in range(3):
            response = self.session.post(
                f"{API_BASE_URL}/download_video",
                json={
                    "video_url": TEST_VIDEO_URLS["short_video"],
                    "quality": "480p",
                    "format": "mp4"
                }
            )
            
            assert response.status_code == 200
            task_ids.append(response.json()["task_id"])
        
        print(f"启动了 {len(task_ids)} 个并发下载任务")
        
        # 监控所有任务
        completed_tasks = 0
        max_attempts = 30
        
        for attempt in range(max_attempts):
            for task_id in task_ids:
                response = self.session.get(f"{API_BASE_URL}/download_status/{task_id}")
                if response.status_code == 200:
                    status = response.json()["status"]
                    if status == "completed":
                        completed_tasks += 1
            
            if completed_tasks >= len(task_ids):
                break
            
            time.sleep(5)
        
        print(f"完成了 {completed_tasks}/{len(task_ids)} 个下载任务")
        assert completed_tasks > 0  # 至少有一个任务完成

def run_manual_test():
    """手动测试函数，用于开发时调试"""
    print("=== 手动测试视频下载功能 ===")
    
    # 测试健康检查
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"健康检查: {response.status_code} - {response.json()}")
    
    # 测试下载
    test_url = TEST_VIDEO_URLS["short_video"]
    print(f"测试下载: {test_url}")
    
    response = requests.post(
        f"{API_BASE_URL}/download_video",
        json={
            "video_url": test_url,
            "quality": "720p",
            "format": "mp4"
        }
    )
    
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"任务已启动: {task_id}")
        
        # 监控进度
        while True:
            response = requests.get(f"{API_BASE_URL}/download_status/{task_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"进度: {data['progress']}% - {data['message']}")
                
                if data["status"] == "completed":
                    print("下载完成！")
                    
                    # 获取结果
                    response = requests.get(f"{API_BASE_URL}/download_result/{task_id}")
                    if response.status_code == 200:
                        result = response.json()["result"]
                        print(f"文件: {result['file_path']}")
                        print(f"大小: {result['file_size'] / 1024 / 1024:.1f}MB")
                    break
                elif data["status"] == "failed":
                    print(f"下载失败: {data.get('error', '未知错误')}")
                    break
            
            time.sleep(5)
    else:
        print(f"启动下载失败: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # 运行手动测试
    run_manual_test()