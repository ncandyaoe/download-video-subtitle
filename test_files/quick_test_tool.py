#!/usr/bin/env python3
"""
视频处理API快速测试工具
提供简单易用的API测试功能
"""

import requests
import time
import json
import sys
import argparse
from typing import Dict, Any, Optional

class QuickTestTool:
    """快速测试工具"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def test_health(self) -> bool:
        """测试健康检查"""
        print("🏥 测试健康检查...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 服务状态: {data.get('status')}")
                print(f"   📊 活跃任务: {data.get('active_transcription_tasks', 0) + data.get('active_download_tasks', 0) + data.get('active_keyframe_tasks', 0) + data.get('active_composition_tasks', 0)}")
                return True
            else:
                print(f"   ❌ 健康检查失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 健康检查异常: {str(e)}")
            return False
    
    def test_transcription(self, video_url: str) -> Optional[str]:
        """测试视频转录功能"""
        print(f"🎤 测试视频转录: {video_url}")
        
        try:
            # 启动转录任务
            response = self.session.post(
                f"{self.api_base_url}/generate_text_from_video",
                json={"video_url": video_url}
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 启动失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 快速检查任务状态（不等待完成）
            time.sleep(2)
            status_response = self.session.get(f"{self.api_base_url}/transcription_status/{task_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 当前状态: {status_data.get('status')} ({status_data.get('progress', 0)}%)")
            
            return task_id
            
        except Exception as e:
            print(f"   💥 转录测试异常: {str(e)}")
            return None
    
    def test_download(self, video_url: str, quality: str = "720p") -> Optional[str]:
        """测试视频下载功能"""
        print(f"📥 测试视频下载: {video_url} ({quality})")
        
        try:
            # 启动下载任务
            response = self.session.post(
                f"{self.api_base_url}/download_video",
                json={
                    "video_url": video_url,
                    "quality": quality,
                    "format": "mp4"
                }
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 启动失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 快速检查任务状态
            time.sleep(2)
            status_response = self.session.get(f"{self.api_base_url}/download_status/{task_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 当前状态: {status_data.get('status')} ({status_data.get('progress', 0)}%)")
            
            return task_id
            
        except Exception as e:
            print(f"   💥 下载测试异常: {str(e)}")
            return None
    
    def test_keyframes(self, video_url: str, method: str = "count", count: int = 5) -> Optional[str]:
        """测试关键帧提取功能"""
        print(f"🖼️ 测试关键帧提取: {video_url} ({method}, {count})")
        
        try:
            # 启动关键帧提取任务
            response = self.session.post(
                f"{self.api_base_url}/extract_keyframes",
                json={
                    "video_url": video_url,
                    "method": method,
                    "count": count,
                    "width": 640,
                    "height": 360,
                    "format": "jpg"
                }
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 启动失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 快速检查任务状态
            time.sleep(2)
            status_response = self.session.get(f"{self.api_base_url}/keyframe_status/{task_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 当前状态: {status_data.get('status')} ({status_data.get('progress', 0)}%)")
            
            return task_id
            
        except Exception as e:
            print(f"   💥 关键帧测试异常: {str(e)}")
            return None
    
    def test_composition(self, video_urls: list, composition_type: str = "concat") -> Optional[str]:
        """测试视频合成功能"""
        print(f"🎬 测试视频合成: {composition_type} ({len(video_urls)}个视频)")
        
        try:
            # 构建请求数据
            request_data = {
                "composition_type": composition_type,
                "videos": [{"video_url": url} for url in video_urls],
                "output_format": "mp4",
                "output_resolution": "1280x720"
            }
            
            # 启动合成任务
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 启动失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 快速检查任务状态
            time.sleep(2)
            status_response = self.session.get(f"{self.api_base_url}/composition_status/{task_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 当前状态: {status_data.get('status')} ({status_data.get('progress', 0)}%)")
            
            return task_id
            
        except Exception as e:
            print(f"   💥 合成测试异常: {str(e)}")
            return None
    
    def test_system_resources(self) -> bool:
        """测试系统资源监控"""
        print("💻 测试系统资源监控...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/resources")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 CPU使用率: {data.get('cpu_percent', 0):.1f}%")
                print(f"   📊 内存使用率: {data.get('memory_percent', 0):.1f}%")
                print(f"   📊 磁盘使用率: {data.get('disk_percent', 0):.1f}%")
                print(f"   📊 活跃任务: {data.get('active_tasks', 0)}")
                print(f"   📊 最大并发: {data.get('max_concurrent_tasks', 0)}")
                return True
            else:
                print(f"   ❌ 资源监控失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 资源监控异常: {str(e)}")
            return False
    
    def test_performance_stats(self) -> bool:
        """测试性能统计"""
        print("⚡ 测试性能统计...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/performance/stats")
            
            if response.status_code == 200:
                data = response.json()
                performance_data = data.get('data', {})
                
                # 缓存统计
                cache_stats = performance_data.get('cache_stats', {})
                print(f"   💾 缓存项数: {cache_stats.get('total_items', 0)}")
                print(f"   💾 缓存大小: {cache_stats.get('total_size_mb', 0):.2f}MB")
                
                # 硬件信息
                hardware_info = performance_data.get('hardware_info', {})
                print(f"   🔧 硬件加速: {'是' if hardware_info.get('has_hardware_acceleration') else '否'}")
                print(f"   🔧 首选编码器: {hardware_info.get('preferred_encoder', 'N/A')}")
                
                # 内存统计
                memory_stats = performance_data.get('memory_stats', {})
                memory_info = memory_stats.get('memory_info', {})
                print(f"   💾 可用内存: {memory_info.get('available_gb', 0):.1f}GB")
                
                return True
            else:
                print(f"   ❌ 性能统计失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 性能统计异常: {str(e)}")
            return False
    
    def test_all_tasks(self) -> bool:
        """测试所有任务列表"""
        print("📋 测试任务列表...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/tasks")
            
            if response.status_code == 200:
                data = response.json()
                
                total_tasks = 0
                for task_type, tasks in data.items():
                    if isinstance(tasks, dict):
                        task_count = len(tasks)
                        total_tasks += task_count
                        print(f"   📊 {task_type}: {task_count}个任务")
                
                print(f"   📊 总任务数: {total_tasks}")
                return True
            else:
                print(f"   ❌ 任务列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 任务列表异常: {str(e)}")
            return False
    
    def run_quick_test(self, test_video_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
        """运行快速测试"""
        print("🚀 开始快速测试")
        print("=" * 60)
        
        test_results = []
        
        # 基础功能测试
        tests = [
            ("健康检查", lambda: self.test_health()),
            ("系统资源", lambda: self.test_system_resources()),
            ("性能统计", lambda: self.test_performance_stats()),
            ("任务列表", lambda: self.test_all_tasks()),
            ("视频转录", lambda: self.test_transcription(test_video_url) is not None),
            ("视频下载", lambda: self.test_download(test_video_url) is not None),
            ("关键帧提取", lambda: self.test_keyframes(test_video_url) is not None),
            ("视频合成", lambda: self.test_composition([test_video_url, test_video_url]) is not None),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n🧪 {test_name}测试:")
                result = test_func()
                test_results.append((test_name, result))
                
                if result:
                    print(f"   ✅ {test_name}测试通过")
                else:
                    print(f"   ❌ {test_name}测试失败")
                    
            except Exception as e:
                print(f"   💥 {test_name}测试异常: {str(e)}")
                test_results.append((test_name, False))
        
        # 输出测试结果摘要
        print("\n" + "=" * 60)
        print("📊 快速测试结果摘要:")
        
        passed_tests = [name for name, result in test_results if result]
        failed_tests = [name for name, result in test_results if not result]
        
        print(f"   总测试数: {len(test_results)}")
        print(f"   通过: {len(passed_tests)}")
        print(f"   失败: {len(failed_tests)}")
        print(f"   成功率: {len(passed_tests)/len(test_results)*100:.1f}%")
        
        if passed_tests:
            print(f"\n✅ 通过的测试:")
            for test_name in passed_tests:
                print(f"   - {test_name}")
        
        if failed_tests:
            print(f"\n❌ 失败的测试:")
            for test_name in failed_tests:
                print(f"   - {test_name}")
        
        if len(passed_tests) == len(test_results):
            print("\n🎉 所有快速测试通过！")
            print("✅ API服务运行正常")
            return True
        else:
            print("\n⚠️ 部分测试失败，请检查系统状态")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='视频处理API快速测试工具')
    parser.add_argument('--api-url', default='http://localhost:7878', help='API服务地址')
    parser.add_argument('--video-url', default='https://www.youtube.com/watch?v=dQw4w9WgXcQ', 
                       help='测试用视频URL')
    parser.add_argument('--test', choices=['health', 'transcription', 'download', 'keyframes', 
                                          'composition', 'resources', 'performance', 'tasks', 'all'],
                       default='all', help='指定要运行的测试')
    
    args = parser.parse_args()
    
    tool = QuickTestTool(args.api_url)
    
    if args.test == 'all':
        success = tool.run_quick_test(args.video_url)
    elif args.test == 'health':
        success = tool.test_health()
    elif args.test == 'transcription':
        success = tool.test_transcription(args.video_url) is not None
    elif args.test == 'download':
        success = tool.test_download(args.video_url) is not None
    elif args.test == 'keyframes':
        success = tool.test_keyframes(args.video_url) is not None
    elif args.test == 'composition':
        success = tool.test_composition([args.video_url, args.video_url]) is not None
    elif args.test == 'resources':
        success = tool.test_system_resources()
    elif args.test == 'performance':
        success = tool.test_performance_stats()
    elif args.test == 'tasks':
        success = tool.test_all_tasks()
    else:
        print(f"未知的测试类型: {args.test}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()