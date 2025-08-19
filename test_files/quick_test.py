#!/usr/bin/env python3
"""
快速测试脚本 - 验证视频下载功能是否正常工作
"""

import requests
import time
import json

API_BASE = "http://localhost:7878"

def test_service_health():
    """测试服务健康状态"""
    print("🔍 检查服务健康状态...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务正常运行")
            print(f"   转录任务数: {data.get('active_transcription_tasks', 0)}")
            print(f"   下载任务数: {data.get('active_download_tasks', 0)}")
            return True
        else:
            print(f"❌ 服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return False

def test_download_api():
    """测试下载API基础功能"""
    print("\n🧪 测试下载API基础功能...")
    
    # 测试无效URL
    print("测试无效URL处理...")
    response = requests.post(
        f"{API_BASE}/download_video",
        json={"video_url": "invalid_url"},
        timeout=10
    )
    if response.status_code == 400:
        print("✅ 无效URL处理正常")
    else:
        print(f"❌ 无效URL处理异常: {response.status_code}")
    
    # 测试无效质量参数
    print("测试无效质量参数处理...")
    response = requests.post(
        f"{API_BASE}/download_video",
        json={
            "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "quality": "invalid_quality"
        },
        timeout=10
    )
    if response.status_code == 400:
        print("✅ 无效质量参数处理正常")
    else:
        print(f"❌ 无效质量参数处理异常: {response.status_code}")
    
    # 测试无效格式参数
    print("测试无效格式参数处理...")
    response = requests.post(
        f"{API_BASE}/download_video",
        json={
            "video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "format": "invalid_format"
        },
        timeout=10
    )
    if response.status_code == 400:
        print("✅ 无效格式参数处理正常")
    else:
        print(f"❌ 无效格式参数处理异常: {response.status_code}")

def test_download_flow():
    """测试完整的下载流程（使用短视频）"""
    print("\n🎬 测试完整下载流程...")
    
    # 使用一个短视频进行测试
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # 短视频
    
    print(f"启动下载任务: {test_url}")
    
    try:
        # 1. 启动下载任务
        response = requests.post(
            f"{API_BASE}/download_video",
            json={
                "video_url": test_url,
                "quality": "480p",  # 使用较低质量以加快测试
                "format": "mp4"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ 启动下载任务失败: {response.status_code} - {response.text}")
            return False
        
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ 任务已启动，ID: {task_id}")
        
        # 2. 监控下载进度（最多等待2分钟）
        print("监控下载进度...")
        max_attempts = 24  # 2分钟，每5秒检查一次
        
        for attempt in range(max_attempts):
            response = requests.get(f"{API_BASE}/download_status/{task_id}", timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 获取状态失败: {response.status_code}")
                return False
            
            status_data = response.json()
            status = status_data["status"]
            progress = status_data["progress"]
            message = status_data["message"]
            
            print(f"   进度: {progress}% - {message}")
            
            if status == "completed":
                print("✅ 下载完成！")
                
                # 3. 获取结果
                response = requests.get(f"{API_BASE}/download_result/{task_id}", timeout=10)
                if response.status_code == 200:
                    result = response.json()["result"]
                    print(f"   标题: {result['title']}")
                    print(f"   文件大小: {result['file_size'] / 1024 / 1024:.1f}MB")
                    print(f"   文件路径: {result['file_path']}")
                    return True
                else:
                    print(f"❌ 获取结果失败: {response.status_code}")
                    return False
                    
            elif status == "failed":
                error = status_data.get("error", "未知错误")
                print(f"❌ 下载失败: {error}")
                return False
            
            time.sleep(5)
        
        print("❌ 下载超时")
        return False
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def main():
    """主测试函数"""
    print("=== 视频下载功能快速测试 ===")
    
    # 1. 检查服务健康状态
    if not test_service_health():
        print("\n❌ 服务不可用，请先启动服务")
        print("启动命令: python run.py 或 docker-compose up -d")
        return
    
    # 2. 测试API基础功能
    test_download_api()
    
    # 3. 询问是否进行完整流程测试
    print("\n" + "="*50)
    user_input = input("是否进行完整下载流程测试？这将下载一个真实视频 (y/N): ")
    
    if user_input.lower() in ['y', 'yes']:
        success = test_download_flow()
        if success:
            print("\n🎉 所有测试通过！视频下载功能正常工作")
        else:
            print("\n⚠️  完整流程测试失败，请检查日志")
    else:
        print("\n✅ 基础功能测试完成")
    
    print("\n=== 测试结束 ===")

if __name__ == "__main__":
    main()