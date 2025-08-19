#!/usr/bin/env python3
"""
本地视频合成使用示例
演示如何使用本地视频文件进行合成
"""

import requests
import time
import json
import os

def compose_local_videos(video_paths, api_url="http://localhost:7878"):
    """
    合成本地视频文件
    
    Args:
        video_paths: 本地视频文件路径列表
        api_url: API服务地址
    
    Returns:
        合成结果信息
    """
    
    # 验证文件存在
    for path in video_paths:
        if not os.path.exists(path):
            print(f"❌ 文件不存在: {path}")
            return None
        print(f"✅ 找到视频文件: {path} ({os.path.getsize(path) / 1024 / 1024:.1f}MB)")
    
    # 构建请求数据
    request_data = {
        "composition_type": "concat",
        "videos": [{"video_url": path} for path in video_paths],
        "output_format": "mp4",
        "output_resolution": "1280x720"
    }
    
    print(f"\\n📤 发送合成请求到: {api_url}")
    print(f"   合成类型: {request_data['composition_type']}")
    print(f"   视频数量: {len(request_data['videos'])}")
    
    try:
        # 发送请求
        session = requests.Session()
        session.timeout = 30
        
        response = session.post(f"{api_url}/compose_video", json=request_data)
        
        if response.status_code == 503:
            print("⚠️ 系统资源不足，请稍后重试")
            return None
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
        
        data = response.json()
        task_id = data.get('task_id')
        
        if not task_id:
            print("❌ 未获取到任务ID")
            return None
        
        print(f"✅ 合成任务已启动: {task_id}")
        
        # 监控任务进度
        print("\\n⏳ 监控合成进度...")
        
        while True:
            status_response = session.get(f"{api_url}/composition_status/{task_id}")
            
            if status_response.status_code != 200:
                print(f"⚠️ 查询状态失败: {status_response.status_code}")
                time.sleep(5)
                continue
            
            status_data = status_response.json()
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            message = status_data.get('message', '')
            
            print(f"   📊 进度: {progress}% - {message}")
            
            if status == 'completed':
                print("\\n🎉 视频合成完成！")
                
                # 获取详细结果
                result_response = session.get(f"{api_url}/composition_result/{task_id}")
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    result = result_data.get('result', {})
                    
                    print("\\n📊 合成结果:")
                    print(f"   输出文件: {result.get('output_file', 'N/A')}")
                    print(f"   文件大小: {result.get('output_file_size', 0) / 1024 / 1024:.1f}MB")
                    print(f"   视频时长: {result.get('output_duration', 0):.1f}秒")
                    print(f"   处理时间: {result.get('processing_time', 0):.1f}秒")
                    
                    # 检查是否使用了硬件加速
                    perf_stats = result.get('performance_stats', {})
                    if perf_stats.get('hardware_acceleration'):
                        encoder = perf_stats.get('encoder_used', 'unknown')
                        print(f"   硬件加速: ✅ ({encoder})")
                    else:
                        print(f"   硬件加速: ❌ (使用软件编码)")
                    
                    return result
                else:
                    print("⚠️ 无法获取详细结果")
                    return {"task_id": task_id, "status": "completed"}
                
            elif status == 'failed':
                error = status_data.get('error', 'Unknown error')
                print(f"\\n❌ 合成失败: {error}")
                return None
            
            time.sleep(10)  # 每10秒检查一次
    
    except requests.exceptions.RequestException as e:
        print(f"💥 网络请求异常: {str(e)}")
        return None
    except Exception as e:
        print(f"💥 处理异常: {str(e)}")
        return None

def main():
    """主函数 - 使用示例"""
    print("🎬 本地视频合成使用示例")
    print("=" * 50)
    
    # 示例1: 使用绝对路径
    print("\\n📝 示例1: 使用绝对路径")
    video_paths_1 = [
        "/Users/mulele/Documents/4-n8ndata/video/小蝌蚪找妈妈/A group of small tadpoles swim in a clear pond, looking confused..mp4",  # 替换为实际路径
        "/Users/mulele/Documents/4-n8ndata/video/小蝌蚪找妈妈/The tadpoles finally meet their mom, a graceful frog, and hug her..mp4"   # 替换为实际路径
    ]
    
    print("视频文件路径:")
    for i, path in enumerate(video_paths_1):
        print(f"  {i+1}. {path}")
    
    # 检查文件是否存在
    existing_files = [path for path in video_paths_1 if os.path.exists(path)]
    
    if len(existing_files) >= 2:
        print("\\n🚀 开始合成...")
        result = compose_local_videos(existing_files)
        
        if result:
            print("\\n✅ 合成成功完成！")
        else:
            print("\\n❌ 合成失败")
    else:
        print("\\n⚠️ 请修改脚本中的视频文件路径为实际存在的文件")
        print("\\n💡 使用方法:")
        print("1. 准备2个或更多本地视频文件")
        print("2. 修改脚本中的video_paths_1列表，填入实际的文件路径")
        print("3. 确保API服务正在运行 (python run.py)")
        print("4. 重新运行此脚本")
        
        print("\\n📋 支持的文件格式:")
        formats = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".3gp"]
        print(f"   {', '.join(formats)}")
        
        print("\\n🔧 API服务启动命令:")
        print("   python run.py")
        
        print("\\n🌐 API服务地址:")
        print("   http://localhost:7878")
    
    # 示例2: 演示不同路径格式
    print("\\n" + "=" * 50)
    print("📝 支持的路径格式示例:")
    
    path_examples = [
        {
            "format": "绝对路径",
            "example": "/Users/username/Videos/video.mp4",
            "description": "完整的文件系统路径"
        },
        {
            "format": "相对路径", 
            "example": "./videos/video.mp4",
            "description": "相对于当前工作目录的路径"
        },
        {
            "format": "file:// 协议",
            "example": "file:///Users/username/Videos/video.mp4", 
            "description": "使用file协议的URL格式"
        },
        {
            "format": "Windows路径",
            "example": "C:\\\\Users\\\\username\\\\Videos\\\\video.mp4",
            "description": "Windows系统的文件路径"
        }
    ]
    
    for example in path_examples:
        print(f"\\n   📁 {example['format']}:")
        print(f"      示例: {example['example']}")
        print(f"      说明: {example['description']}")
    
    print("\\n" + "=" * 50)
    print("💡 提示:")
    print("- 确保视频文件存在且可读")
    print("- 支持混合使用本地文件和在线URL")
    print("- 文件大小限制: 2GB")
    print("- 视频时长限制: 3小时")
    print("- 推荐使用MP4格式以获得最佳兼容性")

if __name__ == "__main__":
    main()