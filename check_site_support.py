#!/usr/bin/env python3
"""
检查特定网站是否支持关键帧提取
"""

import requests
import sys
import time

API_BASE = "http://localhost:7878"

def check_site_support(video_url):
    """检查指定URL是否支持关键帧提取"""
    print(f"检查网站支持: {video_url}")
    print("="*60)
    
    # 1. 检查服务状态
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code != 200:
            print("❌ 服务不可用，请先启动服务")
            return False
        print("✅ 服务正常运行")
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return False
    
    # 2. 测试URL验证
    print(f"\n🔍 测试URL验证...")
    try:
        response = requests.post(
            f"{API_BASE}/extract_keyframes",
            json={
                "video_url": video_url,
                "method": "count",
                "count": 1,  # 只提取1帧进行快速测试
                "width": 640,
                "height": 360
            },
            timeout=30
        )
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data["task_id"]
            print(f"✅ URL验证通过，任务ID: {task_id}")
        elif response.status_code == 400:
            error_detail = response.json().get('detail', '未知错误')
            print(f"❌ URL验证失败: {error_detail}")
            return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False
    
    # 3. 监控任务状态（简短测试）
    print(f"\n⏳ 监控任务状态（最多等待2分钟）...")
    
    for attempt in range(24):  # 2分钟，每5秒检查一次
        try:
            status_response = requests.get(f"{API_BASE}/keyframe_status/{task_id}", timeout=10)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data["status"]
                progress = status_data["progress"]
                message = status_data["message"]
                
                print(f"   进度: {progress}% - {message}")
                
                if status == "completed":
                    print(f"✅ 网站完全支持！关键帧提取成功完成")
                    
                    # 获取结果信息
                    result_response = requests.get(f"{API_BASE}/keyframe_result/{task_id}", timeout=10)
                    if result_response.status_code == 200:
                        result = result_response.json()["result"]
                        print(f"   📹 视频标题: {result.get('title', 'N/A')}")
                        print(f"   ⏱️  视频时长: {result.get('duration', 0)}秒")
                        print(f"   🖼️  提取帧数: {result.get('total_frames', 0)}")
                    
                    return True
                    
                elif status == "failed":
                    error = status_data.get('error', '未知错误')
                    print(f"❌ 关键帧提取失败: {error}")
                    
                    # 分析失败原因
                    if "HTTP Error 403" in error:
                        print("   💡 可能原因: 视频有访问限制或需要登录")
                    elif "HTTP Error 404" in error:
                        print("   💡 可能原因: 视频不存在或URL无效")
                    elif "Unsupported URL" in error:
                        print("   💡 可能原因: yt-dlp不支持此网站")
                    elif "Private video" in error:
                        print("   💡 可能原因: 视频为私有，需要权限访问")
                    else:
                        print("   💡 建议: 检查视频URL是否正确，或稍后重试")
                    
                    return False
                    
            else:
                print(f"   ❌ 状态查询失败: {status_response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 状态查询异常: {e}")
            return False
        
        time.sleep(5)
    
    print(f"⏳ 测试超时，但URL验证通过，网站可能支持但处理较慢")
    return None  # 不确定

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python check_site_support.py <video_url>")
        print("")
        print("示例:")
        print("  python check_site_support.py 'https://www.youtube.com/watch?v=VIDEO_ID'")
        print("  python check_site_support.py 'https://www.bilibili.com/video/BV1xx411c7mu'")
        print("  python check_site_support.py 'https://vimeo.com/148751763'")
        print("")
        print("支持的网站列表: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md")
        sys.exit(1)
    
    video_url = sys.argv[1]
    result = check_site_support(video_url)
    
    print("\n" + "="*60)
    if result is True:
        print("🎉 结论: 该网站完全支持关键帧提取功能！")
        print("   你可以使用所有功能：转录、下载、关键帧提取")
    elif result is False:
        print("❌ 结论: 该网站或视频不支持关键帧提取")
        print("   请检查URL是否正确，或尝试其他视频")
    else:
        print("⚠️  结论: 网站可能支持，但需要更长时间处理")
        print("   建议使用完整测试或稍后重试")
    
    print("\n📚 更多信息:")
    print("- 支持的网站文档: SUPPORTED_SITES.md")
    print("- 完整功能测试: python test_keyframes_multisite.py")
    print("- API使用文档: API_DOCUMENTATION.md")

if __name__ == "__main__":
    main()