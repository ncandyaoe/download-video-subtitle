#!/usr/bin/env python3
"""
本地视频合成功能测试脚本
测试修改后的API是否能正确处理本地视频文件
"""

import requests
import time
import json
import os
import tempfile
import subprocess
from typing import Dict, Any

class LocalVideoCompositionTester:
    """本地视频合成测试器"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 30
        self.test_videos = []
    
    def create_test_videos(self) -> list:
        """创建测试用的本地视频文件"""
        print("🎬 创建测试视频文件...")
        
        test_videos = []
        
        for i in range(2):
            # 创建临时视频文件
            with tempfile.NamedTemporaryFile(suffix=f'_test_{i+1}.mp4', delete=False) as f:
                video_path = f.name
            
            # 使用FFmpeg创建5秒的测试视频
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'testsrc=duration=5:size=640x480:rate=30',
                '-f', 'lavfi', 
                '-i', f'sine=frequency=1000:duration=5',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-t', '5',
                video_path
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    test_videos.append(video_path)
                    print(f"   ✅ 创建测试视频 {i+1}: {video_path} ({file_size / 1024:.1f}KB)")
                else:
                    print(f"   ❌ 创建测试视频 {i+1} 失败: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"   ⏰ 创建测试视频 {i+1} 超时")
            except Exception as e:
                print(f"   💥 创建测试视频 {i+1} 异常: {str(e)}")
        
        self.test_videos = test_videos
        return test_videos
    
    def cleanup_test_videos(self):
        """清理测试视频文件"""
        print("🧹 清理测试视频文件...")
        
        for video_path in self.test_videos:
            try:
                if os.path.exists(video_path):
                    os.unlink(video_path)
                    print(f"   🗑️ 删除: {video_path}")
            except Exception as e:
                print(f"   ⚠️ 删除失败 {video_path}: {str(e)}")
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def test_local_video_concat(self, video_paths: list) -> bool:
        """测试本地视频拼接"""
        print(f"\\n🔗 测试本地视频拼接...")
        print(f"   视频文件:")
        for i, path in enumerate(video_paths):
            print(f"     {i+1}. {path}")
        
        try:
            # 构建请求数据
            request_data = {
                "composition_type": "concat",
                "videos": [{"video_url": path} for path in video_paths],
                "output_format": "mp4",
                "output_resolution": "640x480"
            }
            
            print("   📤 发送合成请求...")
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return False
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                print(f"   📄 错误信息: {response.text}")
                return False
            
            data = response.json()
            task_id = data.get('task_id')
            
            if not task_id:
                print("   ❌ 未获取到任务ID")
                return False
            
            print(f"   ✅ 任务已启动: {task_id[:8]}...")
            
            # 监控任务进度
            return self.monitor_composition_task(task_id)
            
        except Exception as e:
            print(f"   💥 测试异常: {str(e)}")
            return False
    
    def test_mixed_video_concat(self, local_paths: list, online_url: str) -> bool:
        """测试混合视频拼接（本地+在线）"""
        print(f"\\n🌐 测试混合视频拼接（本地+在线）...")
        
        try:
            # 构建请求数据（本地视频 + 在线视频）
            videos = []
            
            # 添加本地视频
            for path in local_paths:
                videos.append({"video_url": path})
                print(f"   📁 本地视频: {path}")
            
            # 添加在线视频
            videos.append({"video_url": online_url})
            print(f"   🌐 在线视频: {online_url}")
            
            request_data = {
                "composition_type": "concat",
                "videos": videos,
                "output_format": "mp4"
            }
            
            print("   📤 发送混合合成请求...")
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return False
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                print(f"   📄 错误信息: {response.text}")
                return False
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ 混合合成任务已启动: {task_id[:8]}...")
            
            # 监控任务进度
            return self.monitor_composition_task(task_id)
            
        except Exception as e:
            print(f"   💥 测试异常: {str(e)}")
            return False
    
    def test_file_protocol_support(self, video_paths: list) -> bool:
        """测试file://协议支持"""
        print(f"\\n📁 测试file://协议支持...")
        
        try:
            # 使用file://协议
            file_urls = [f"file://{os.path.abspath(path)}" for path in video_paths]
            
            for url in file_urls:
                print(f"   📎 file:// URL: {url}")
            
            request_data = {
                "composition_type": "concat",
                "videos": [{"video_url": url} for url in file_urls],
                "output_format": "mp4"
            }
            
            print("   📤 发送file://协议请求...")
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print("   ⚠️ 系统资源不足")
                return False
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                print(f"   📄 错误信息: {response.text}")
                return False
            
            data = response.json()
            task_id = data.get('task_id')
            
            print(f"   ✅ file://协议任务已启动: {task_id[:8]}...")
            
            # 监控任务进度
            return self.monitor_composition_task(task_id)
            
        except Exception as e:
            print(f"   💥 测试异常: {str(e)}")
            return False
    
    def monitor_composition_task(self, task_id: str, max_wait_time: int = 300) -> bool:
        """监控合成任务进度"""
        print(f"   ⏳ 监控任务进度: {task_id[:8]}...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{self.api_base_url}/composition_status/{task_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    progress = data.get('progress', 0)
                    message = data.get('message', '')
                    
                    print(f"      📊 进度: {progress}% - {message}")
                    
                    if status == 'completed':
                        print(f"   ✅ 任务完成: {task_id[:8]}")
                        
                        # 获取详细结果
                        result_response = self.session.get(f"{self.api_base_url}/composition_result/{task_id}")
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            composition_result = result_data.get('result', {})
                            
                            output_file = composition_result.get('output_file', '')
                            file_size = composition_result.get('output_file_size', 0)
                            duration = composition_result.get('output_duration', 0)
                            processing_time = composition_result.get('processing_time', 0)
                            
                            print(f"      📊 输出文件: {output_file}")
                            print(f"      📊 文件大小: {file_size / 1024 / 1024:.1f}MB")
                            print(f"      📊 视频时长: {duration:.1f}秒")
                            print(f"      📊 处理时间: {processing_time:.1f}秒")
                        
                        return True
                        
                    elif status == 'failed':
                        error = data.get('error', 'Unknown error')
                        print(f"   ❌ 任务失败: {error}")
                        return False
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                print(f"      ⚠️ 查询状态失败: {str(e)}")
                time.sleep(5)
        
        print(f"   ⏰ 任务监控超时: {task_id[:8]}")
        return False
    
    def run_all_tests(self):
        """运行所有本地视频合成测试"""
        print("🚀 开始本地视频合成功能测试")
        print("=" * 60)
        
        # 检查API可用性
        if not self.check_api_availability():
            print("❌ API服务不可用，请确保服务正在运行")
            return False
        
        print("✅ API服务可用")
        
        # 创建测试视频
        test_videos = self.create_test_videos()
        
        if len(test_videos) < 2:
            print("❌ 测试视频创建失败，无法进行测试")
            return False
        
        print(f"✅ 成功创建 {len(test_videos)} 个测试视频")
        
        try:
            # 测试结果
            test_results = []
            
            # 测试1: 纯本地视频拼接
            print("\\n" + "=" * 60)
            result1 = self.test_local_video_concat(test_videos)
            test_results.append(("本地视频拼接", result1))
            
            # 测试2: file://协议支持
            print("\\n" + "=" * 60)
            result2 = self.test_file_protocol_support(test_videos)
            test_results.append(("file://协议支持", result2))
            
            # 测试3: 混合视频拼接（如果有在线视频URL）
            online_test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            print("\\n" + "=" * 60)
            result3 = self.test_mixed_video_concat([test_videos[0]], online_test_url)
            test_results.append(("混合视频拼接", result3))
            
            # 输出测试结果摘要
            print("\\n" + "=" * 60)
            print("📊 测试结果摘要:")
            
            passed_tests = [name for name, result in test_results if result]
            failed_tests = [name for name, result in test_results if not result]
            
            print(f"   总测试数: {len(test_results)}")
            print(f"   通过: {len(passed_tests)}")
            print(f"   失败: {len(failed_tests)}")
            
            if passed_tests:
                print(f"\\n✅ 通过的测试:")
                for test_name in passed_tests:
                    print(f"   - {test_name}")
            
            if failed_tests:
                print(f"\\n❌ 失败的测试:")
                for test_name in failed_tests:
                    print(f"   - {test_name}")
            
            success_rate = len(passed_tests) / len(test_results) * 100
            print(f"\\n📈 成功率: {success_rate:.1f}%")
            
            if len(passed_tests) == len(test_results):
                print("\\n🎉 所有本地视频合成测试通过！")
                print("✅ 本地视频支持功能正常工作")
                return True
            else:
                print("\\n⚠️ 部分测试失败，请检查实现")
                return False
                
        finally:
            # 清理测试文件
            self.cleanup_test_videos()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='本地视频合成功能测试')
    parser.add_argument('--api-url', default='http://localhost:7878', help='API服务地址')
    
    args = parser.parse_args()
    
    tester = LocalVideoCompositionTester(args.api_url)
    success = tester.run_all_tests()
    
    import sys
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()