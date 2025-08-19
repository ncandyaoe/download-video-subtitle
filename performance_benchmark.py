#!/usr/bin/env python3
"""
视频处理API性能基准测试脚本
测试系统在不同负载下的性能表现
"""

import requests
import time
import json
import sys
import argparse
import threading
import statistics
from typing import Dict, Any, List, Tuple
from datetime import datetime
import concurrent.futures

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 30
        
        # 测试用视频URL
        self.test_videos = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=9bZkp7q19f0",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ]
        
        self.results = {
            'response_times': [],
            'throughput_tests': [],
            'concurrent_tests': [],
            'resource_usage': []
        }
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def measure_response_time(self, endpoint: str, method: str = 'GET', data: dict = None, iterations: int = 10) -> Dict[str, Any]:
        """测量API端点响应时间"""
        print(f"⏱️ 测量 {endpoint} 响应时间 ({iterations}次)...")
        
        response_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                if method.upper() == 'GET':
                    response = self.session.get(f"{self.api_base_url}{endpoint}")
                else:
                    response = self.session.post(f"{self.api_base_url}{endpoint}", json=data)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code in [200, 503]:  # 503表示资源限制，也是正常响应
                    response_times.append(response_time)
                
            except Exception as e:
                print(f"   ⚠️ 第{i+1}次请求失败: {str(e)}")
            
            time.sleep(0.1)  # 短暂间隔
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            median_time = statistics.median(response_times)
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'iterations': len(response_times),
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'median_response_time': median_time,
                'success_rate': len(response_times) / iterations
            }
            
            print(f"   📊 平均响应时间: {avg_time:.3f}s")
            print(f"   📊 最小/最大: {min_time:.3f}s / {max_time:.3f}s")
            print(f"   📊 成功率: {result['success_rate']:.2%}")
            
            self.results['response_times'].append(result)
            return result
        else:
            print("   ❌ 所有请求都失败")
            return None
    
    def test_concurrent_requests(self, endpoint: str, method: str, data: dict, concurrent_users: int, duration: int) -> Dict[str, Any]:
        """测试并发请求性能"""
        print(f"🔄 测试并发请求: {concurrent_users}用户, {duration}秒")
        
        results = []
        start_time = time.time()
        
        def worker():
            """工作线程"""
            session = requests.Session()
            session.timeout = 10
            
            while time.time() - start_time < duration:
                request_start = time.time()
                
                try:
                    if method.upper() == 'GET':
                        response = session.get(f"{self.api_base_url}{endpoint}")
                    else:
                        response = session.post(f"{self.api_base_url}{endpoint}", json=data)
                    
                    request_end = time.time()
                    
                    results.append({
                        'timestamp': request_start,
                        'response_time': request_end - request_start,
                        'status_code': response.status_code,
                        'success': response.status_code in [200, 503]
                    })
                    
                except Exception as e:
                    results.append({
                        'timestamp': request_start,
                        'response_time': 0,
                        'status_code': 0,
                        'success': False,
                        'error': str(e)
                    })
                
                time.sleep(0.1)  # 短暂间隔
        
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
        successful_requests = len([r for r in results if r['success']])
        failed_requests = total_requests - successful_requests
        
        if successful_requests > 0:
            successful_results = [r for r in results if r['success']]
            avg_response_time = statistics.mean([r['response_time'] for r in successful_results])
            throughput = successful_requests / duration
        else:
            avg_response_time = 0
            throughput = 0
        
        result = {
            'endpoint': endpoint,
            'concurrent_users': concurrent_users,
            'duration': duration,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'avg_response_time': avg_response_time,
            'throughput': throughput
        }
        
        print(f"   📊 总请求数: {total_requests}")
        print(f"   📊 成功请求: {successful_requests}")
        print(f"   📊 成功率: {result['success_rate']:.2%}")
        print(f"   📊 平均响应时间: {avg_response_time:.3f}s")
        print(f"   📊 吞吐量: {throughput:.2f} 请求/秒")
        
        self.results['concurrent_tests'].append(result)
        return result
    
    def monitor_resource_usage(self, duration: int) -> Dict[str, Any]:
        """监控资源使用情况"""
        print(f"💻 监控资源使用 ({duration}秒)...")
        
        resource_data = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                response = self.session.get(f"{self.api_base_url}/system/resources")
                
                if response.status_code == 200:
                    data = response.json()
                    resource_data.append({
                        'timestamp': time.time(),
                        'cpu_percent': data.get('cpu_percent', 0),
                        'memory_percent': data.get('memory_percent', 0),
                        'disk_percent': data.get('disk_percent', 0),
                        'active_tasks': data.get('active_tasks', 0),
                        'can_accept_tasks': data.get('can_accept_tasks', True)
                    })
                
            except Exception as e:
                print(f"   ⚠️ 资源监控失败: {str(e)}")
            
            time.sleep(2)  # 每2秒采样一次
        
        if resource_data:
            cpu_values = [r['cpu_percent'] for r in resource_data]
            memory_values = [r['memory_percent'] for r in resource_data]
            disk_values = [r['disk_percent'] for r in resource_data]
            task_values = [r['active_tasks'] for r in resource_data]
            
            result = {
                'duration': duration,
                'samples': len(resource_data),
                'cpu_stats': {
                    'avg': statistics.mean(cpu_values),
                    'min': min(cpu_values),
                    'max': max(cpu_values),
                    'median': statistics.median(cpu_values)
                },
                'memory_stats': {
                    'avg': statistics.mean(memory_values),
                    'min': min(memory_values),
                    'max': max(memory_values),
                    'median': statistics.median(memory_values)
                },
                'disk_stats': {
                    'avg': statistics.mean(disk_values),
                    'min': min(disk_values),
                    'max': max(disk_values),
                    'median': statistics.median(disk_values)
                },
                'task_stats': {
                    'avg': statistics.mean(task_values),
                    'min': min(task_values),
                    'max': max(task_values),
                    'median': statistics.median(task_values)
                }
            }
            
            print(f"   📊 CPU使用率: 平均{result['cpu_stats']['avg']:.1f}%, 最大{result['cpu_stats']['max']:.1f}%")
            print(f"   📊 内存使用率: 平均{result['memory_stats']['avg']:.1f}%, 最大{result['memory_stats']['max']:.1f}%")
            print(f"   📊 活跃任务数: 平均{result['task_stats']['avg']:.1f}, 最大{result['task_stats']['max']}")
            
            self.results['resource_usage'].append(result)
            return result
        else:
            print("   ❌ 未收集到资源数据")
            return None
    
    def test_task_submission_performance(self) -> Dict[str, Any]:
        """测试任务提交性能"""
        print("🚀 测试任务提交性能...")
        
        task_types = [
            {
                'name': '转录任务',
                'endpoint': '/generate_text_from_video',
                'data': {'video_url': self.test_videos[0]}
            },
            {
                'name': '下载任务',
                'endpoint': '/download_video',
                'data': {
                    'video_url': self.test_videos[0],
                    'quality': '480p',
                    'format': 'mp4'
                }
            },
            {
                'name': '关键帧任务',
                'endpoint': '/extract_keyframes',
                'data': {
                    'video_url': self.test_videos[0],
                    'method': 'count',
                    'count': 3
                }
            }
        ]
        
        submission_results = []
        
        for task_type in task_types:
            print(f"\n   📤 测试{task_type['name']}提交...")
            
            submission_times = []
            successful_submissions = 0
            
            for i in range(5):  # 每种任务类型提交5次
                start_time = time.time()
                
                try:
                    response = self.session.post(
                        f"{self.api_base_url}{task_type['endpoint']}",
                        json=task_type['data']
                    )
                    
                    end_time = time.time()
                    submission_time = end_time - start_time
                    
                    if response.status_code in [200, 503]:
                        submission_times.append(submission_time)
                        if response.status_code == 200:
                            successful_submissions += 1
                    
                except Exception as e:
                    print(f"      ⚠️ 第{i+1}次提交失败: {str(e)}")
                
                time.sleep(1)  # 间隔1秒
            
            if submission_times:
                avg_time = statistics.mean(submission_times)
                result = {
                    'task_type': task_type['name'],
                    'avg_submission_time': avg_time,
                    'successful_submissions': successful_submissions,
                    'total_attempts': 5,
                    'success_rate': successful_submissions / 5
                }
                
                print(f"      📊 平均提交时间: {avg_time:.3f}s")
                print(f"      📊 成功提交: {successful_submissions}/5")
                
                submission_results.append(result)
        
        return {'task_submission_results': submission_results}
    
    def run_comprehensive_benchmark(self):
        """运行综合性能基准测试"""
        print("🚀 开始综合性能基准测试")
        print("=" * 80)
        
        # 检查API可用性
        if not self.check_api_availability():
            print("❌ API服务不可用，请确保服务正在运行")
            return False
        
        print("✅ API服务可用，开始基准测试...")
        
        # 1. 响应时间测试
        print("\n📊 第1阶段: 响应时间基准测试")
        print("-" * 40)
        
        endpoints_to_test = [
            ('/health', 'GET', None),
            ('/system/resources', 'GET', None),
            ('/system/performance/stats', 'GET', None),
            ('/generate_text_from_video', 'POST', {'video_url': self.test_videos[0]}),
        ]
        
        for endpoint, method, data in endpoints_to_test:
            self.measure_response_time(endpoint, method, data, 5)
            time.sleep(1)
        
        # 2. 并发性能测试
        print("\n🔄 第2阶段: 并发性能测试")
        print("-" * 40)
        
        # 测试健康检查端点的并发性能
        self.test_concurrent_requests('/health', 'GET', None, 5, 30)
        time.sleep(5)
        
        # 测试任务提交的并发性能
        self.test_concurrent_requests(
            '/generate_text_from_video', 
            'POST', 
            {'video_url': self.test_videos[0]}, 
            3, 
            20
        )
        time.sleep(5)
        
        # 3. 资源使用监控
        print("\n💻 第3阶段: 资源使用监控")
        print("-" * 40)
        
        # 在负载下监控资源使用
        def create_load():
            """创建系统负载"""
            for _ in range(3):
                try:
                    self.session.post(
                        f"{self.api_base_url}/generate_text_from_video",
                        json={'video_url': self.test_videos[0]}
                    )
                except:
                    pass
                time.sleep(2)
        
        # 启动负载生成线程
        load_thread = threading.Thread(target=create_load)
        load_thread.start()
        
        # 监控资源使用
        self.monitor_resource_usage(30)
        
        load_thread.join()
        
        # 4. 任务提交性能测试
        print("\n🚀 第4阶段: 任务提交性能测试")
        print("-" * 40)
        
        submission_results = self.test_task_submission_performance()
        self.results.update(submission_results)
        
        # 生成测试报告
        self.generate_benchmark_report()
        
        return True
    
    def generate_benchmark_report(self):
        """生成基准测试报告"""
        print("\n" + "=" * 80)
        print("📊 性能基准测试报告")
        print("=" * 80)
        
        print(f"🕐 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 API地址: {self.api_base_url}")
        
        # 响应时间报告
        if self.results['response_times']:
            print("\n📊 响应时间基准:")
            for result in self.results['response_times']:
                print(f"   {result['endpoint']} ({result['method']}):")
                print(f"      平均: {result['avg_response_time']:.3f}s")
                print(f"      中位数: {result['median_response_time']:.3f}s")
                print(f"      范围: {result['min_response_time']:.3f}s - {result['max_response_time']:.3f}s")
                print(f"      成功率: {result['success_rate']:.2%}")
        
        # 并发性能报告
        if self.results['concurrent_tests']:
            print("\n🔄 并发性能基准:")
            for result in self.results['concurrent_tests']:
                print(f"   {result['endpoint']} ({result['concurrent_users']}并发用户):")
                print(f"      吞吐量: {result['throughput']:.2f} 请求/秒")
                print(f"      平均响应时间: {result['avg_response_time']:.3f}s")
                print(f"      成功率: {result['success_rate']:.2%}")
        
        # 资源使用报告
        if self.results['resource_usage']:
            print("\n💻 资源使用基准:")
            for result in self.results['resource_usage']:
                print(f"   监控时长: {result['duration']}秒 ({result['samples']}个样本)")
                print(f"   CPU使用率: 平均{result['cpu_stats']['avg']:.1f}%, 峰值{result['cpu_stats']['max']:.1f}%")
                print(f"   内存使用率: 平均{result['memory_stats']['avg']:.1f}%, 峰值{result['memory_stats']['max']:.1f}%")
                print(f"   活跃任务数: 平均{result['task_stats']['avg']:.1f}, 峰值{result['task_stats']['max']}")
        
        # 任务提交性能报告
        if 'task_submission_results' in self.results:
            print("\n🚀 任务提交性能:")
            for result in self.results['task_submission_results']:
                print(f"   {result['task_type']}:")
                print(f"      平均提交时间: {result['avg_submission_time']:.3f}s")
                print(f"      成功率: {result['success_rate']:.2%}")
        
        # 性能评估
        print("\n🎯 性能评估:")
        
        # 响应时间评估
        if self.results['response_times']:
            avg_response_times = [r['avg_response_time'] for r in self.results['response_times']]
            overall_avg = statistics.mean(avg_response_times)
            
            if overall_avg < 0.1:
                print("   ✅ 响应时间: 优秀 (< 100ms)")
            elif overall_avg < 0.5:
                print("   ✅ 响应时间: 良好 (< 500ms)")
            elif overall_avg < 1.0:
                print("   ⚠️ 响应时间: 一般 (< 1s)")
            else:
                print("   ❌ 响应时间: 需要优化 (> 1s)")
        
        # 并发性能评估
        if self.results['concurrent_tests']:
            throughputs = [r['throughput'] for r in self.results['concurrent_tests']]
            max_throughput = max(throughputs) if throughputs else 0
            
            if max_throughput > 10:
                print("   ✅ 并发性能: 优秀 (> 10 req/s)")
            elif max_throughput > 5:
                print("   ✅ 并发性能: 良好 (> 5 req/s)")
            elif max_throughput > 1:
                print("   ⚠️ 并发性能: 一般 (> 1 req/s)")
            else:
                print("   ❌ 并发性能: 需要优化 (< 1 req/s)")
        
        # 资源使用评估
        if self.results['resource_usage']:
            resource_result = self.results['resource_usage'][0]
            max_cpu = resource_result['cpu_stats']['max']
            max_memory = resource_result['memory_stats']['max']
            
            if max_cpu < 70 and max_memory < 80:
                print("   ✅ 资源使用: 优秀 (CPU < 70%, 内存 < 80%)")
            elif max_cpu < 85 and max_memory < 90:
                print("   ✅ 资源使用: 良好 (CPU < 85%, 内存 < 90%)")
            else:
                print("   ⚠️ 资源使用: 需要关注 (CPU或内存使用率较高)")
        
        print("\n💡 优化建议:")
        print("   - 定期运行性能基准测试监控系统性能")
        print("   - 根据负载情况调整并发限制和资源配置")
        print("   - 监控关键性能指标并设置告警阈值")
        print("   - 考虑启用缓存和硬件加速优化")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='视频处理API性能基准测试')
    parser.add_argument('--api-url', default='http://localhost:7878', help='API服务地址')
    parser.add_argument('--test', choices=['response', 'concurrent', 'resource', 'submission', 'all'],
                       default='all', help='指定要运行的测试类型')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.api_url)
    
    if args.test == 'all':
        success = benchmark.run_comprehensive_benchmark()
    elif args.test == 'response':
        # 只运行响应时间测试
        endpoints = [
            ('/health', 'GET', None),
            ('/system/resources', 'GET', None),
        ]
        for endpoint, method, data in endpoints:
            benchmark.measure_response_time(endpoint, method, data, 10)
        success = True
    elif args.test == 'concurrent':
        # 只运行并发测试
        benchmark.test_concurrent_requests('/health', 'GET', None, 5, 30)
        success = True
    elif args.test == 'resource':
        # 只运行资源监控
        benchmark.monitor_resource_usage(60)
        success = True
    elif args.test == 'submission':
        # 只运行任务提交测试
        benchmark.test_task_submission_performance()
        success = True
    else:
        print(f"未知的测试类型: {args.test}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()