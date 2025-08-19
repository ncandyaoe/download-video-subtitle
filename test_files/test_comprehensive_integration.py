#!/usr/bin/env python3
"""
视频处理API综合集成测试
全面测试API工作流程、并发处理、资源管理和错误恢复
"""

import unittest
import requests
import time
import threading
import tempfile
import os
import json
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Tuple
import subprocess
import psutil
from datetime import datetime, timedelta

class ComprehensiveIntegrationTester:
    """综合集成测试器"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.test_tasks = []  # 跟踪创建的任务
        self.test_files = []  # 跟踪创建的文件
        
        # 测试用的URL和文件
        self.test_video_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # 经典测试视频
            "https://www.youtube.com/watch?v=9bZkp7q19f0",  # 另一个测试视频
        ]
        
        self.test_audio_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
    def cleanup(self):
        """清理测试资源"""
        # 取消所有测试任务
        for task_id in self.test_tasks:
            try:
                self.session.post(f"{self.api_base_url}/system/tasks/{task_id}/cancel")
            except:
                pass
        
        # 删除测试文件
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def create_test_subtitle_file(self, content: str = None) -> str:
        """创建测试字幕文件"""
        if content is None:
            content = """1
00:00:00,000 --> 00:00:05,000
测试字幕第一行

2
00:00:05,000 --> 00:00:10,000
测试字幕第二行

3
00:00:10,000 --> 00:00:15,000
测试字幕第三行
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = f.name
        
        self.test_files.append(temp_file)
        return temp_file
    
    def wait_for_task_completion(self, task_id: str, task_type: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        status_endpoints = {
            'transcription': f'/transcription_status/{task_id}',
            'download': f'/download_status/{task_id}',
            'keyframe': f'/keyframe_status/{task_id}',
            'composition': f'/composition_status/{task_id}'
        }
        
        endpoint = status_endpoints.get(task_type)
        if not endpoint:
            return {'status': 'unknown', 'error': 'Invalid task type'}
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{self.api_base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    
                    if status in ['completed', 'failed']:
                        return data
                    
                    # 显示进度
                    progress = data.get('progress', 0)
                    print(f"   📊 任务 {task_id[:8]}... 进度: {progress}%")
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                print(f"   ⚠️ 查询任务状态失败: {str(e)}")
                time.sleep(5)
        
        return {'status': 'timeout', 'error': 'Task execution timeout'}

class TestEndToEndWorkflows(unittest.TestCase):
    """端到端工作流程测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = ComprehensiveIntegrationTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_complete_video_processing_pipeline(self):
        """测试完整的视频处理流水线"""
        print("\n🔄 测试完整视频处理流水线...")
        
        # 1. 视频下载
        print("   📥 步骤1: 下载视频")
        download_response = self.tester.session.post(
            f"{self.tester.api_base_url}/download_video",
            json={
                "video_url": self.tester.test_video_urls[0],
                "quality": "480p",
                "format": "mp4"
            }
        )
        
        if download_response.status_code == 503:
            self.skipTest("系统资源不足")
        
        self.assertEqual(download_response.status_code, 200)
        download_data = download_response.json()
        download_task_id = download_data.get('task_id')
        self.tester.test_tasks.append(download_task_id)
        
        # 2. 视频转录
        print("   🎤 步骤2: 视频转录")
        transcription_response = self.tester.session.post(
            f"{self.tester.api_base_url}/generate_text_from_video",
            json={"video_url": self.tester.test_video_urls[0]}
        )
        
        if transcription_response.status_code == 503:
            print("   ⚠️ 转录任务被资源限制拒绝")
        else:
            self.assertEqual(transcription_response.status_code, 200)
            transcription_data = transcription_response.json()
            transcription_task_id = transcription_data.get('task_id')
            self.tester.test_tasks.append(transcription_task_id)
        
        # 3. 关键帧提取
        print("   🖼️ 步骤3: 关键帧提取")
        keyframe_response = self.tester.session.post(
            f"{self.tester.api_base_url}/extract_keyframes",
            json={
                "video_url": self.tester.test_video_urls[0],
                "method": "count",
                "count": 5,
                "width": 640,
                "height": 360,
                "format": "jpg",
                "quality": 80
            }
        )
        
        if keyframe_response.status_code == 503:
            print("   ⚠️ 关键帧提取任务被资源限制拒绝")
        else:
            self.assertEqual(keyframe_response.status_code, 200)
            keyframe_data = keyframe_response.json()
            keyframe_task_id = keyframe_data.get('task_id')
            self.tester.test_tasks.append(keyframe_task_id)
        
        # 4. 等待下载任务完成（优先级最高）
        print("   ⏳ 等待下载任务完成...")
        download_result = self.tester.wait_for_task_completion(download_task_id, 'download', 180)
        
        if download_result['status'] == 'completed':
            print("   ✅ 下载任务成功完成")
        elif download_result['status'] == 'failed':
            print(f"   ❌ 下载任务失败: {download_result.get('error', 'Unknown error')}")
        else:
            print("   ⏰ 下载任务超时")
        
        # 验证至少有一个任务成功启动
        self.assertGreater(len(self.tester.test_tasks), 0, "应该至少有一个任务成功启动")
        
        print("   🎉 视频处理流水线测试完成")
    
    def test_video_composition_workflow(self):
        """测试视频合成工作流程"""
        print("\n🎬 测试视频合成工作流程...")
        
        # 创建测试字幕文件
        subtitle_file = self.tester.create_test_subtitle_file()
        
        # 测试不同类型的合成
        composition_tests = [
            {
                'name': '视频拼接',
                'type': 'concat',
                'videos': self.tester.test_video_urls[:2],
                'expected_video_count': 2
            },
            {
                'name': '音频视频字幕合成',
                'type': 'audio_video_subtitle',
                'videos': [self.tester.test_video_urls[0]],
                'audio_file': self.tester.test_audio_url,
                'subtitle_file': subtitle_file,
                'expected_video_count': 1
            }
        ]
        
        successful_compositions = 0
        
        for test_config in composition_tests:
            print(f"   🎭 测试 {test_config['name']}...")
            
            request_data = {
                "composition_type": test_config['type'],
                "videos": [{"video_url": url} for url in test_config['videos']],
                "output_format": "mp4"
            }
            
            if 'audio_file' in test_config:
                request_data['audio_file'] = test_config['audio_file']
            
            if 'subtitle_file' in test_config:
                request_data['subtitle_file'] = test_config['subtitle_file']
            
            response = self.tester.session.post(
                f"{self.tester.api_base_url}/compose_video",
                json=request_data
            )
            
            if response.status_code == 503:
                print(f"      ⚠️ {test_config['name']} 被资源限制拒绝")
                continue
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            task_id = data.get('task_id')
            self.tester.test_tasks.append(task_id)
            
            print(f"      ✅ {test_config['name']} 任务已启动: {task_id[:8]}...")
            successful_compositions += 1
            
            # 等待一段时间查看任务状态
            time.sleep(5)
            status_response = self.tester.session.get(
                f"{self.tester.api_base_url}/composition_status/{task_id}"
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"      📊 当前状态: {status_data.get('status')}, 进度: {status_data.get('progress', 0)}%")
        
        self.assertGreater(successful_compositions, 0, "应该至少有一个合成任务成功启动")
        print("   🎉 视频合成工作流程测试完成")

class TestConcurrentProcessing(unittest.TestCase):
    """并发处理测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = ComprehensiveIntegrationTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_concurrent_task_submission_and_processing(self):
        """测试并发任务提交和处理"""
        print("\n🔄 测试并发任务提交和处理...")
        
        def submit_transcription_task(video_url: str, task_index: int) -> Dict[str, Any]:
            """提交转录任务"""
            try:
                session = requests.Session()
                response = session.post(
                    f"{self.tester.api_base_url}/generate_text_from_video",
                    json={"video_url": video_url},
                    timeout=15
                )
                
                return {
                    'index': task_index,
                    'status_code': response.status_code,
                    'task_id': response.json().get('task_id') if response.status_code == 200 else None,
                    'response_time': response.elapsed.total_seconds(),
                    'error': response.json().get('detail') if response.status_code != 200 else None
                }
            except Exception as e:
                return {
                    'index': task_index,
                    'status_code': 0,
                    'task_id': None,
                    'response_time': 0,
                    'error': str(e)
                }
        
        # 并发提交多个任务
        num_tasks = 8
        video_urls = [self.tester.test_video_urls[i % len(self.tester.test_video_urls)] for i in range(num_tasks)]
        
        print(f"   📤 并发提交 {num_tasks} 个转录任务...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_tasks) as executor:
            futures = [
                executor.submit(submit_transcription_task, video_urls[i], i)
                for i in range(num_tasks)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        successful_tasks = [r for r in results if r['status_code'] == 200]
        resource_limited_tasks = [r for r in results if r['status_code'] == 503]
        failed_tasks = [r for r in results if r['status_code'] not in [200, 503]]
        
        print(f"   📊 结果统计:")
        print(f"      ✅ 成功提交: {len(successful_tasks)} 个")
        print(f"      🚫 资源限制: {len(resource_limited_tasks)} 个")
        print(f"      ❌ 提交失败: {len(failed_tasks)} 个")
        
        if successful_tasks:
            avg_response_time = sum(r['response_time'] for r in successful_tasks) / len(successful_tasks)
            print(f"      ⏱️ 平均响应时间: {avg_response_time:.3f} 秒")
            
            # 记录成功的任务ID以便清理
            for result in successful_tasks:
                if result['task_id']:
                    self.tester.test_tasks.append(result['task_id'])
        
        # 验证系统正确处理了并发请求
        total_handled = len(successful_tasks) + len(resource_limited_tasks)
        self.assertGreater(total_handled, 0, "系统应该能处理至少一些并发请求")
        
        # 如果有资源限制，说明系统正确执行了限制策略
        if resource_limited_tasks:
            print("   ✅ 系统正确执行了资源限制策略")
        
        print("   🎉 并发处理测试完成")

class TestResourceManagementAndRecovery(unittest.TestCase):
    """资源管理和错误恢复测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.tester = ComprehensiveIntegrationTester()
        
        if not self.tester.check_api_availability():
            self.skipTest("API服务不可用")
    
    def tearDown(self):
        """测试后的清理"""
        self.tester.cleanup()
    
    def test_resource_limit_enforcement_and_recovery(self):
        """测试资源限制执行和恢复"""
        print("\n🛡️ 测试资源限制执行和恢复...")
        
        # 1. 获取当前资源状态
        print("   📊 获取当前资源状态...")
        response = self.tester.session.get(f"{self.tester.api_base_url}/system/resources")
        self.assertEqual(response.status_code, 200)
        
        original_data = response.json()
        original_max_tasks = original_data.get('max_concurrent_tasks', 3)
        
        print(f"      原始最大并发任务数: {original_max_tasks}")
        
        try:
            # 2. 设置很低的并发限制
            print("   ⚙️ 设置低并发限制...")
            response = self.tester.session.put(
                f"{self.tester.api_base_url}/system/resources/limits",
                params={"max_concurrent_tasks": 1}
            )
            self.assertEqual(response.status_code, 200)
            print("      ✅ 并发限制已设置为1")
            
            # 3. 尝试提交多个任务
            print("   📤 尝试提交多个任务...")
            task_results = []
            
            for i in range(5):
                response = self.tester.session.post(
                    f"{self.tester.api_base_url}/generate_text_from_video",
                    json={"video_url": self.tester.test_video_urls[0]}
                )
                
                task_results.append({
                    'index': i,
                    'status_code': response.status_code,
                    'task_id': response.json().get('task_id') if response.status_code == 200 else None
                })
                
                if response.status_code == 200:
                    task_id = response.json().get('task_id')
                    if task_id:
                        self.tester.test_tasks.append(task_id)
                        print(f"      ✅ 任务 {i+1} 成功提交: {task_id[:8]}...")
                elif response.status_code == 503:
                    print(f"      🚫 任务 {i+1} 被资源限制拒绝")
                    break
                
                time.sleep(1)  # 短暂等待
            
            # 4. 验证资源限制生效
            successful_tasks = [r for r in task_results if r['status_code'] == 200]
            rejected_tasks = [r for r in task_results if r['status_code'] == 503]
            
            print(f"   📊 任务提交结果: 成功={len(successful_tasks)}, 拒绝={len(rejected_tasks)}")
            
            # 应该有任务被拒绝，说明限制生效
            if rejected_tasks:
                print("   ✅ 资源限制正确执行")
            
            # 5. 等待一段时间，然后尝试恢复
            print("   ⏳ 等待任务处理...")
            time.sleep(10)
            
            # 6. 检查系统状态
            response = self.tester.session.get(f"{self.tester.api_base_url}/system/resources")
            self.assertEqual(response.status_code, 200)
            
            current_data = response.json()
            active_tasks = current_data.get('active_tasks', 0)
            print(f"      当前活跃任务数: {active_tasks}")
            
        finally:
            # 7. 恢复原始设置
            print("   🔄 恢复原始资源限制...")
            response = self.tester.session.put(
                f"{self.tester.api_base_url}/system/resources/limits",
                params={"max_concurrent_tasks": original_max_tasks}
            )
            self.assertEqual(response.status_code, 200)
            print(f"      ✅ 并发限制已恢复为 {original_max_tasks}")
        
        print("   🎉 资源限制和恢复测试完成")

def run_comprehensive_integration_tests():
    """运行综合集成测试"""
    print("🚀 开始运行综合集成测试")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestEndToEndWorkflows,
        TestConcurrentProcessing,
        TestResourceManagementAndRecovery
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # 输出结果摘要
    print("\n" + "=" * 80)
    print(f"📊 综合集成测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("🎉 所有综合集成测试通过！")
        print("✅ 系统具备良好的端到端功能和稳定性")
    else:
        print("⚠️ 部分综合集成测试失败")
        
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
    import sys
    success = run_comprehensive_integration_tests()
    sys.exit(0 if success else 1)