#!/usr/bin/env python3
"""
快速测试宽高比保持功能
"""

import requests
import json
import time
import os

API_BASE_URL = "http://localhost:7878"

def test_aspect_ratio():
    """测试宽高比保持功能"""
    print("🎬 快速测试宽高比保持功能")
    
    video1 = "downloads/test_16_9.mp4"      # 16:9 视频
    video2 = "downloads/test_video_4_3.mp4" # 4:3 视频
    
    if not os.path.exists(video1) or not os.path.exists(video2):
        print("❌ 测试视频文件不存在")
        return False
    
    # 构建请求参数
    params = {
        "composition_type": "side_by_side",
        "videos": [
            {"video_url": video1},
            {"video_url": video2}
        ],
        "layout": "horizontal",
        "output_format": "mp4",
        "output_quality": "720p"
    }
    
    try:
        print("📤 发送合成请求...")
        response = requests.post(f"{API_BASE_URL}/compose_video", json=params)
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            return False
        
        result = response.json()
        task_id = result.get("task_id")
        print(f"✅ 任务创建成功，任务ID: {task_id}")
        
        # 轮询任务状态
        print("⏳ 等待合成完成...")
        max_wait_time = 60  # 最多等待1分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = requests.get(f"{API_BASE_URL}/composition_status/{task_id}")
            if status_response.status_code != 200:
                print(f"❌ 获取状态失败: {status_response.status_code}")
                return False
            
            status = status_response.json()
            print(f"📊 进度: {status['progress']}% - {status['message']}")
            
            if status["status"] == "completed":
                print("✅ 合成完成!")
                
                # 获取结果
                result_response = requests.get(f"{API_BASE_URL}/composition_result/{task_id}")
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    result = result_data.get("result", {})
                    output_file = result.get("output_file_path")
                    print(f"📁 输出文件: {output_file}")
                    
                    if os.path.exists(output_file):
                        file_size = os.path.getsize(output_file) / (1024 * 1024)
                        print(f"📊 文件大小: {file_size:.2f} MB")
                        
                        # 检查视频信息
                        print("\n📺 视频信息对比:")
                        check_video_info(video1, "输入视频1 (16:9)")
                        check_video_info(video2, "输入视频2 (4:3)")
                        check_video_info(output_file, "合成结果")
                        
                        return True
                    else:
                        print(f"❌ 输出文件不存在: {output_file}")
                        return False
                        
            elif status["status"] == "failed":
                print(f"❌ 合成失败: {status.get('error', '未知错误')}")
                return False
            
            time.sleep(2)
        
        print("❌ 等待超时")
        return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def check_video_info(video_file, label):
    """检查视频信息"""
    try:
        import subprocess
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    duration = float(stream.get('duration', 0))
                    aspect_ratio = width / height if height > 0 else 0
                    
                    print(f"   {label}:")
                    print(f"     分辨率: {width}x{height}")
                    print(f"     宽高比: {aspect_ratio:.2f}")
                    print(f"     时长: {duration:.2f}秒")
                    break
                    
    except Exception as e:
        print(f"❌ 检查 {label} 信息失败: {e}")

if __name__ == "__main__":
    print("🚀 开始快速测试宽高比保持功能")
    
    success = test_aspect_ratio()
    
    if success:
        print("\n✅ 测试成功!")
        print("📝 说明: 修复后的功能会保持每个视频的原始宽高比，")
        print("      不会拉伸变形，空白区域会用黑色填充。")
    else:
        print("\n❌ 测试失败!")