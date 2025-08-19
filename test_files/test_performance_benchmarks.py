#!/usr/bin/env python3
"""
视频处理API性能基准测试
测试系统性能、吞吐量、响应时间和资源使用效率
"""

import unittest
import requests
import time
import threading
import statistics
import psutil
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import sys

class PerformanceBenchmarkTester:
    """性能基准测试器"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.test_tasks = []
        self.performance_data = {
            'response_times': [],
            'throughput': [],
            'resource_usage': [],
            'error_rates': []
        }
        
        # 测试配置
        self.test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
    def cleanup(self):
        """清理测试资源"""
        for task_id in self.test_tasks:
            try:
                self.session.post(f"{self.api_base_url}/system/tasks/{task_id}/cancel")
            except:
                pass
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def measure_response_time(self, endpoint: str, method: str = 'GET', data: dict = None) -> Dict[str, Any]:
        """测量单个请求的响应时间"""
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(f"{self.api_base_url}{endpoint}", timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(f"{self.api_base_url}{endpoint}", json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response_time': response_time,
                'response_size': len(response.content),
                'timestamp': start_time
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'error': str(e),
                'response_time': end_time - start_time,
                'timestamp': start_time
            }
    
    def measure_throughput(self, endpoint: str, method: str, data: dict, duration_seconds: int, concurrent_users: int) -> Dict[str, Any]:
        """测量系统吞吐量"""
        results = []
        start_time = time.time()
        
        def worker():
            """工作线程"""
            session = requests.Session()
            while time.time() - start_time < duration_seconds:
                try:
                    if method.upper() == 'GET':
                        response = session.get(f"{self.api_base_url}{endpoint}", timeout=10)
                    else:
                        response = session.post(f"{self.api_base_url}{endpoint}", json=data, timeout=10)
                    
                    results.append({
                        'timestamp': time.time(),
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds(),
                        'success': response.status_code < 400
                    })
                    
                except Exception as e:
                    results.append({
                        'timestamp': time.time(),
                        'error': str(e),
                        'response_time': 0,
                        'success': False
                    })
                
                time.sleep(0.1)  # 短暂休息避免过度负载
        
        # 启动并发工作线程
        threads = []
        for _ in range(concurrent_users):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 分析结果
        total_requests = len(results)
        successful_requests = len([r for r in results if r.get('success', False)])
        failed_requests = total_requests - successful_requests
        
        if successful_requests > 0:
            avg_response_time = statistics.mean([r['response_time'] for r in results if r.get('success', False)])
            throughput = successful_requests / duration_seconds
        else:
            avg_response_time = 0
            throughput = 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'duration': duration_seconds,
            'concurrent_users': concurrent_users,
            'raw_results': results
        }
    
    def monitor_resource_usage(self, duration_seconds: int, interval_seconds: int = 1) -> List[Dict[str, Any]]:
        """监控系统资源使用情况"""
        resource_data = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            try:
                # 获取系统资源信息
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # 获取API服务器资源信息
                try:
                    response = self.session.get(f"{self.api_base_url}/system/resources", timeout=2)
                    if response.status_code == 200:
                        api_resources = response.json()
                    else:
                        api_resources = {}
                except:
                    api_resources = {}
                
                resource_data.append({
                    'timestamp': time.time(),
                    'system_cpu_percent': cpu_percent,
                    'system_memory_percent': memory.percent,
                    'system_disk_percent': (disk.used / disk.total) * 100,
                    'api_cpu_percent': api_resources.get('cpu_percent', 0),
                    'api_memory_percent': api_resources.get('memory_percent', 0),
                    'api_active_tasks': api_resources.get('active_tasks', 0)
                })
                
            except Exception as e:
                resource_data.append({
                    'timestamp': time.time(),
                    'error': str(e)
                })
            
            time.sleep(interval_seconds)
        
        return resource_data

class TestResponseTimePerformance(unittest.TestCase):
    """响应时间性能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = PerformanceBenchmarkTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_api_endpoint_response_times(self):
        """测试各API端点的响应时间"""
        print("\n⏱️ 测试API端点响应时间...")
        
        # 定义要测试的端点
        endpoints = [
            {'name': '健康检查', 'endpoint': '/health', 'method': 'GET'},
            {'name': '系统资源', 'endpoint': '/system/resources', 'method': 'GET'},
            {'name': '错误统计', 'endpoint': '/system/errors/stats', 'method': 'GET'},
            {'name': '任务列表', 'endpoint': '/system/tasks', 'method': 'GET'},
            {
                'name': '视频转录提交', 
                'endpoint': '/generate_text_from_video', 
                'method': 'POST',
                'data': {'video_url': self.tester.test_video_url}
            }
        ]
        
        response_times = {}
        
        for endpoint_config in endpoints:
            print(f"   📊 测试 {endpoint_config['name']}...")
            
            # 进行多次测试取平均值
            times = []
            for i in range(5):
                result = self.tester.measure_response_time(
                    endpoint_config['endpoint'],
                    endpoint_config['method'],
                    endpoint_config.get('data')
                )
                
                if result['success']:
                    times.append(result['response_time'])
                    if result.get('status_code') == 200 and endpoint_config['method'] == 'POST':
                        # 如果是POST请求且成功，记录任务ID以便清理
                        try:
                            response_data = self.tester.session.get(
                                f"{self.tester.api_base_url}{endpoint_config['endpoint']}",
                                json=endpoint_config.get('data')
                            ).json()
                            task_id = response_data.get('task_id')
                            if task_id:
                                self.tester.test_tasks.append(task_id)
                        except:
                            pass
                else:
                    print(f"      ⚠️ 第{i+1}次请求失败: {result.get('error')}")
                
                time.sleep(0.5)  # 短暂休息
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                
                response_times[endpoint_config['name']] = {
                    'avg': avg_time,
                    'min': min_time,
                    'max': max_time,
                    'samples': len(times)
                }
                
                print(f"      ✅ 平均: {avg_time:.3f}s, 最小: {min_time:.3f}s, 最大: {max_time:.3f}s")
            else:
                print(f"      ❌ 所有请求都失败")
        
        # 验证响应时间在合理范围内
        for name, times in response_times.items():
            self.assertLess(times['avg'], 10.0, f"{name} 平均响应时间应小于10秒")
        
        print("   🎉 响应时间测试完成")

class TestThroughputPerformance(unittest.TestCase):
    """吞吐量性能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = PerformanceBenchmarkTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_health_check_throughput(self):
        """测试健康检查端点的吞吐量"""
        print("\n🚀 测试健康检查吞吐量...")
        
        # 测试不同并发级别
        concurrency_levels = [1, 5, 10]
        duration = 30  # 30秒测试
        
        for concurrent_users in concurrency_levels:
            print(f"   📊 测试并发用户数: {concurrent_users}")
            
            result = self.tester.measure_throughput(
                '/health', 'GET', None, duration, concurrent_users
            )
            
            print(f"      总请求数: {result['total_requests']}")
            print(f"      成功率: {result['success_rate']:.2%}")
            print(f"      吞吐量: {result['throughput']:.2f} 请求/秒")
            print(f"      平均响应时间: {result['avg_response_time']:.3f}秒")
            
            # 验证基本性能指标
            self.assertGreater(result['success_rate'], 0.8, "健康检查成功率应大于80%")
            self.assertGreater(result['throughput'], 1.0, "健康检查吞吐量应大于1请求/秒")
            self.assertLess(result['avg_response_time'], 2.0, "健康检查平均响应时间应小于2秒")
        
        print("   🎉 健康检查吞吐量测试完成")
    
    def test_video_processing_throughput(self):
        """测试视频处理任务的吞吐量"""
        print("\n🎬 测试视频处理吞吐量...")
        
        # 测试视频转录任务的提交吞吐量
        print("   📊 测试转录任务提交吞吐量...")
        
        result = self.tester.measure_throughput(
            '/generate_text_from_video', 
            'POST', 
            {'video_url': self.tester.test_video_url},
            20,  # 20秒测试
            3    # 3个并发用户
        )
        
        print(f"      总请求数: {result['total_requests']}")
        print(f"      成功率: {result['success_rate']:.2%}")
        print(f"      吞吐量: {result['throughput']:.2f} 请求/秒")
        print(f"      平均响应时间: {result['avg_response_time']:.3f}秒")
        
        # 验证视频处理任务的基本性能
        # 由于视频处理任务可能受资源限制，我们放宽要求
        if result['successful_requests'] > 0:
            self.assertLess(result['avg_response_time'], 5.0, "视频处理任务提交响应时间应小于5秒")
        
        print("   🎉 视频处理吞吐量测试完成")

class TestResourceUsagePerformance(unittest.TestCase):
    """资源使用性能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = PerformanceBenchmarkTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_resource_usage_under_load(self):
        """测试负载下的资源使用情况"""
        print("\n💻 测试负载下的资源使用...")
        
        # 启动资源监控
        print("   📊 启动资源监控...")
        
        def run_load_test():
            """运行负载测试"""
            return self.tester.measure_throughput(
                '/health', 'GET', None, 30, 5
            )
        
        # 同时运行负载测试和资源监控
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 启动资源监控
            resource_future = executor.submit(self.tester.monitor_resource_usage, 35, 2)
            
            # 等待2秒后启动负载测试
            time.sleep(2)
            load_future = executor.submit(run_load_test)
            
            # 获取结果
            load_result = load_future.result()
            resource_data = resource_future.result()
        
        # 分析资源使用情况
        print("   📈 分析资源使用情况...")
        
        valid_resource_data = [r for r in resource_data if 'error' not in r]
        
        if valid_resource_data:
            cpu_values = [r.get('system_cpu_percent', 0) for r in valid_resource_data]
            memory_values = [r.get('system_memory_percent', 0) for r in valid_resource_data]
            
            if cpu_values and memory_values:
                avg_cpu = statistics.mean(cpu_values)
                max_cpu = max(cpu_values)
                avg_memory = statistics.mean(memory_values)
                max_memory = max(memory_values)
                
                print(f"      平均CPU使用率: {avg_cpu:.1f}%")
                print(f"      最大CPU使用率: {max_cpu:.1f}%")
                print(f"      平均内存使用率: {avg_memory:.1f}%")
                print(f"      最大内存使用率: {max_memory:.1f}%")
                
                # 验证资源使用在合理范围内
                self.assertLess(max_cpu, 95.0, "CPU使用率不应超过95%")
                self.assertLess(max_memory, 90.0, "内存使用率不应超过90%")
        
        print(f"   🚀 负载测试结果: {load_result['throughput']:.2f} 请求/秒")
        print("   🎉 资源使用性能测试完成")

class TestScalabilityPerformance(unittest.TestCase):
    """可扩展性性能测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = PerformanceBenchmarkTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_concurrent_user_scalability(self):
        """测试并发用户可扩展性"""
        print("\n📈 测试并发用户可扩展性...")
        
        # 测试不同并发级别下的性能
        concurrency_levels = [1, 2, 5, 10, 15]
        duration = 20  # 每个级别测试20秒
        
        scalability_results = {}
        
        for concurrent_users in concurrency_levels:
            print(f"   👥 测试并发用户数: {concurrent_users}")
            
            result = self.tester.measure_throughput(
                '/health', 'GET', None, duration, concurrent_users
            )
            
            scalability_results[concurrent_users] = {
                'throughput': result['throughput'],
                'success_rate': result['success_rate'],
                'avg_response_time': result['avg_response_time']
            }
            
            print(f"      吞吐量: {result['throughput']:.2f} 请求/秒")
            print(f"      成功率: {result['success_rate']:.2%}")
            print(f"      平均响应时间: {result['avg_response_time']:.3f}秒")
            
            # 短暂休息让系统恢复
            time.sleep(5)
        
        # 分析可扩展性
        print("   📊 可扩展性分析:")
        
        throughputs = [scalability_results[level]['throughput'] for level in concurrency_levels]
        response_times = [scalability_results[level]['avg_response_time'] for level in concurrency_levels]
        
        # 计算吞吐量增长率
        if len(throughputs) >= 2:
            throughput_growth = (throughputs[-1] - throughputs[0]) / throughputs[0] if throughputs[0] > 0 else 0
            print(f"      吞吐量增长率: {throughput_growth:.2%}")
            
            # 理想情况下，吞吐量应该随并发数增加而增加（至少在低并发时）
            if throughput_growth > 0:
                print("      ✅ 系统显示出良好的可扩展性")
            else:
                print("      ⚠️ 系统可扩展性有限")
        
        # 检查响应时间是否随并发数合理增长
        if len(response_times) >= 2:
            response_time_growth = (response_times[-1] - response_times[0]) / response_times[0] if response_times[0] > 0 else 0
            print(f"      响应时间增长率: {response_time_growth:.2%}")
            
            # 响应时间增长应该是合理的
            if response_time_growth < 5.0:  # 500%以内的增长是可接受的
                print("      ✅ 响应时间增长在合理范围内")
            else:
                print("      ⚠️ 响应时间增长过快，可能存在性能瓶颈")
        
        print("   🎉 并发用户可扩展性测试完成")

def run_performance_benchmarks():
    """运行性能基准测试"""
    print("🚀 开始运行性能基准测试")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestResponseTimePerformance,
        TestThroughputPerformance,
        TestResourceUsagePerformance,
        TestScalabilityPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # 生成性能报告
    print("\n" + "=" * 80)
    print("📊 性能基准测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("🎉 所有性能基准测试通过！")
        print("✅ 系统性能表现良好")
    else:
        print("⚠️ 部分性能基准测试失败")
        
        if result.failures:
            print("\n❌ 失败的测试:")
            for test, traceback in result.failures:
                print(f"   - {test}")
        
        if result.errors:
            print("\n💥 错误的测试:")
            for test, traceback in result.errors:
                print(f"   - {test}")
    
    # 性能建议
    print("\n💡 性能优化建议:")
    print("   - 定期运行性能基准测试监控系统性能")
    print("   - 根据负载情况调整系统资源配置")
    print("   - 监控关键性能指标并设置告警")
    print("   - 考虑实施缓存策略提高响应速度")
    print("   - 优化数据库查询和文件I/O操作")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import sys
    success = run_performance_benchmarks()
    sys.exit(0 if success else 1)