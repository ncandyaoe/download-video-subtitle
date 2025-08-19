#!/usr/bin/env python3
"""
性能优化集成测试
测试性能优化功能与API的集成
"""

import requests
import time
import json
from typing import Dict, Any

class PerformanceIntegrationTester:
    """性能优化集成测试器"""
    
    def __init__(self, api_base_url: str = "http://localhost:7878"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def check_api_availability(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def test_performance_stats_endpoint(self) -> bool:
        """测试性能统计端点"""
        print("\n🧪 测试性能统计端点...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/performance/stats")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            
            # 验证响应结构
            required_fields = ['status', 'data', 'timestamp']
            for field in required_fields:
                if field not in data:
                    print(f"   ❌ 缺少字段: {field}")
                    return False
            
            performance_data = data['data']
            expected_sections = ['cache_stats', 'hardware_info', 'memory_stats']
            for section in expected_sections:
                if section not in performance_data:
                    print(f"   ❌ 缺少性能数据部分: {section}")
                    return False
            
            # 显示统计信息
            cache_stats = performance_data['cache_stats']
            hardware_info = performance_data['hardware_info']
            memory_stats = performance_data['memory_stats']
            
            print(f"   📊 缓存统计:")
            print(f"      - 缓存项数: {cache_stats['total_items']}")
            print(f"      - 缓存大小: {cache_stats['total_size_mb']:.2f}MB")
            print(f"      - 使用率: {cache_stats['usage_percent']:.1f}%")
            
            print(f"   📊 硬件信息:")
            print(f"      - 可用编码器: {len(hardware_info['available_encoders'])}")
            print(f"      - 首选编码器: {hardware_info['preferred_encoder']}")
            print(f"      - 硬件加速: {'是' if hardware_info['has_hardware_acceleration'] else '否'}")
            
            print(f"   📊 内存统计:")
            memory_info = memory_stats['memory_info']
            print(f"      - 内存使用率: {memory_info['used_percent']:.1f}%")
            print(f"      - 可用内存: {memory_info['available_gb']:.1f}GB")
            
            print("   ✅ 性能统计端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_cache_stats_endpoint(self) -> bool:
        """测试缓存统计端点"""
        print("\n🧪 测试缓存统计端点...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/performance/cache/stats")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            cache_stats = data['data']
            
            print(f"   📊 缓存详细统计:")
            print(f"      - 总项目数: {cache_stats['total_items']}")
            print(f"      - 总大小: {cache_stats['total_size_mb']:.2f}MB")
            print(f"      - 最大大小: {cache_stats['max_size_mb']:.2f}MB")
            print(f"      - 使用率: {cache_stats['usage_percent']:.1f}%")
            print(f"      - 缓存目录: {cache_stats['cache_dir']}")
            
            if cache_stats['items_by_type']:
                print(f"      - 按类型分布:")
                for item_type, stats in cache_stats['items_by_type'].items():
                    print(f"        * {item_type}: {stats['count']}项, {stats['size_mb']:.2f}MB")
            
            print("   ✅ 缓存统计端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_hardware_info_endpoint(self) -> bool:
        """测试硬件信息端点"""
        print("\n🧪 测试硬件信息端点...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/performance/hardware")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            hardware_info = data['data']
            
            print(f"   🔧 硬件加速信息:")
            print(f"      - 硬件加速支持: {'是' if hardware_info['has_hardware_acceleration'] else '否'}")
            print(f"      - 首选编码器: {hardware_info['preferred_encoder']}")
            print(f"      - 可用编码器列表:")
            
            for encoder in hardware_info['available_encoders']:
                encoder_details = hardware_info['encoder_details'].get(encoder, {})
                encoder_type = encoder_details.get('type', 'unknown')
                codec = encoder_details.get('codec', 'unknown')
                print(f"        * {encoder} ({encoder_type}, {codec})")
            
            print("   ✅ 硬件信息端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_memory_stats_endpoint(self) -> bool:
        """测试内存统计端点"""
        print("\n🧪 测试内存统计端点...")
        
        try:
            response = self.session.get(f"{self.api_base_url}/system/performance/memory")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            memory_stats = data['data']
            
            print(f"   💾 内存优化统计:")
            memory_info = memory_stats['memory_info']
            print(f"      - 总内存: {memory_info['total_gb']:.1f}GB")
            print(f"      - 可用内存: {memory_info['available_gb']:.1f}GB")
            print(f"      - 使用率: {memory_info['used_percent']:.1f}%")
            print(f"      - 最大使用率限制: {memory_stats['max_usage_percent']}%")
            print(f"      - 块大小: {memory_stats['chunk_size_mb']}MB")
            print(f"      - 临时目录: {memory_stats['temp_dir']}")
            print(f"      - 内存可用: {'是' if memory_stats['is_memory_available'] else '否'}")
            
            print("   ✅ 内存统计端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_memory_cleanup_endpoint(self) -> bool:
        """测试内存清理端点"""
        print("\n🧪 测试内存清理端点...")
        
        try:
            # 获取清理前的内存状态
            before_response = self.session.get(f"{self.api_base_url}/system/performance/memory")
            before_data = before_response.json()['data']
            before_usage = before_data['memory_info']['used_percent']
            
            # 执行内存清理
            response = self.session.post(f"{self.api_base_url}/system/performance/memory/cleanup")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            after_data = data['data']
            after_usage = after_data['memory_info']['used_percent']
            
            print(f"   🧹 内存清理结果:")
            print(f"      - 清理前使用率: {before_usage:.1f}%")
            print(f"      - 清理后使用率: {after_usage:.1f}%")
            print(f"      - 清理效果: {before_usage - after_usage:.1f}%")
            print(f"      - 状态: {data['status']}")
            print(f"      - 消息: {data['message']}")
            
            print("   ✅ 内存清理端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_system_optimization_endpoint(self) -> bool:
        """测试系统优化端点"""
        print("\n🧪 测试系统优化端点...")
        
        try:
            response = self.session.post(f"{self.api_base_url}/system/performance/optimize")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            
            print(f"   ⚡ 系统优化结果:")
            print(f"      - 状态: {data['status']}")
            print(f"      - 消息: {data['message']}")
            
            # 显示优化后的统计信息
            if 'data' in data:
                performance_data = data['data']
                cache_stats = performance_data['cache_stats']
                memory_stats = performance_data['memory_stats']
                
                print(f"      - 优化后缓存使用率: {cache_stats['usage_percent']:.1f}%")
                print(f"      - 优化后内存使用率: {memory_stats['memory_info']['used_percent']:.1f}%")
            
            print("   ✅ 系统优化端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False
    
    def test_cache_clear_endpoint(self) -> bool:
        """测试缓存清理端点"""
        print("\n🧪 测试缓存清理端点...")
        
        try:
            # 获取清理前的缓存状态
            before_response = self.session.get(f"{self.api_base_url}/system/performance/cache/stats")
            before_data = before_response.json()['data']
            before_items = before_data['total_items']
            before_size = before_data['total_size_mb']
            
            # 执行缓存清理
            response = self.session.post(f"{self.api_base_url}/system/performance/cache/clear")
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: {response.status_code}")
                return False
            
            data = response.json()
            
            # 获取清理后的缓存状态
            after_response = self.session.get(f"{self.api_base_url}/system/performance/cache/stats")
            after_data = after_response.json()['data']
            after_items = after_data['total_items']
            after_size = after_data['total_size_mb']
            
            print(f"   🗑️ 缓存清理结果:")
            print(f"      - 清理前项目数: {before_items}")
            print(f"      - 清理后项目数: {after_items}")
            print(f"      - 清理前大小: {before_size:.2f}MB")
            print(f"      - 清理后大小: {after_size:.2f}MB")
            print(f"      - 状态: {data['status']}")
            print(f"      - 消息: {data['message']}")
            
            print("   ✅ 缓存清理端点测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
            return False

def run_performance_integration_tests():
    """运行性能优化集成测试"""
    print("🚀 开始运行性能优化集成测试")
    print("=" * 60)
    
    tester = PerformanceIntegrationTester()
    
    # 检查API可用性
    if not tester.check_api_availability():
        print("❌ API服务不可用，请确保服务正在运行")
        return False
    
    print("✅ API服务可用")
    
    # 运行测试
    tests = [
        ("性能统计端点", tester.test_performance_stats_endpoint),
        ("缓存统计端点", tester.test_cache_stats_endpoint),
        ("硬件信息端点", tester.test_hardware_info_endpoint),
        ("内存统计端点", tester.test_memory_stats_endpoint),
        ("内存清理端点", tester.test_memory_cleanup_endpoint),
        ("缓存清理端点", tester.test_cache_clear_endpoint),
        ("系统优化端点", tester.test_system_optimization_endpoint),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"   ❌ {test_name} 测试失败")
        except Exception as e:
            print(f"   💥 {test_name} 测试异常: {str(e)}")
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print(f"📊 性能优化集成测试结果摘要:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过: {passed_tests}")
    print(f"   失败: {total_tests - passed_tests}")
    print(f"   成功率: {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 所有性能优化集成测试通过！")
        print("✅ 性能优化功能已成功集成到API中")
        return True
    else:
        print("⚠️ 部分性能优化集成测试失败")
        return False

if __name__ == "__main__":
    import sys
    success = run_performance_integration_tests()
    sys.exit(0 if success else 1)