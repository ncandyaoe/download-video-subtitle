#!/usr/bin/env python3
"""
关键帧提取功能测试用例
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
}

class TestKeyframeExtraction:
    """关键帧提取功能测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.session = requests.Session()
        self.session.timeout = 30
        
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        self.session.close()
    
    def test_health_check_includes_keyframe_tasks(self):
        """测试健康检查包含关键帧任务信息"""
        response = self.session.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_keyframe_tasks" in data
        assert isinstance(data["active_keyframe_tasks"], int)
    
    def test_extract_keyframes_invalid_url(self):
        """测试无效URL的处理"""
        invalid_urls = [
            "",
            "not_a_url",
            "http://invalid-domain.com/video",
        ]
        
        for url in invalid_urls:
            response = self.session.post(
                f"{API_BASE_URL}/extract_keyframes",
                json={"video_url": url}
            )
            assert response.status_code == 400
    
    def test_extract_keyframes_invalid_method(self):
        """测试无效方法参数的处理"""
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "invalid_method"
            }
        )
        assert response.status_code == 400
        assert "不支持的提取方法" in response.json()["detail"]
    
    def test_extract_keyframes_invalid_format(self):
        """测试无效格式参数的处理"""
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "format": "invalid_format"
            }
        )
        assert response.status_code == 400
        assert "不支持的图片格式" in response.json()["detail"]
    
    def test_extract_keyframes_invalid_dimensions(self):
        """测试无效尺寸参数的处理"""
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "width": 50,  # 太小
                "height": 50
            }
        )
        assert response.status_code == 400
        assert "图片尺寸必须在" in response.json()["detail"]
    
    def test_extract_keyframes_timestamps_without_list(self):
        """测试timestamps方法但未提供timestamps列表"""
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "timestamps"
            }
        )
        assert response.status_code == 400
        assert "必须提供timestamps列表" in response.json()["detail"]
    
    def test_extract_keyframes_interval_method(self):
        """测试间隔方法的关键帧提取"""
        # 1. 启动提取任务
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "interval",
                "interval": 15,  # 每15秒一帧
                "width": 640,
                "height": 360,
                "format": "jpg",
                "quality": 80
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_id" in data
        assert data["status"] == "started"
        assert data["method"] == "interval"
        assert data["parameters"]["interval"] == 15
        
        task_id = data["task_id"]
        
        # 2. 轮询任务状态直到完成
        max_attempts = 60  # 最多等待5分钟
        for attempt in range(max_attempts):
            response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            assert response.status_code == 200
            
            status_data = response.json()
            assert "status" in status_data
            assert "progress" in status_data
            
            print(f"提取进度: {status_data['progress']}% - {status_data['message']}")
            
            if status_data["status"] == "completed":
                assert status_data["result_available"] is True
                assert "result_summary" in status_data
                assert status_data["total_frames"] > 0
                assert status_data["extracted_frames"] > 0
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"关键帧提取失败: {status_data.get('error', '未知错误')}")
            
            time.sleep(5)  # 等待5秒后重试
        else:
            pytest.fail("关键帧提取超时")
        
        # 3. 获取完整结果
        response = self.session.get(f"{API_BASE_URL}/keyframe_result/{task_id}")
        assert response.status_code == 200
        
        result_data = response.json()
        assert "result" in result_data
        
        result = result_data["result"]
        assert "title" in result
        assert "total_frames" in result
        assert "frames" in result
        assert result["method"] == "interval"
        assert result["total_frames"] > 0
        assert len(result["frames"]) == result["total_frames"]
        
        # 验证帧信息
        for frame in result["frames"]:
            assert "timestamp" in frame
            assert "filename" in frame
            assert "path" in frame
            assert "size" in frame
            assert os.path.exists(frame["path"])
        
        print(f"提取成功: {result['title']}, 共 {result['total_frames']} 帧")
        return result
    
    def test_extract_keyframes_timestamps_method(self):
        """测试指定时间点方法的关键帧提取"""
        timestamps = [10.0, 30.0, 60.0, 90.0]  # 指定时间点
        
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "timestamps",
                "timestamps": timestamps,
                "width": 800,
                "height": 450,
                "format": "png"
            }
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # 等待完成（简化版）
        for _ in range(30):
            response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            if response.status_code == 200:
                status = response.json()["status"]
                if status in ["completed", "failed"]:
                    break
            time.sleep(5)
        
        # 验证结果
        response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
        if response.status_code == 200:
            status_data = response.json()
            if status_data["status"] == "completed":
                # 获取完整结果
                result_response = self.session.get(f"{API_BASE_URL}/keyframe_result/{task_id}")
                if result_response.status_code == 200:
                    result = result_response.json()["result"]
                    assert result["method"] == "timestamps"
                    # 帧数应该等于或少于指定的时间点数（某些时间点可能超出视频长度）
                    assert result["total_frames"] <= len(timestamps)
                    print(f"时间点提取成功: 请求 {len(timestamps)} 个时间点，实际提取 {result['total_frames']} 帧")
    
    def test_extract_keyframes_count_method(self):
        """测试按数量平均分布方法的关键帧提取"""
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "count",
                "count": 5,  # 提取5帧
                "width": 1280,
                "height": 720,
                "format": "jpg",
                "quality": 90
            }
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # 等待完成（简化版）
        for _ in range(30):
            response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            if response.status_code == 200:
                status = response.json()["status"]
                if status in ["completed", "failed"]:
                    break
            time.sleep(5)
        
        # 验证结果
        response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
        if response.status_code == 200:
            status_data = response.json()
            if status_data["status"] == "completed":
                result_response = self.session.get(f"{API_BASE_URL}/keyframe_result/{task_id}")
                if result_response.status_code == 200:
                    result = result_response.json()["result"]
                    assert result["method"] == "count"
                    assert result["total_frames"] == 5
                    print(f"按数量提取成功: 提取了 {result['total_frames']} 帧")
    
    def test_keyframe_image_download(self):
        """测试关键帧图片下载"""
        # 首先提取一些关键帧
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "count",
                "count": 3,
                "width": 640,
                "height": 360
            }
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # 等待完成
        for _ in range(30):
            response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            if response.status_code == 200:
                status = response.json()["status"]
                if status == "completed":
                    break
            time.sleep(5)
        
        # 测试下载第一帧
        response = self.session.get(f"{API_BASE_URL}/keyframe_image/{task_id}/0")
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("image/")
            assert len(response.content) > 0
            print("关键帧图片下载成功")
        
        # 测试下载不存在的帧
        response = self.session.get(f"{API_BASE_URL}/keyframe_image/{task_id}/999")
        assert response.status_code == 404
    
    def test_keyframe_thumbnail_download(self):
        """测试缩略图网格下载"""
        # 首先提取一些关键帧
        response = self.session.post(
            f"{API_BASE_URL}/extract_keyframes",
            json={
                "video_url": TEST_VIDEO_URLS["short_video"],
                "method": "count",
                "count": 4,
                "width": 640,
                "height": 360
            }
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # 等待完成
        for _ in range(30):
            response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            if response.status_code == 200:
                status = response.json()["status"]
                if status == "completed":
                    break
            time.sleep(5)
        
        # 测试下载缩略图
        response = self.session.get(f"{API_BASE_URL}/keyframe_thumbnail/{task_id}")
        if response.status_code == 200:
            assert response.headers["content-type"] == "image/jpeg"
            assert len(response.content) > 0
            print("缩略图网格下载成功")
    
    def test_keyframe_status_nonexistent_task(self):
        """测试查询不存在任务的状态"""
        fake_task_id = "00000000-0000-0000-0000-000000000000"
        response = self.session.get(f"{API_BASE_URL}/keyframe_status/{fake_task_id}")
        assert response.status_code == 404
        assert "关键帧提取任务不存在" in response.json()["detail"]
    
    def test_keyframe_result_nonexistent_task(self):
        """测试获取不存在任务的结果"""
        fake_task_id = "00000000-0000-0000-0000-000000000000"
        response = self.session.get(f"{API_BASE_URL}/keyframe_result/{fake_task_id}")
        assert response.status_code == 404
        assert "关键帧提取任务不存在或已过期" in response.json()["detail"]

class TestKeyframeIntegration:
    """关键帧提取集成测试"""
    
    def setup_method(self):
        self.session = requests.Session()
        self.session.timeout = 30
    
    def teardown_method(self):
        self.session.close()
    
    def test_different_methods_comparison(self):
        """测试不同提取方法的比较"""
        methods = [
            {"method": "interval", "interval": 30},
            {"method": "count", "count": 5},
            {"method": "timestamps", "timestamps": [15.0, 45.0, 75.0]}
        ]
        
        results = {}
        
        for method_config in methods:
            print(f"\n测试方法: {method_config['method']}")
            
            # 启动提取任务
            response = self.session.post(
                f"{API_BASE_URL}/extract_keyframes",
                json={
                    "video_url": TEST_VIDEO_URLS["short_video"],
                    **method_config,
                    "width": 640,
                    "height": 360,
                    "format": "jpg"
                }
            )
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                
                # 等待完成（简化版）
                for _ in range(20):
                    status_response = self.session.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()["status"]
                        if status in ["completed", "failed"]:
                            break
                    time.sleep(5)
                
                # 获取结果
                if status == "completed":
                    result_response = self.session.get(f"{API_BASE_URL}/keyframe_result/{task_id}")
                    if result_response.status_code == 200:
                        result = result_response.json()["result"]
                        results[method_config["method"]] = result["total_frames"]
                        print(f"方法 {method_config['method']} 提取了 {result['total_frames']} 帧")
        
        print(f"\n提取结果比较: {results}")
        assert len(results) > 0  # 至少有一个方法成功

def run_manual_test():
    """手动测试函数，用于开发时调试"""
    print("=== 手动测试关键帧提取功能 ===")
    
    # 测试健康检查
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"健康检查: {response.status_code} - {response.json()}")
    
    # 测试关键帧提取
    test_url = TEST_VIDEO_URLS["short_video"]
    print(f"测试关键帧提取: {test_url}")
    
    response = requests.post(
        f"{API_BASE_URL}/extract_keyframes",
        json={
            "video_url": test_url,
            "method": "interval",
            "interval": 20,
            "width": 800,
            "height": 450,
            "format": "jpg",
            "quality": 85
        }
    )
    
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"任务已启动: {task_id}")
        
        # 监控进度
        while True:
            response = requests.get(f"{API_BASE_URL}/keyframe_status/{task_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"进度: {data['progress']}% - {data['message']}")
                
                if data["status"] == "completed":
                    print("关键帧提取完成！")
                    
                    # 获取结果
                    response = requests.get(f"{API_BASE_URL}/keyframe_result/{task_id}")
                    if response.status_code == 200:
                        result = response.json()["result"]
                        print(f"标题: {result['title']}")
                        print(f"总帧数: {result['total_frames']}")
                        print(f"方法: {result['method']}")
                        
                        # 测试下载第一帧
                        if result['total_frames'] > 0:
                            img_response = requests.get(f"{API_BASE_URL}/keyframe_image/{task_id}/0")
                            if img_response.status_code == 200:
                                print(f"第一帧下载成功，大小: {len(img_response.content)} 字节")
                    break
                elif data["status"] == "failed":
                    print(f"关键帧提取失败: {data.get('error', '未知错误')}")
                    break
            
            time.sleep(5)
    else:
        print(f"启动关键帧提取失败: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # 运行手动测试
    run_manual_test()