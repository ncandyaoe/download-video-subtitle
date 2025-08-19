#!/usr/bin/env python3
"""
性能优化器测试
"""

import unittest
import tempfile
import os
import json
import time
from pathlib import Path
from performance_optimizer import (
    CacheManager, 
    HardwareAccelerationDetector, 
    MemoryOptimizedProcessor,
    PerformanceOptimizer
)

class TestCacheManager(unittest.TestCase):
    """缓存管理器测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(
            cache_dir=os.path.join(self.temp_dir, "cache"),
            max_cache_size_gb=0.1  # 100MB用于测试
        )
        
        # 创建测试视频文件
        self.test_video = os.path.join(self.temp_dir, "test_video.mp4")
        with open(self.test_video, 'wb') as f:
            f.write(b'fake video content for testing')
    
    def tearDown(self):
        """测试后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_metadata_cache(self):
        """测试元数据缓存"""
        print("\n🧪 测试元数据缓存...")
        
        # 测试数据
        test_metadata = {
            'duration': 120.5,
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'codec': 'h264'
        }
        
        # 设置缓存
        self.cache_manager.set_video_metadata_cache(self.test_video, test_metadata)
        
        # 获取缓存
        cached_metadata = self.cache_manager.get_video_metadata_cache(self.test_video)
        
        self.assertIsNotNone(cached_metadata)
        self.assertEqual(cached_metadata['duration'], 120.5)
        self.assertEqual(cached_metadata['width'], 1920)
        
        print("   ✅ 元数据缓存测试通过")
    
    def test_processed_video_cache(self):
        """测试预处理视频缓存"""
        print("\n🧪 测试预处理视频缓存...")
        
        # 创建处理后的视频文件
        processed_video = os.path.join(self.temp_dir, "processed_video.mp4")
        with open(processed_video, 'wb') as f:
            f.write(b'processed video content')
        
        # 处理参数
        processing_params = {
            'resolution': '720p',
            'codec': 'h264',
            'quality': 'medium'
        }
        
        # 设置缓存
        self.cache_manager.set_processed_video_cache(
            self.test_video, processing_params, processed_video
        )
        
        # 获取缓存
        cached_video = self.cache_manager.get_processed_video_cache(
            self.test_video, processing_params
        )
        
        self.assertIsNotNone(cached_video)
        self.assertTrue(os.path.exists(cached_video))
        
        print("   ✅ 预处理视频缓存测试通过")
    
    def test_cache_stats(self):
        """测试缓存统计"""
        print("\n🧪 测试缓存统计...")
        
        # 添加一些缓存数据
        test_metadata = {'duration': 60, 'width': 1280, 'height': 720}
        self.cache_manager.set_video_metadata_cache(self.test_video, test_metadata)
        
        # 获取统计信息
        stats = self.cache_manager.get_cache_stats()
        
        self.assertIn('total_items', stats)
        self.assertIn('total_size_mb', stats)
        self.assertIn('usage_percent', stats)
        self.assertGreater(stats['total_items'], 0)
        
        print(f"   📊 缓存项数: {stats['total_items']}")
        print(f"   📊 缓存大小: {stats['total_size_mb']:.2f}MB")
        print(f"   📊 使用率: {stats['usage_percent']:.1f}%")
        print("   ✅ 缓存统计测试通过")

class TestHardwareAccelerationDetector(unittest.TestCase):
    """硬件加速检测器测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.detector = HardwareAccelerationDetector()
    
    def test_hardware_detection(self):
        """测试硬件检测"""
        print("\n🧪 测试硬件加速检测...")
        
        hardware_info = self.detector.get_hardware_info()
        
        self.assertIn('available_encoders', hardware_info)
        self.assertIn('has_hardware_acceleration', hardware_info)
        
        print(f"   🔧 可用编码器: {hardware_info['available_encoders']}")
        print(f"   🔧 首选编码器: {hardware_info['preferred_encoder']}")
        print(f"   🔧 硬件加速: {'是' if hardware_info['has_hardware_acceleration'] else '否'}")
        print("   ✅ 硬件检测测试通过")
    
    def test_encoder_params(self):
        """测试编码器参数生成"""
        print("\n🧪 测试编码器参数生成...")
        
        # 测试不同质量设置
        for quality in ['fast', 'medium', 'slow']:
            params = self.detector.get_encoder_params('h264', quality)
            
            self.assertIsInstance(params, list)
            self.assertIn('-c:v', params)
            
            print(f"   ⚙️ {quality} 质量参数: {' '.join(params[:6])}...")
        
        print("   ✅ 编码器参数测试通过")

class TestMemoryOptimizedProcessor(unittest.TestCase):
    """内存优化处理器测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.processor = MemoryOptimizedProcessor(
            max_memory_usage_percent=80.0,
            chunk_size_mb=50
        )
    
    def test_memory_check(self):
        """测试内存检查"""
        print("\n🧪 测试内存检查...")
        
        memory_info = self.processor.check_memory_usage()
        
        self.assertIn('total_gb', memory_info)
        self.assertIn('available_gb', memory_info)
        self.assertIn('used_percent', memory_info)
        
        print(f"   💾 总内存: {memory_info['total_gb']:.1f}GB")
        print(f"   💾 可用内存: {memory_info['available_gb']:.1f}GB")
        print(f"   💾 使用率: {memory_info['used_percent']:.1f}%")
        
        # 测试内存可用性检查
        is_available = self.processor.is_memory_available(100)  # 需要100MB
        print(f"   💾 内存可用: {'是' if is_available else '否'}")
        
        print("   ✅ 内存检查测试通过")
    
    def test_memory_cleanup(self):
        """测试内存清理"""
        print("\n🧪 测试内存清理...")
        
        # 记录清理前的内存使用
        before_cleanup = self.processor.check_memory_usage()
        
        # 执行内存清理
        self.processor.trigger_memory_cleanup()
        
        # 记录清理后的内存使用
        after_cleanup = self.processor.check_memory_usage()
        
        print(f"   🧹 清理前使用率: {before_cleanup['used_percent']:.1f}%")
        print(f"   🧹 清理后使用率: {after_cleanup['used_percent']:.1f}%")
        print("   ✅ 内存清理测试通过")
    
    def test_memory_stats(self):
        """测试内存统计"""
        print("\n🧪 测试内存统计...")
        
        stats = self.processor.get_memory_stats()
        
        self.assertIn('memory_info', stats)
        self.assertIn('max_usage_percent', stats)
        self.assertIn('chunk_size_mb', stats)
        
        print(f"   📊 最大使用率限制: {stats['max_usage_percent']}%")
        print(f"   📊 块大小: {stats['chunk_size_mb']}MB")
        print(f"   📊 临时目录: {stats['temp_dir']}")
        print("   ✅ 内存统计测试通过")

class TestPerformanceOptimizer(unittest.TestCase):
    """性能优化器集成测试"""
    
    def setUp(self):
        """测试前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.optimizer = PerformanceOptimizer(
            cache_dir=os.path.join(self.temp_dir, "cache"),
            max_cache_size_gb=0.1,
            max_memory_usage_percent=80.0
        )
    
    def tearDown(self):
        """测试后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_optimization_stats(self):
        """测试优化统计信息"""
        print("\n🧪 测试优化统计信息...")
        
        stats = self.optimizer.get_optimization_stats()
        
        self.assertIn('cache_stats', stats)
        self.assertIn('hardware_info', stats)
        self.assertIn('memory_stats', stats)
        self.assertIn('timestamp', stats)
        
        print("   📊 缓存统计:")
        cache_stats = stats['cache_stats']
        print(f"      - 缓存项数: {cache_stats['total_items']}")
        print(f"      - 缓存大小: {cache_stats['total_size_mb']:.2f}MB")
        
        print("   📊 硬件信息:")
        hardware_info = stats['hardware_info']
        print(f"      - 可用编码器: {len(hardware_info['available_encoders'])}")
        print(f"      - 硬件加速: {'是' if hardware_info['has_hardware_acceleration'] else '否'}")
        
        print("   📊 内存统计:")
        memory_stats = stats['memory_stats']
        memory_info = memory_stats['memory_info']
        print(f"      - 内存使用率: {memory_info['used_percent']:.1f}%")
        print(f"      - 可用内存: {memory_info['available_gb']:.1f}GB")
        
        print("   ✅ 优化统计测试通过")
    
    def test_ffmpeg_command_optimization(self):
        """测试FFmpeg命令优化"""
        print("\n🧪 测试FFmpeg命令优化...")
        
        # 基础FFmpeg命令
        base_cmd = [
            'ffmpeg', '-i', 'input.mp4',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            'output.mp4'
        ]
        
        # 优化命令
        optimized_cmd = self.optimizer.optimize_ffmpeg_command(base_cmd, 'medium')
        
        self.assertIsInstance(optimized_cmd, list)
        self.assertIn('ffmpeg', optimized_cmd)
        self.assertIn('-c:v', optimized_cmd)
        
        print(f"   ⚙️ 原始命令: {' '.join(base_cmd[:8])}...")
        print(f"   ⚙️ 优化命令: {' '.join(optimized_cmd[:8])}...")
        print("   ✅ FFmpeg命令优化测试通过")

def run_performance_optimizer_tests():
    """运行性能优化器测试"""
    print("🚀 开始运行性能优化器测试")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestCacheManager,
        TestHardwareAccelerationDetector,
        TestMemoryOptimizedProcessor,
        TestPerformanceOptimizer
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print(f"📊 性能优化器测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("🎉 所有性能优化器测试通过！")
        print("✅ 性能优化功能运行正常")
    else:
        print("⚠️ 部分性能优化器测试失败")
        
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
    success = run_performance_optimizer_tests()
    sys.exit(0 if success else 1)