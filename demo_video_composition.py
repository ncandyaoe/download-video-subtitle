#!/usr/bin/env python3
"""
视频合成功能演示脚本
展示各种视频合成场景的使用方法
"""

import requests
import time
import json
import sys
from typing import Dict, Any, Optional

class VideoCompositionDemo:
    """视频合成演示类"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 30
        
        # 演示用的视频URL（可以替换为实际的视频URL）
        self.demo_videos = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # 经典测试视频
            "https://www.youtube.com/watch?v=9bZkp7q19f0",  # 另一个测试视频
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # 第三个测试视频
        ]
        
        self.demo_audio = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def wait_for_task_completion(self, task_id: str, task_type: str = "composition", max_wait_time: int = 600) -> Dict[str, Any]:
        """等待任务完成"""
        print(f"⏳ 等待任务完成: {task_id[:8]}...")
        
        status_endpoints = {
            'composition': f'/composition_status/{task_id}',
            'transcription': f'/transcription_status/{task_id}',
            'download': f'/download_status/{task_id}',
            'keyframe': f'/keyframe_status/{task_id}'
        }
        
        endpoint = status_endpoints.get(task_type, f'/composition_status/{task_id}')
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{self.api_base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    progress = data.get('progress', 0)
                    message = data.get('message', '')
                    
                    print(f"   📊 进度: {progress}% - {message}")
                    
                    if status == 'completed':
                        print(f"   ✅ 任务完成: {task_id[:8]}")
                        return data
                    elif status == 'failed':
                        print(f"   ❌ 任务失败: {data.get('error', 'Unknown error')}")
                        return data
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                print(f"   ⚠️ 查询状态失败: {str(e)}")
                time.sleep(5)
        
        print(f"   ⏰ 任务超时: {task_id[:8]}")
        return {'status': 'timeout', 'error': 'Task execution timeout'}
    
    def demo_video_concat(self):
        """演示视频拼接功能"""
        print("\n🎬 演示1: 视频拼接 (concat)")
        print("=" * 50)
        
        request_data = {
            "composition_type": "concat",
            "videos": [
                {"video_url": self.demo_videos[0]},
                {"video_url": self.demo_videos[1]}
            ],
            "output_format": "mp4",
            "output_resolution": "1280x720"
        }
        
        print("📤 发送合成请求...")
        print(f"   合成类型: {request_data['composition_type']}")
        print(f"   视频数量: {len(request_data['videos'])}")
        print(f"   输出格式: {request_data['output_format']}")
        print(f"   输出分辨率: {request_data['output_resolution']}")
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足，跳过此演示")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 等待任务完成
            result = self.wait_for_task_completion(task_id, 'composition', 300)
            
            if result.get('status') == 'completed':
                print("   🎉 视频拼接演示完成！")
                
                # 获取详细结果
                result_response = self.session.get(f"{self.api_base_url}/composition_result/{task_id}")
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    composition_result = result_data.get('result', {})
                    
                    print(f"   📊 输出文件大小: {composition_result.get('output_file_size', 0) / 1024 / 1024:.1f}MB")
                    print(f"   📊 输出时长: {composition_result.get('output_duration', 0):.1f}秒")
                    print(f"   📊 处理时间: {composition_result.get('processing_time', 0):.1f}秒")
                    
                    return task_id
            else:
                print(f"   ❌ 任务失败: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
            return None
    
    def demo_picture_in_picture(self):
        """演示画中画功能"""
        print("\n🖼️ 演示2: 画中画 (picture_in_picture)")
        print("=" * 50)
        
        request_data = {
            "composition_type": "picture_in_picture",
            "videos": [
                {
                    "video_url": self.demo_videos[0],
                    "role": "main"
                },
                {
                    "video_url": self.demo_videos[1],
                    "role": "overlay",
                    "position": {
                        "x": 50,
                        "y": 50,
                        "width": 320,
                        "height": 240
                    },
                    "opacity": 0.8
                }
            ],
            "output_format": "mp4",
            "output_resolution": "1280x720"
        }
        
        print("📤 发送画中画合成请求...")
        print(f"   主视频: {self.demo_videos[0]}")
        print(f"   叠加视频: {self.demo_videos[1]}")
        print(f"   叠加位置: (50, 50)")
        print(f"   叠加大小: 320x240")
        print(f"   透明度: 0.8")
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足，跳过此演示")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 等待任务完成
            result = self.wait_for_task_completion(task_id, 'composition', 300)
            
            if result.get('status') == 'completed':
                print("   🎉 画中画演示完成！")
                return task_id
            else:
                print(f"   ❌ 任务失败: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
            return None
    
    def demo_side_by_side(self):
        """演示并排显示功能"""
        print("\n↔️ 演示3: 并排显示 (side_by_side)")
        print("=" * 50)
        
        request_data = {
            "composition_type": "side_by_side",
            "videos": [
                {"video_url": self.demo_videos[0]},
                {"video_url": self.demo_videos[1]}
            ],
            "layout": "horizontal",
            "output_format": "mp4",
            "output_resolution": "1280x720"
        }
        
        print("📤 发送并排显示合成请求...")
        print(f"   左侧视频: {self.demo_videos[0]}")
        print(f"   右侧视频: {self.demo_videos[1]}")
        print(f"   布局方式: {request_data['layout']}")
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足，跳过此演示")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 等待任务完成
            result = self.wait_for_task_completion(task_id, 'composition', 300)
            
            if result.get('status') == 'completed':
                print("   🎉 并排显示演示完成！")
                return task_id
            else:
                print(f"   ❌ 任务失败: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
            return None
    
    def demo_grid_layout(self):
        """演示网格布局功能"""
        print("\n⊞ 演示4: 网格布局 (grid)")
        print("=" * 50)
        
        request_data = {
            "composition_type": "grid",
            "videos": [
                {"video_url": self.demo_videos[0]},
                {"video_url": self.demo_videos[1]},
                {"video_url": self.demo_videos[0]},  # 重复使用演示
                {"video_url": self.demo_videos[1]}   # 重复使用演示
            ],
            "grid_size": "2x2",
            "output_format": "mp4",
            "output_resolution": "1280x720"
        }
        
        print("📤 发送网格布局合成请求...")
        print(f"   视频数量: {len(request_data['videos'])}")
        print(f"   网格大小: {request_data['grid_size']}")
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足，跳过此演示")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 等待任务完成
            result = self.wait_for_task_completion(task_id, 'composition', 300)
            
            if result.get('status') == 'completed':
                print("   🎉 网格布局演示完成！")
                return task_id
            else:
                print(f"   ❌ 任务失败: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
            return None
    
    def demo_audio_video_subtitle(self):
        """演示音频视频字幕合成功能"""
        print("\n🎵 演示5: 音频视频字幕合成 (audio_video_subtitle)")
        print("=" * 50)
        
        # 首先创建一个简单的SRT字幕文件
        subtitle_content = """1
00:00:00,000 --> 00:00:05,000
这是第一段字幕

2
00:00:05,000 --> 00:00:10,000
这是第二段字幕

3
00:00:10,000 --> 00:00:15,000
这是第三段字幕
"""
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(subtitle_content)
            subtitle_file = f.name
        
        request_data = {
            "composition_type": "audio_video_subtitle",
            "videos": [
                {"video_url": self.demo_videos[0]}
            ],
            "audio_file": self.demo_audio,
            "subtitle_file": subtitle_file,
            "audio_settings": {
                "volume": 0.8,
                "start_offset": 0.0
            },
            "subtitle_settings": {
                "font_size": 24,
                "font_color": "white",
                "outline_color": "black"
            },
            "output_format": "mp4"
        }
        
        print("📤 发送音频视频字幕合成请求...")
        print(f"   视频: {self.demo_videos[0]}")
        print(f"   音频: {self.demo_audio}")
        print(f"   字幕文件: {subtitle_file}")
        print(f"   音频音量: {request_data['audio_settings']['volume']}")
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足，跳过此演示")
                return None
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 等待任务完成
            result = self.wait_for_task_completion(task_id, 'composition', 300)
            
            if result.get('status') == 'completed':
                print("   🎉 音频视频字幕合成演示完成！")
                return task_id
            else:
                print(f"   ❌ 任务失败: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
            return None
        finally:
            # 清理临时字幕文件
            try:
                os.unlink(subtitle_file)
            except:
                pass
    
    def demo_performance_features(self):
        """演示性能优化功能"""
        print("\n⚡ 演示6: 性能优化功能")
        print("=" * 50)
        
        try:
            # 获取性能统计
            print("📊 获取性能统计信息...")
            response = self.session.get(f"{self.api_base_url}/system/performance/stats")
            
            if response.status_code == 200:
                data = response.json()
                performance_data = data.get('data', {})
                
                # 显示缓存统计
                cache_stats = performance_data.get('cache_stats', {})
                print(f"   💾 缓存统计:")
                print(f"      - 缓存项数: {cache_stats.get('total_items', 0)}")
                print(f"      - 缓存大小: {cache_stats.get('total_size_mb', 0):.2f}MB")
                print(f"      - 使用率: {cache_stats.get('usage_percent', 0):.1f}%")
                
                # 显示硬件信息
                hardware_info = performance_data.get('hardware_info', {})
                print(f"   🔧 硬件加速:")
                print(f"      - 硬件加速: {'是' if hardware_info.get('has_hardware_acceleration') else '否'}")
                print(f"      - 首选编码器: {hardware_info.get('preferred_encoder', 'N/A')}")
                print(f"      - 可用编码器: {len(hardware_info.get('available_encoders', []))}")
                
                # 显示内存统计
                memory_stats = performance_data.get('memory_stats', {})
                memory_info = memory_stats.get('memory_info', {})
                print(f"   💾 内存统计:")
                print(f"      - 总内存: {memory_info.get('total_gb', 0):.1f}GB")
                print(f"      - 可用内存: {memory_info.get('available_gb', 0):.1f}GB")
                print(f"      - 使用率: {memory_info.get('used_percent', 0):.1f}%")
            
            # 演示内存清理
            print("\n🧹 执行内存清理...")
            cleanup_response = self.session.post(f"{self.api_base_url}/system/performance/memory/cleanup")
            
            if cleanup_response.status_code == 200:
                cleanup_data = cleanup_response.json()
                print(f"   ✅ 内存清理完成: {cleanup_data.get('message')}")
            
            # 演示系统优化
            print("\n⚡ 执行系统优化...")
            optimize_response = self.session.post(f"{self.api_base_url}/system/performance/optimize")
            
            if optimize_response.status_code == 200:
                optimize_data = optimize_response.json()
                print(f"   ✅ 系统优化完成: {optimize_data.get('message')}")
            
            print("   🎉 性能优化功能演示完成！")
            
        except Exception as e:
            print(f"   💥 演示异常: {str(e)}")
    
    def run_all_demos(self):
        """运行所有演示"""
        print("🚀 开始视频合成功能演示")
        print("=" * 80)
        
        # 检查API可用性
        if not self.check_api_availability():
            print("❌ API服务不可用，请确保服务正在运行")
            return False
        
        print("✅ API服务可用，开始演示...")
        
        # 运行各种演示
        demos = [
            ("视频拼接", self.demo_video_concat),
            ("画中画", self.demo_picture_in_picture),
            ("并排显示", self.demo_side_by_side),
            ("网格布局", self.demo_grid_layout),
            ("音频视频字幕合成", self.demo_audio_video_subtitle),
            ("性能优化功能", self.demo_performance_features),
        ]
        
        completed_demos = []
        failed_demos = []
        
        for demo_name, demo_func in demos:
            try:
                print(f"\n🎯 开始演示: {demo_name}")
                result = demo_func()
                
                if result is not None or demo_name == "性能优化功能":
                    completed_demos.append(demo_name)
                    print(f"✅ {demo_name} 演示成功")
                else:
                    failed_demos.append(demo_name)
                    print(f"❌ {demo_name} 演示失败")
                
                # 演示间隔
                time.sleep(2)
                
            except Exception as e:
                failed_demos.append(demo_name)
                print(f"💥 {demo_name} 演示异常: {str(e)}")
        
        # 输出演示结果摘要
        print("\n" + "=" * 80)
        print("📊 演示结果摘要:")
        print(f"   总演示数: {len(demos)}")
        print(f"   成功: {len(completed_demos)}")
        print(f"   失败: {len(failed_demos)}")
        
        if completed_demos:
            print(f"\n✅ 成功的演示:")
            for demo in completed_demos:
                print(f"   - {demo}")
        
        if failed_demos:
            print(f"\n❌ 失败的演示:")
            for demo in failed_demos:
                print(f"   - {demo}")
        
        if len(completed_demos) == len(demos):
            print("\n🎉 所有演示都成功完成！")
            print("✅ 视频合成功能运行正常")
            return True
        else:
            print("\n⚠️ 部分演示失败，请检查系统状态")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='视频合成功能演示脚本')
    parser.add_argument('--api-url', default='http://localhost:7878', help='API服务地址')
    parser.add_argument('--demo', choices=['concat', 'pip', 'side', 'grid', 'avs', 'perf', 'all'], 
                       default='all', help='指定要运行的演示')
    
    args = parser.parse_args()
    
    demo = VideoCompositionDemo(args.api_url)
    
    if args.demo == 'all':
        success = demo.run_all_demos()
    elif args.demo == 'concat':
        success = demo.demo_video_concat() is not None
    elif args.demo == 'pip':
        success = demo.demo_picture_in_picture() is not None
    elif args.demo == 'side':
        success = demo.demo_side_by_side() is not None
    elif args.demo == 'grid':
        success = demo.demo_grid_layout() is not None
    elif args.demo == 'avs':
        success = demo.demo_audio_video_subtitle() is not None
    elif args.demo == 'perf':
        demo.demo_performance_features()
        success = True
    else:
        print(f"未知的演示类型: {args.demo}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()