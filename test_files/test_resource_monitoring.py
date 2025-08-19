#!/usr/bin/env python3
"""
资源监控功能测试脚本
测试系统资源监控、限制检查和任务管理功能
"""

import requests
import time
import json
from typing import Dict, Any

class ResourceMonitoringTester:
    """资源监控测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查端点"""
        print("🔍 测试健康检查端点...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 健康检查成功")
            print(f"   状态: {data.get('status')}")
            print(f"   总活跃任务: {data.get('total_active_tasks', 0)}")
            print(f"   资源状态: {data.get('resource_status', {}).get('message', 'N/A')}")
            print(f"   CPU: {data.get('resource_status', {}).get('cpu_percent', 0):.1f}%")
            print(f"   内存: {data.get('resource_status', {}).get('memory_percent', 0):.1f}%")
            print(f"   磁盘: {data.get('resource_status', {}).get('disk_percent', 0):.1f}%")
            
            return data
            
        except Exception as e:
            print(f"❌ 健康检查失败: {str(e)}")
            return {}
    
    def test_resource_stats(self) -> Dict[str, Any]:
        """测试资源统计端点"""
        print("\n🔍 测试资源统计端点...")
        try:
            response = self.session.get(f"{self.base_url}/system/resources")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 资源统计获取成功")
            print(f"   CPU使用率: {data.get('cpu_percent', 0):.1f}%")
            print(f"   内存使用率: {data.get('memory_percent', 0):.1f}%")
            print(f"   内存使用: {data.get('memory_used_gb', 0):.2f}GB / {data.get('memory_total_gb', 0):.2f}GB")
            print(f"   磁盘使用率: {data.get('disk_percent', 0):.1f}%")
            print(f"   磁盘剩余: {data.get('free_disk_gb', 0):.2f}GB")
            print(f"   活跃任务: {data.get('active_tasks', 0)} / {data.get('max_concurrent_tasks', 0)}")
            
            limits = data.get('limits', {})
            print(f"   资源限制:")
            print(f"     最大内存使用率: {limits.get('max_memory_usage', 0)}%")
            print(f"     最大磁盘使用率: {limits.get('max_disk_usage', 0)}%")
            print(f"     最大CPU使用率: {limits.get('max_cpu_usage', 0)}%")
            print(f"     最小剩余磁盘: {limits.get('min_free_disk_gb', 0)}GB")
            
            return data
            
        except Exception as e:
            print(f"❌ 资源统计获取失败: {str(e)}")
            return {}
    
    def test_resource_history(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """测试资源历史数据端点"""
        print(f"\n🔍 测试资源历史数据端点 (最近{duration_minutes}分钟)...")
        try:
            response = self.session.get(
                f"{self.base_url}/system/resources/history",
                params={"duration_minutes": duration_minutes}
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 资源历史数据获取成功")
            for resource_type, history in data.items():
                if history:
                    latest_value = history[-1][1] if history else 0
                    print(f"   {resource_type}: {len(history)}个数据点, 最新值: {latest_value}")
                else:
                    print(f"   {resource_type}: 无历史数据")
            
            return data
            
        except Exception as e:
            print(f"❌ 资源历史数据获取失败: {str(e)}")
            return {}
    
    def test_update_resource_limits(self) -> bool:
        """测试更新资源限制"""
        print("\n🔍 测试更新资源限制...")
        try:
            # 先获取当前限制
            current_response = self.session.get(f"{self.base_url}/system/resources")
            current_response.raise_for_status()
            current_data = current_response.json()
            current_limits = current_data.get('limits', {})
            
            # 更新限制（稍微调整一些值）
            new_limits = {
                "max_concurrent_tasks": 4,
                "max_memory_usage": 85,
                "max_cpu_usage": 85
            }
            
            response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params=new_limits
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 资源限制更新成功")
            print(f"   消息: {data.get('message')}")
            updated_limits = data.get('updated_limits', {})
            for key, value in updated_limits.items():
                print(f"   {key}: {value}")
            
            # 恢复原始限制
            restore_limits = {
                "max_concurrent_tasks": current_limits.get('max_concurrent_tasks', 3),
                "max_memory_usage": current_limits.get('max_memory_usage', 80),
                "max_cpu_usage": current_limits.get('max_cpu_usage', 90)
            }
            
            restore_response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params=restore_limits
            )
            restore_response.raise_for_status()
            print(f"✅ 资源限制已恢复到原始值")
            
            return True
            
        except Exception as e:
            print(f"❌ 更新资源限制失败: {str(e)}")
            return False
    
    def test_force_cleanup(self) -> bool:
        """测试强制资源清理"""
        print("\n🔍 测试强制资源清理...")
        try:
            response = self.session.post(f"{self.base_url}/system/resources/cleanup")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 强制资源清理成功")
            print(f"   消息: {data.get('message')}")
            print(f"   时间戳: {data.get('timestamp')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 强制资源清理失败: {str(e)}")
            return False
    
    def test_task_management(self) -> bool:
        """测试任务管理功能"""
        print("\n🔍 测试任务管理功能...")
        try:
            # 获取所有任务
            response = self.session.get(f"{self.base_url}/system/tasks")
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 任务列表获取成功")
            summary = data.get('summary', {})
            print(f"   总任务数: {summary.get('total_tasks', 0)}")
            print(f"   活跃任务数: {summary.get('active_tasks', 0)}")
            print(f"   合成任务: {summary.get('composition_tasks', 0)}")
            print(f"   转录任务: {summary.get('transcription_tasks', 0)}")
            print(f"   下载任务: {summary.get('download_tasks', 0)}")
            print(f"   关键帧任务: {summary.get('keyframe_tasks', 0)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 任务管理测试失败: {str(e)}")
            return False
    
    def test_resource_limits_enforcement(self) -> bool:
        """测试资源限制强制执行"""
        print("\n🔍 测试资源限制强制执行...")
        try:
            # 先设置很低的并发任务限制
            low_limit = {"max_concurrent_tasks": 1}
            response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params=low_limit
            )
            response.raise_for_status()
            print(f"✅ 设置低并发限制: 1个任务")
            
            # 尝试启动多个任务（这里使用一个简单的测试URL）
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 经典测试URL
            
            task_ids = []
            for i in range(3):
                try:
                    task_response = self.session.post(
                        f"{self.base_url}/generate_text_from_video",
                        json={"video_url": test_url}
                    )
                    
                    if task_response.status_code == 503:
                        print(f"✅ 第{i+1}个任务被正确拒绝 (资源限制)")
                        break
                    elif task_response.status_code == 200:
                        task_data = task_response.json()
                        task_ids.append(task_data.get('task_id'))
                        print(f"✅ 第{i+1}个任务已启动: {task_data.get('task_id')}")
                    else:
                        print(f"⚠️ 第{i+1}个任务返回状态码: {task_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ 第{i+1}个任务启动异常: {str(e)}")
                
                time.sleep(1)  # 短暂等待
            
            # 取消启动的任务
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
            restore_limit = {"max_concurrent_tasks": 3}
            restore_response = self.session.put(
                f"{self.base_url}/system/resources/limits",
                params=restore_limit
            )
            restore_response.raise_for_status()
            print(f"✅ 并发限制已恢复: 3个任务")
            
            return True
            
        except Exception as e:
            print(f"❌ 资源限制强制执行测试失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始资源监控功能测试")
        print("=" * 50)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("资源统计", self.test_resource_stats),
            ("资源历史", self.test_resource_history),
            ("更新资源限制", self.test_update_resource_limits),
            ("强制资源清理", self.test_force_cleanup),
            ("任务管理", self.test_task_management),
            ("资源限制强制执行", self.test_resource_limits_enforcement)
        ]
        
        passed = 0
        total = len(tests)
        
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
            
            print("-" * 30)
        
        print(f"\n📊 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！资源监控功能正常工作。")
        else:
            print("⚠️ 部分测试失败，请检查系统状态。")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="资源监控功能测试")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="API服务器URL (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--test",
        choices=["health", "stats", "history", "limits", "cleanup", "tasks", "enforcement", "all"],
        default="all",
        help="要运行的测试类型"
    )
    
    args = parser.parse_args()
    
    tester = ResourceMonitoringTester(args.url)
    
    if args.test == "all":
        tester.run_all_tests()
    elif args.test == "health":
        tester.test_health_check()
    elif args.test == "stats":
        tester.test_resource_stats()
    elif args.test == "history":
        tester.test_resource_history()
    elif args.test == "limits":
        tester.test_update_resource_limits()
    elif args.test == "cleanup":
        tester.test_force_cleanup()
    elif args.test == "tasks":
        tester.test_task_management()
    elif args.test == "enforcement":
        tester.test_resource_limits_enforcement()

if __name__ == "__main__":
    main()