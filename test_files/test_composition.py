#!/usr/bin/env python3
"""
视频合成功能测试脚本
测试音频视频字幕三合一合成功能
"""

import requests
import time
import json
import sys
import os

API_BASE_URL = "http://localhost:7878"

def test_audio_video_subtitle_composition():
    """测试音频视频字幕三合一合成"""
    print("🎬 开始测试音频视频字幕三合一合成功能")
    
    # 测试参数 - 请根据你的实际文件路径修改
    test_data = {
        "composition_type": "audio_video_subtitle",
        "videos": [
            {
                "video_url": "/path/to/your/video.mp4"  # 请修改为实际的视频文件路径
            }
        ],
        "audio_file": "/path/to/your/audio.mp3",  # 请修改为实际的音频文件路径
        "subtitle_file": "/path/to/your/subtitle.srt",  # 请修改为实际的字幕文件路径（可选）
        "output_format": "mp4",
        "output_quality": "720p"
    }
    
    print(f"📝 测试参数:")
    print(f"   视频文件: {test_data['videos'][0]['video_url']}")
    print(f"   音频文件: {test_data['audio_file']}")
    print(f"   字幕文件: {test_data.get('subtitle_file', '无')}")
    
    # 检查文件是否存在
    video_file = test_data['videos'][0]['video_url']
    audio_file = test_data['audio_file']
    subtitle_file = test_data.get('subtitle_file')
    
    if not os.path.exists(video_file):
        print(f"❌ 视频文件不存在: {video_file}")
        print("请修改 test_data 中的文件路径为实际存在的文件")
        return False
    
    if not os.path.exists(audio_file):
        print(f"❌ 音频文件不存在: {audio_file}")
        print("请修改 test_data 中的文件路径为实际存在的文件")
        return False
    
    if subtitle_file and not os.path.exists(subtitle_file):
        print(f"❌ 字幕文件不存在: {subtitle_file}")
        print("请修改 test_data 中的文件路径为实际存在的文件，或设置为 None")
        return False
    
    try:
        # 1. 启动合成任务
        print("\n🚀 启动合成任务...")
        response = requests.post(f"{API_BASE_URL}/compose_video", json=test_data)
        
        if response.status_code != 200:
            print(f"❌ 启动任务失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
        
        result = response.json()
        task_id = result["task_id"]
        print(f"✅ 任务启动成功，任务ID: {task_id}")
        
        # 2. 轮询任务状态
        print("\n📊 监控任务进度...")
        while True:
            response = requests.get(f"{API_BASE_URL}/composition_status/{task_id}")
            
            if response.status_code != 200:
                print(f"❌ 查询状态失败: {response.status_code}")
                return False
            
            status = response.json()
            progress = status["progress"]
            message = status["message"]
            current_status = status["status"]
            
            print(f"📈 进度: {progress}% - {message}")
            
            if current_status == "completed":
                print("🎉 任务完成！")
                break
            elif current_status == "failed":
                print(f"❌ 任务失败: {status.get('error', '未知错误')}")
                return False
            
            time.sleep(2)  # 等待2秒后再次查询
        
        # 3. 获取结果
        print("\n📋 获取合成结果...")
        response = requests.get(f"{API_BASE_URL}/composition_result/{task_id}")
        
        if response.status_code != 200:
            print(f"❌ 获取结果失败: {response.status_code}")
            return False
        
        result = response.json()["result"]
        
        print("✅ 合成结果:")
        print(f"   输出文件: {result['output_file_path']}")
        print(f"   文件大小: {result['file_size'] / 1024 / 1024:.1f} MB")
        print(f"   视频时长: {result['duration']:.1f} 秒")
        print(f"   分辨率: {result['resolution']}")
        print(f"   处理时间: {result['processing_time']:.1f} 秒")
        
        # 4. 可选：下载文件
        download_choice = input("\n💾 是否下载合成的视频文件？(y/n): ").lower().strip()
        if download_choice == 'y':
            print("📥 开始下载...")
            response = requests.get(f"{API_BASE_URL}/composition_file/{task_id}")
            
            if response.status_code == 200:
                output_filename = f"composed_video_{task_id}.mp4"
                with open(output_filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ 文件下载完成: {output_filename}")
            else:
                print(f"❌ 下载失败: {response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器，请确保服务器正在运行")
        print("启动命令: python api.py 或 uvicorn api:app --host 0.0.0.0 --port 7878")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        return False

def test_health_check():
    """测试健康检查"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print("✅ API服务器运行正常")
            print(f"   活跃合成任务: {health.get('active_composition_tasks', 0)}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        return False

def main():
    """主函数"""
    print("🎬 视频合成功能测试工具")
    print("=" * 50)
    
    # 检查服务器状态
    if not test_health_check():
        print("\n请先启动API服务器:")
        print("  python api.py")
        print("或")
        print("  uvicorn api:app --host 0.0.0.0 --port 7878")
        return
    
    print("\n" + "=" * 50)
    
    # 提示用户修改测试参数
    print("⚠️  请注意:")
    print("   在运行测试前，请修改 test_composition.py 中的文件路径")
    print("   确保视频文件、音频文件和字幕文件存在")
    print()
    
    choice = input("是否继续测试？(y/n): ").lower().strip()
    if choice != 'y':
        print("测试已取消")
        return
    
    # 执行测试
    success = test_audio_video_subtitle_composition()
    
    if success:
        print("\n🎉 测试完成！音频视频字幕合成功能正常工作")
    else:
        print("\n❌ 测试失败，请检查错误信息")

if __name__ == "__main__":
    main()