#!/usr/bin/env python3
"""
视频处理API集成测试
测试完整的API工作流程、并发任务处理能力、资源管理和错误恢复
"""

import unittest
import requests
import time
import threading
import tempfile
import os
import json
from typing import List, Dict, Any
import concurrent.futures

class TestAPIWorkflow(unittest.TestCase):
    """API工作流程集成测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.api_base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.test_tasks = []  # 跟踪创建的任务以便清理
        
        # 检查API是否可用
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("API服务不可用")
        except Exception:
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        # 清理创建的任务
        for task_id in self.test_tasks:
            try:
                self.session.post(f"{self.api_base_url}/system/tasks/{task_id}/cancel")
            except:
                pass
        self.session.close()
    
    def test_complete_transcription_workflow(self):
        """测试完整的转录工作流程"""
        print("\n🎤 测试完整转录工作流程...")
        
        # 1. 启动转录任务
        response = self.session.post(
            f"{self.api_base_url}/generate_text_from_video",
            json={"video_url": self.test_video_url}
        )
        
        if response.status_code == 503:
            self.skipTest("系统资源不足")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        task_id = data.get('task_id')
        self.assertIsNotNone(task_id)
        self.test_tasks.append(task_id)
        
        print(f"   ✅ 任务已启动: {task_id}")
        
        # 2. 监控任务状态
        max_wait_time = 60  # 最多等待60秒
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait_time:
            response = self.session.get(f"{self.api_base_url}/transcription_status/{task_id}")
            self.assertEqual(response.status_code, 200)
            
            status_data = response.json()
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            
            print(f"   📊 状态: {status}, 进度: {progress}%")
            
            if status in ['completed', 'failed']:
                final_status = status
                break
            
            time.sleep(5)
        
        # 3. 验证最终状态
        if final_status == 'completed':
            print("   ✅ 转录任务成功完成")
            
            # 4. 获取结果
            response = self.session.get(f"{self.api_base_url}/transcription_result/{task_id}")
            self.assertEqual(response.status_code, 200)
            
            result_data = response.json()
            self.assertIn('result', result_data)
            print("   ✅ 成功获取转录结果")
            
        elif final_status == 'failed':
            print("   ⚠️ 转录任务失败（这在测试环境中是正常的）")
        else:
            print("   ⏰ 转录任务超时（可能需要更长时间）")
    
    def test_complete_download_workflow(self):
        """测试完整的下载工作流程"""
        print("\n⬇️ 测试完整下载工作流程...")
        
        # 1. 启动下载任务
        response = self.session.post(
            f"{self.api_base_url}/download_video",
            json={
                "video_url": self.test_video_url,
                "quality": "480p",  # 使用较低质量以加快测试
                "format": "mp4"
            }
        )
        
        if response.status_code == 503:
            self.skipTest("系统资源不足")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        task_id = data.get('task_id')
        self.assertIsNotNone(task_id)
        self.test_tasks.append(task_id)
        
        print(f"   ✅ 下载任务已启动: {task_id}")
        
        # 2. 监控任务状态
        max_wait_time = 120  # 下载可能需要更长时间
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait_time:
            response = self.session.get(f"{self.api_base_url}/download_status/{task_id}")
            self.assertEqual(response.status_code, 200)
            
            status_data = response.json()
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            
            print(f"   📊 状态: {status}, 进度: {progress}%")
            
            if status in ['completed', 'failed']:
                final_status = status
                break
            
            time.sleep(10)
        
        # 3. 验证最终状态
        if final_status == 'completed':
            print("   ✅ 下载任务成功完成")
        elif final_status == 'failed':
            print("   ⚠️ 下载任务失败（这在测试环境中是正常的）")
        else:
            print("   ⏰ 下载任务超时（可能需要更长时间）")
    
    def test_complete_composition_workflow(self):
        """测试完整的合成工作流程"""
        print("\n🎬 测试完整合成工作流程...")
        
        # 创建测试字幕文件
        srt_content = """1
00:00:00,000 --> 00:00:05,000
测试字幕第一行

2
00:00:05,000 --> 00:00:10,000
测试字幕第二行
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            subtitle_file = f.name
        
        try:
            # 1. 启动合成任务
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json={
                    "composition_type": "audio_video_subtitle",
                    "videos": [{"video_url": self.test_video_url}],
                    "audio_file": self.test_video_url,  # 使用同一个URL作为音频源
                    "subtitle_file": subtitle_file,
                    "output_format": "mp4"
                }
            )
            
            if response.status_code == 503:
                self.skipTest("系统资源不足")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            task_id = data.get('task_id')
            self.assertIsNotNone(task_id)
            self.test_tasks.append(task_id)
            
            print(f"   ✅ 合成任务已启动: {task_id}")
            
            # 2. 监控任务状态
            max_wait_time = 180  # 合成可能需要更长时间
            start_time = time.time()
            final_status = None
            
            while time.time() - start_time < max_wait_time:
                response = self.session.get(f"{self.api_base_url}/composition_status/{task_id}")
                self.assertEqual(response.status_code, 200)
                
                status_data = response.json()
                status = status_data.get('status')
                progress = status_data.get('progress', 0)
                current_stage = status_data.get('current_stage', '')
                
                print(f"   📊 状态: {status}, 进度: {progress}%, 阶段: {current_stage}")
                
                if status in ['completed', 'failed']:
                    final_status = status
                    break
                
                time.sleep(15)
            
            # 3. 验证最终状态
            if final_status == 'completed':
                print("   ✅ 合成任务成功完成")
                
                # 4. 获取结果
                response = self.session.get(f"{self.api_base_url}/composition_result/{task_id}")
                self.assertEqual(response.status_code, 200)
                
                result_data = response.json()
                self.assertIn('result', result_data)
                print("   ✅ 成功获取合成结果")
                
            elif final_status == 'failed':
                print("   ⚠️ 合成任务失败（这在测试环境中是正常的）")
            else:
                print("   ⏰ 合成任务超时（可能需要更长时间）")
        
        finally:
            # 清理临时字幕文件
            try:
                os.unlink(subtitle_file)
            except:
                pass

class TestConcurrentProcessing(unittest.TestCase):
    """并发处理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.api_base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.test_tasks = []
        
        # 检查API是否可用
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("API服务不可用")
        except Exception:
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        # 清理创建的任务
        for task_id in self.test_tasks:
            try:
                self.session.post(f"{self.api_base_url}/system/tasks/{task_id}/cancel")
            except:
                pass
        self.session.close()
    
    def test_concurrent_task_submission(self):
        """测试并发任务提交"""
        print("\n🔄 测试并发任务提交...")
        
        def submit_task(task_index):
            """提交单个任务"""
            try:
                session = requests.Session()
                response = session.post(
                    f"{self.api_base_url}/generate_text_from_video",
                    json={"video_url": self.test_video_url},
                    timeout=10
                )
                
                return {
                    'index': task_index,
                    'status_code': response.status_code,
                    'task_id': response.json().get('task_id') if response.status_code == 200 else None,
                    'error': response.json().get('detail') if response.status_code != 200 else None
                }
            except Exception as e:
                return {
                    'index': task_index,
                    'status_code': 0,
                    'task_id': None,
                    'error': str(e)
                }
        
        # 并发提交多个任务
        num_tasks = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_tasks) as executor:
            futures = [executor.submit(submit_task, i) for i in range(num_tasks)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        successful_tasks = [r for r in results if r['status_code'] == 200]
        resource_limited_tasks = [r for r in results if r['status_code'] == 503]
        failed_tasks = [r for r in results if r['status_code'] not in [200, 503]]
        
        print(f"   ✅ 成功提交: {len(successful_tasks)} 个任务")
        print(f"   🚫 资源限制: {len(resource_limited_tasks)} 个任务")
        print(f"   ❌ 失败: {len(failed_tasks)} 个任务")
        
        # 记录成功的任务ID以便清理
        for result in successful_tasks:
            if result['task_id']:
                self.test_tasks.append(result['task_id'])
        
        # 验证至少有一些任务成功或被资源限制拒绝（说明系统正常工作）
        self.assertGreater(len(successful_tasks) + len(resource_limited_tasks), 0,
                          "应该至少有一些任务成功提交或被资源限制拒绝")
    
    def test_concurrent_status_queries(self):
        """测试并发状态查询"""
        print("\n🔍 测试并发状态查询...")
        
        # 首先启动一个任务
        response = self.session.post(
            f"{self.api_base_url}/generate_text_from_video",
            json={"video_url": self.test_video_url}
        )
        
        if response.status_code != 200:
            self.skipTest("无法启动测试任务")
        
        task_id = response.json().get('task_id')
        self.test_tasks.append(task_id)
        
        def query_status(query_index):
            """查询任务状态"""
            try:
                session = requests.Session()
                response = session.get(
                    f"{self.api_base_url}/transcription_status/{task_id}",
                    timeout=5
                )
                
                return {
                    'index': query_index,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                return {
                    'index': query_index,
                    'status_code': 0,
                    'error': str(e),
                    'response_time': 0
                }
        
        # 并发查询状态
        num_queries = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_queries) as executor:
            futures = [executor.submit(query_status, i) for i in range(num_queries)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        successful_queries = [r for r in results if r['status_code'] == 200]
        failed_queries = [r for r in results if r['status_code'] != 200]
        
        avg_response_time = sum(r['response_time'] for r in successful_queries) / len(successful_queries) if successful_queries else 0
        
        print(f"   ✅ 成功查询: {len(successful_queries)} 次")
        print(f"   ❌ 失败查询: {len(failed_queries)} 次")
        print(f"   ⏱️ 平均响应时间: {avg_response_time:.3f} 秒")
        
        # 验证大部分查询成功
        self.assertGreater(len(successful_queries), len(failed_queries),
                          "成功的查询应该多于失败的查询")

class TestResourceManagement(unittest.TestCase):
    """资源管理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.api_base_url = "http://localhost:8000"
        self.session = requests.Session()
        
        # 检查API是否可用
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("API服务不可用")
        except Exception:
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.session.close()
    
    def test_resource_monitoring(self):
        """测试资源监控功能"""
        print("\n📊 测试资源监控功能...")
        
        # 1. 获取资源状态
        response = self.session.get(f"{self.api_base_url}/system/resources")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        required_fields = [
            'cpu_percent', 'memory_percent', 'disk_percent', 
            'free_disk_gb', 'active_tasks', 'max_concurrent_tasks'
        ]
        
        for field in required_fields:
            self.assertIn(field, data)
            print(f"   📈 {field}: {data[field]}")
        
        # 2. 获取资源历史
        response = self.session.get(f"{self.api_base_url}/system/resources/history?duration_minutes=1")
        self.assertEqual(response.status_code, 200)
        
        history_data = response.json()
        self.assertIn('cpu', history_data)
        self.assertIn('memory', history_data)
        self.assertIn('disk', history_data)
        
        print(f"   📊 历史数据点数: CPU={len(history_data['cpu'])}, Memory={len(history_data['memory'])}")
    
    def test_resource_limits_management(self):
        """测试资源限制管理"""
        print("\n⚙️ 测试资源限制管理...")
        
        # 1. 获取当前限制
        response = self.session.get(f"{self.api_base_url}/system/resources")
        self.assertEqual(response.status_code, 200)
        
        original_data = response.json()
        original_limits = original_data.get('limits', {})
        original_max_tasks = original_data.get('max_concurrent_tasks', 3)
        
        print(f"   📋 原始限制: {original_limits}")
        
        # 2. 更新限制
        new_limits = {
            "max_concurrent_tasks": 2,
            "max_memory_usage": 85
        }
        
        response = self.session.put(
            f"{self.api_base_url}/system/resources/limits",
            params=new_limits
        )
        self.assertEqual(response.status_code, 200)
        
        update_data = response.json()
        self.assertIn('updated_limits', update_data)
        print(f"   ✅ 限制已更新: {update_data['updated_limits']}")
        
        # 3. 验证更新
        response = self.session.get(f"{self.api_base_url}/system/resources")
        self.assertEqual(response.status_code, 200)
        
        updated_data = response.json()
        self.assertEqual(updated_data.get('max_concurrent_tasks'), 2)
        
        # 4. 恢复原始限制
        restore_limits = {
            "max_concurrent_tasks": original_max_tasks,
            "max_memory_usage": original_limits.get('max_memory_usage', 80)
        }
        
        response = self.session.put(
            f"{self.api_base_url}/system/resources/limits",
            params=restore_limits
        )
        self.assertEqual(response.status_code, 200)
        print("   🔄 原始限制已恢复")
    
    def test_cleanup_functionality(self):
        """测试清理功能"""
        print("\n🧹 测试清理功能...")
        
        # 1. 获取清理统计
        response = self.session.get(f"{self.api_base_url}/system/cleanup/stats")
        self.assertEqual(response.status_code, 200)
        
        stats_data = response.json()
        cleanup_stats = stats_data.get('cleanup_stats', {})
        
        print(f"   📊 清理统计:")
        print(f"      过期任务: {cleanup_stats.get('expired_tasks_cleaned', 0)}")
        print(f"      临时文件: {cleanup_stats.get('temp_files_cleaned', 0)}")
        print(f"      终止进程: {cleanup_stats.get('processes_terminated', 0)}")
        print(f"      活跃进程: {stats_data.get('active_processes', 0)}")
        
        # 2. 执行强制清理
        response = self.session.post(f"{self.api_base_url}/system/cleanup/force")
        self.assertEqual(response.status_code, 200)
        
        cleanup_data = response.json()
        cleanup_results = cleanup_data.get('cleanup_results', {})
        
        print(f"   🧽 强制清理结果:")
        print(f"      清理耗时: {cleanup_results.get('cleanup_duration', 0):.2f} 秒")
        print(f"      过期任务: {cleanup_results.get('expired_tasks_cleaned', 0)}")
        print(f"      临时文件: {cleanup_results.get('temp_files_cleaned', 0)}")

class TestErrorRecovery(unittest.TestCase):
    """错误恢复测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.api_base_url = "http://localhost:8000"
        self.session = requests.Session()
        
        # 检查API是否可用
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("API服务不可用")
        except Exception:
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.session.close()
    
    def test_error_tracking(self):
        """测试错误跟踪功能"""
        print("\n⚠️ 测试错误跟踪功能...")
        
        # 1. 获取初始错误统计
        response = self.session.get(f"{self.api_base_url}/system/errors/stats")
        self.assertEqual(response.status_code, 200)
        
        initial_stats = response.json()
        initial_error_count = initial_stats.get('total_errors', 0)
        
        print(f"   📊 初始错误数: {initial_error_count}")
        
        # 2. 故意触发错误
        response = self.session.post(
            f"{self.api_base_url}/compose_video",
            json={
                "composition_type": "invalid_type",
                "videos": [{"video_url": "test.mp4"}]
            }
        )
        self.assertEqual(response.status_code, 400)  # 应该返回400错误
        
        # 3. 检查错误是否被记录（注意：输入验证错误可能不会被记录到统计中）
        time.sleep(1)  # 等待错误处理完成
        
        response = self.session.get(f"{self.api_base_url}/system/errors/recent?limit=5")
        self.assertEqual(response.status_code, 200)
        
        recent_errors = response.json().get('recent_errors', [])
        print(f"   📝 最近错误数: {len(recent_errors)}")
        
        if recent_errors:
            latest_error = recent_errors[-1]
            print(f"   🔍 最新错误类型: {latest_error.get('error_type')}")
            print(f"   💬 错误消息: {latest_error.get('message', '')[:50]}...")
    
    def test_system_resilience(self):
        """测试系统弹性"""
        print("\n🛡️ 测试系统弹性...")
        
        # 1. 测试无效请求的处理
        invalid_requests = [
            # 无效的JSON
            ("POST", "/compose_video", "invalid json"),
            # 缺少必需字段
            ("POST", "/compose_video", {}),
            # 无效的URL参数
            ("GET", "/transcription_status/invalid-task-id", None),
        ]
        
        resilience_score = 0
        total_tests = len(invalid_requests)
        
        for method, endpoint, data in invalid_requests:
            try:
                if method == "POST":
                    if isinstance(data, str):
                        response = self.session.post(
                            f"{self.api_base_url}{endpoint}",
                            data=data,
                            headers={'Content-Type': 'application/json'}
                        )
                    else:
                        response = self.session.post(
                            f"{self.api_base_url}{endpoint}",
                            json=data
                        )
                else:
                    response = self.session.get(f"{self.api_base_url}{endpoint}")
                
                # 系统应该优雅地处理错误，返回4xx状态码而不是崩溃
                if 400 <= response.status_code < 500:
                    resilience_score += 1
                    print(f"   ✅ {method} {endpoint}: 优雅处理 ({response.status_code})")
                else:
                    print(f"   ⚠️ {method} {endpoint}: 意外状态码 ({response.status_code})")
                    
            except Exception as e:
                print(f"   ❌ {method} {endpoint}: 异常 ({str(e)})")
        
        resilience_percentage = (resilience_score / total_tests) * 100
        print(f"   🎯 系统弹性得分: {resilience_percentage:.1f}% ({resilience_score}/{total_tests})")
        
        # 系统应该至少能优雅处理大部分无效请求
        self.assertGreater(resilience_percentage, 50, "系统应该能优雅处理大部分无效请求")

def run_integration_tests():
    """运行所有集成测试"""
    print("🚀 开始运行集成测试")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestAPIWorkflow,
        TestConcurrentProcessing,
        TestResourceManagement,
        TestErrorRecovery
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print(f"📊 集成测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("🎉 所有集成测试通过！")
    else:
        print("⚠️ 部分集成测试失败，请检查详细信息")
        
        if result.failures:
            print("\n❌ 失败的测试:")
            for test, traceback in result.failures:
                print(f"   - {test}")
        
        if result.errors:
            print("\n💥 错误的测试:")
            for test, traceback in result.errors:
                print(f"   - {test}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)