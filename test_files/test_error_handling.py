#!/usr/bin/env python3
"""
错误处理和资源清理功能测试脚本
测试统一错误处理机制、任务超时、资源清理等功能
"""

import requests
import time
import json
import os
import tempfile
from typing import Dict, Any

class ErrorHandlingTester:
    """错误处理测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_files = []  # 跟踪创建的测试文件
    
    def cleanup_test_files(self):
        """清理测试文件"""
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"清理测试文件: {file_path}")
            except Exception as e:
                print(f"清理测试文件失败 {file_path}: {str(e)}")
        self.test_files.clear()
    
    def create_test_srt_file(self, content: str = None) -> str:
        """创建测试SRT字幕文件"""
        if content is None:
            content = """1
00:00:00,000 --> 00:00:05,000
这是测试字幕第一行

2
00:00:05,000 --> 00:00:10,000
这是测试字幕第二行
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = f.name
        
        self.test_files.append(temp_file)
        return temp_file
    
    def test_error_stats_endpoint(self) -> bool:
        """测试错误统计端点"""
        print("🔍 测试错误统计端点...")
        try:
            response = self.session.get(f"{self.base_url}/system/errors/stats")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 错误统计获取成功")
            print(f"   总错误数: {data.get('total_errors', 0)}")
            print(f"   错误类型数: {len(data.get('error_types', {}))}")
            print(f"   最近错误数: {data.get('recent_errors_count', 0)}")
            
            most_common = data.get('most_common_errors', [])
            if most_common:
                print(f"   最常见错误:")
                for error_type, count in most_common[:3]:
                    print(f"     {error_type}: {count}次")
            
            return True
            
        except Exception as e:
            print(f"❌ 错误统计测试失败: {str(e)}")
            return False
    
    def test_recent_errors_endpoint(self) -> bool:
        """测试最近错误端点"""
        print("\n🔍 测试最近错误端点...")
        try:
            response = self.session.get(f"{self.base_url}/system/errors/recent?limit=5")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 最近错误获取成功")
            recent_errors = data.get('recent_errors', [])
            print(f"   返回错误数: {len(recent_errors)}")
            
            for i, error in enumerate(recent_errors[:3], 1):
                print(f"   错误{i}: {error.get('error_type')} - {error.get('message', '')[:50]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ 最近错误测试失败: {str(e)}")
            return False
    
    def test_cleanup_stats_endpoint(self) -> bool:
        """测试清理统计端点"""
        print("\n🔍 测试清理统计端点...")
        try:
            response = self.session.get(f"{self.base_url}/system/cleanup/stats")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 清理统计获取成功")
            cleanup_stats = data.get('cleanup_stats', {})
            print(f"   已清理过期任务: {cleanup_stats.get('expired_tasks_cleaned', 0)}")
            print(f"   已清理临时文件: {cleanup_stats.get('temp_files_cleaned', 0)}")
            print(f"   已终止进程: {cleanup_stats.get('processes_terminated', 0)}")
            print(f"   活跃进程数: {data.get('active_processes', 0)}")
            print(f"   任务锁数: {data.get('task_locks', 0)}")
            print(f"   清理服务运行: {data.get('cleanup_running', False)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理统计测试失败: {str(e)}")
            return False
    
    def test_force_comprehensive_cleanup(self) -> bool:
        """测试强制全面清理"""
        print("\n🔍 测试强制全面清理...")
        try:
            response = self.session.post(f"{self.base_url}/system/cleanup/force")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 强制全面清理成功")
            print(f"   消息: {data.get('message')}")
            
            cleanup_results = data.get('cleanup_results', {})
            print(f"   清理结果:")
            print(f"     过期任务: {cleanup_results.get('expired_tasks_cleaned', 0)}")
            print(f"     临时文件: {cleanup_results.get('temp_files_cleaned', 0)}")
            print(f"     终止进程: {cleanup_results.get('processes_terminated', 0)}")
            print(f"     清理耗时: {cleanup_results.get('cleanup_duration', 0)}秒")
            
            return True
            
        except Exception as e:
            print(f"❌ 强制全面清理测试失败: {str(e)}")
            return False
    
    def test_invalid_input_error_handling(self) -> bool:
        """测试输入验证错误处理"""
        print("\n🔍 测试输入验证错误处理...")
        try:
            # 测试无效的合成类型
            invalid_request = {
                "composition_type": "invalid_type",
                "videos": [{"video_url": "test.mp4"}],
                "output_format": "mp4"
            }
            
            response = self.session.post(
                f"{self.base_url}/compose_video",
                json=invalid_request
            )
            
            # 应该返回400错误
            if response.status_code == 400:
                print(f"✅ 输入验证错误正确处理 (状态码: {response.status_code})")
                error_data = response.json()
                print(f"   错误详情: {error_data.get('detail', 'N/A')}")
                return True
            else:
                print(f"❌ 期望400状态码，实际收到: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 输入验证错误处理测试失败: {str(e)}")
            return False
    
    def test_resource_limit_error_handling(self) -> bool:
        """测试资源限制错误处理"""
        print("\n🔍 测试资源限制错误处理...")
        try:
            # 先设置很低的并发限制
            limit_response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params={"max_concurrent_tasks": 1}
            )
            limit_response.raise_for_status()
            print(f"✅ 设置并发限制为1")
            
            # 尝试启动多个任务
            test_request = {
                "composition_type": "concat",
                "videos": [
                    {"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                    {"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
                ],
                "output_format": "mp4"
            }
            
            task_ids = []
            resource_limit_hit = False
            
            for i in range(3):
                try:
                    response = self.session.post(
                        f"{self.base_url}/compose_video",
                        json=test_request
                    )
                    
                    if response.status_code == 503:
                        print(f"✅ 第{i+1}个任务被正确拒绝 (资源限制)")
                        resource_limit_hit = True
                        break
                    elif response.status_code == 200:
                        task_data = response.json()
                        task_ids.append(task_data.get('task_id'))
                        print(f"✅ 第{i+1}个任务已启动: {task_data.get('task_id')}")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"⚠️ 第{i+1}个任务启动异常: {str(e)}")
            
            # 清理启动的任务
            for task_id in task_ids:
                try:
                    cancel_response = self.session.post(
                        f"{self.base_url}/system/tasks/{task_id}/cancel"
                    )
                    if cancel_response.status_code == 200:
                        print(f"✅ 任务已取消: {task_id}")
                except Exception as e:
                    print(f"⚠️ 取消任务失败 {task_id}: {str(e)}")
            
            # 恢复原始限制
            restore_response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params={"max_concurrent_tasks": 3}
            )
            restore_response.raise_for_status()
            print(f"✅ 并发限制已恢复为3")
            
            return resource_limit_hit
            
        except Exception as e:
            print(f"❌ 资源限制错误处理测试失败: {str(e)}")
            return False
    
    def test_task_cleanup_functionality(self) -> bool:
        """测试任务清理功能"""
        print("\n🔍 测试任务清理功能...")
        try:
            # 创建一个测试字幕文件
            srt_file = self.create_test_srt_file()
            
            # 启动一个简单的合成任务
            test_request = {
                "composition_type": "audio_video_subtitle",
                "videos": [{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}],
                "audio_file": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "subtitle_file": srt_file,
                "output_format": "mp4"
            }
            
            response = self.session.post(
                f"{self.base_url}/compose_video",
                json=test_request
            )
            
            if response.status_code == 200:
                task_data = response.json()
                task_id = task_data.get('task_id')
                print(f"✅ 测试任务已启动: {task_id}")
                
                # 等待一小段时间
                time.sleep(2)
                
                # 测试强制任务清理
                cleanup_response = self.session.post(
                    f"{self.base_url}/system/tasks/{task_id}/force-cleanup"
                )
                
                if cleanup_response.status_code == 200:
                    cleanup_data = cleanup_response.json()
                    print(f"✅ 任务资源清理成功")
                    print(f"   消息: {cleanup_data.get('message')}")
                    return True
                else:
                    print(f"❌ 任务清理失败，状态码: {cleanup_response.status_code}")
                    return False
            
            elif response.status_code == 503:
                print(f"✅ 任务被资源限制拒绝，这是正常的")
                return True
            else:
                print(f"❌ 启动测试任务失败，状态码: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 任务清理功能测试失败: {str(e)}")
            return False
    
    def test_error_recovery_mechanisms(self) -> bool:
        """测试错误恢复机制"""
        print("\n🔍 测试错误恢复机制...")
        try:
            # 测试无效URL的处理
            invalid_request = {
                "composition_type": "concat",
                "videos": [
                    {"video_url": "invalid://not-a-real-url"},
                    {"video_url": "https://invalid-domain-that-does-not-exist.com/video.mp4"}
                ],
                "output_format": "mp4"
            }
            
            response = self.session.post(
                f"{self.base_url}/compose_video",
                json=invalid_request
            )
            
            if response.status_code in [400, 503]:
                print(f"✅ 无效URL请求被正确拒绝 (状态码: {response.status_code})")
                error_data = response.json()
                print(f"   错误详情: {error_data.get('detail', 'N/A')}")
                
                # 检查错误统计是否更新
                time.sleep(1)
                stats_response = self.session.get(f"{self.base_url}/system/errors/stats")
                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    print(f"   错误统计已更新: 总错误数 {stats_data.get('total_errors', 0)}")
                
                return True
            else:
                print(f"❌ 期望400或503状态码，实际收到: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 错误恢复机制测试失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始错误处理和资源清理功能测试")
        print("=" * 60)
        
        tests = [
            ("错误统计端点", self.test_error_stats_endpoint),
            ("最近错误端点", self.test_recent_errors_endpoint),
            ("清理统计端点", self.test_cleanup_stats_endpoint),
            ("强制全面清理", self.test_force_comprehensive_cleanup),
            ("输入验证错误处理", self.test_invalid_input_error_handling),
            ("资源限制错误处理", self.test_resource_limit_error_handling),
            ("任务清理功能", self.test_task_cleanup_functionality),
            ("错误恢复机制", self.test_error_recovery_mechanisms)
        ]
        
        passed = 0
        total = len(tests)
        
        try:
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    if result:
                        passed += 1
                        print(f"✅ {test_name} - 通过")
                    else:
                        print(f"❌ {test_name} - 失败")
                except Exception as e:
                    print(f"❌ {test_name} - 异常: {str(e)}")
                
                print("-" * 40)
        
        finally:
            # 清理测试文件
            self.cleanup_test_files()
        
        print(f"\n📊 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！错误处理和资源清理功能正常工作。")
        else:
            print("⚠️ 部分测试失败，请检查系统状态。")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="错误处理和资源清理功能测试")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="API服务器URL (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--test",
        choices=["stats", "recent", "cleanup", "input", "resource", "task", "recovery", "all"],
        default="all",
        help="要运行的测试类型"
    )
    
    args = parser.parse_args()
    
    tester = ErrorHandlingTester(args.url)
    
    if args.test == "all":
        tester.run_all_tests()
    elif args.test == "stats":
        tester.test_error_stats_endpoint()
    elif args.test == "recent":
        tester.test_recent_errors_endpoint()
    elif args.test == "cleanup":
        tester.test_cleanup_stats_endpoint()
    elif args.test == "input":
        tester.test_invalid_input_error_handling()
    elif args.test == "resource":
        tester.test_resource_limit_error_handling()
    elif args.test == "task":
        tester.test_task_cleanup_functionality()
    elif args.test == "recovery":
        tester.test_error_recovery_mechanisms()

if __name__ == "__main__":
    main()