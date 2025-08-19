#!/usr/bin/env python3
"""
视频处理API集成测试运行器
统一运行所有集成测试套件
"""

import sys
import os
import time
import subprocess
import argparse
from datetime import datetime
from typing import List, Dict, Any

class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.test_files = [
            {
                'name': '综合集成测试',
                'file': 'test_comprehensive_integration.py',
                'description': '端到端工作流程、并发处理、资源管理和错误恢复测试',
                'priority': 1
            },
            {
                'name': '性能基准测试',
                'file': 'test_performance_benchmarks.py',
                'description': '响应时间、吞吐量、资源使用和可扩展性测试',
                'priority': 2
            },
            {
                'name': '资源监控测试',
                'file': 'test_resource_monitoring.py',
                'description': '系统资源监控和管理测试',
                'priority': 3
            }
        ]
        
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_prerequisites(self) -> bool:
        """检查测试前提条件"""
        print("🔍 检查测试前提条件...")
        
        # 检查测试文件是否存在
        missing_files = []
        for test_config in self.test_files:
            if not os.path.exists(test_config['file']):
                missing_files.append(test_config['file'])
        
        if missing_files:
            print(f"❌ 缺少测试文件: {', '.join(missing_files)}")
            return False
        
        # 检查Python依赖
        required_packages = ['requests', 'psutil', 'concurrent.futures']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ 缺少Python包: {', '.join(missing_packages)}")
            print("请运行: pip install requests psutil")
            return False
        
        # 检查API服务是否运行
        try:
            import requests
            response = requests.get("http://localhost:7878/health", timeout=5)
            if response.status_code != 200:
                print("❌ API服务未正常运行")
                return False
        except Exception as e:
            print(f"❌ 无法连接到API服务: {str(e)}")
            print("请确保API服务在 http://localhost:7878 上运行")
            return False
        
        print("✅ 所有前提条件满足")
        return True
    
    def run_single_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试文件"""
        print(f"\\n🧪 运行 {test_config['name']}...")
        print(f"   📝 描述: {test_config['description']}")
        print(f"   📁 文件: {test_config['file']}")
        
        start_time = time.time()
        
        try:
            # 运行测试文件
            result = subprocess.run(
                [sys.executable, test_config['file']],
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            test_result = {
                'name': test_config['name'],
                'file': test_config['file'],
                'success': result.returncode == 0,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
            
            if test_result['success']:
                print(f"   ✅ {test_config['name']} 通过 (耗时: {duration:.1f}秒)")
            else:
                print(f"   ❌ {test_config['name']} 失败 (耗时: {duration:.1f}秒)")
                print(f"   📄 错误输出: {result.stderr[:500]}...")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   ⏰ {test_config['name']} 超时 (耗时: {duration:.1f}秒)")
            
            return {
                'name': test_config['name'],
                'file': test_config['file'],
                'success': False,
                'duration': duration,
                'stdout': '',
                'stderr': 'Test execution timeout',
                'return_code': -1
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   💥 {test_config['name']} 执行异常: {str(e)}")
            
            return {
                'name': test_config['name'],
                'file': test_config['file'],
                'success': False,
                'duration': duration,
                'stdout': '',
                'stderr': str(e),
                'return_code': -2
            }
    
    def run_all_tests(self, selected_tests: List[str] = None) -> bool:
        """运行所有测试"""
        print("🚀 开始运行视频处理API集成测试")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # 过滤要运行的测试
        tests_to_run = self.test_files
        if selected_tests:
            tests_to_run = [t for t in self.test_files if t['name'] in selected_tests or t['file'] in selected_tests]
        
        # 按优先级排序
        tests_to_run.sort(key=lambda x: x['priority'])
        
        print(f"📋 计划运行 {len(tests_to_run)} 个测试套件:")
        for test_config in tests_to_run:
            print(f"   - {test_config['name']} ({test_config['file']})")
        
        # 运行测试
        all_passed = True
        for test_config in tests_to_run:
            result = self.run_single_test(test_config)
            self.results[test_config['name']] = result
            
            if not result['success']:
                all_passed = False
        
        self.end_time = time.time()
        
        # 生成测试报告
        self.generate_test_report()
        
        return all_passed
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\\n" + "=" * 80)
        print("📊 集成测试结果报告")
        print("=" * 80)
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        print(f"🕐 测试开始时间: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 测试结束时间: {datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ 总耗时: {total_duration:.1f}秒")
        print()
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results.values() if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"📈 测试统计:")
        print(f"   总测试套件数: {total_tests}")
        print(f"   通过: {passed_tests}")
        print(f"   失败: {failed_tests}")
        print(f"   成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "   成功率: 0%")
        print()
        
        # 详细结果
        print("📋 详细结果:")
        for name, result in self.results.items():
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"   {status} {name} (耗时: {result['duration']:.1f}秒)")
            
            if not result['success'] and result['stderr']:
                # 显示错误信息的前几行
                error_lines = result['stderr'].split('\\n')[:3]
                for line in error_lines:
                    if line.strip():
                        print(f"      💬 {line.strip()}")
        
        print()
        
        # 总结
        if passed_tests == total_tests:
            print("🎉 所有集成测试通过！")
            print("✅ 视频处理API系统运行正常，具备良好的稳定性和性能")
        else:
            print("⚠️ 部分集成测试失败")
            print("🔧 请检查失败的测试并修复相关问题")
        
        # 建议
        print("\\n💡 建议:")
        print("   - 定期运行集成测试确保系统稳定性")
        print("   - 监控测试结果趋势，及时发现性能退化")
        print("   - 在部署前运行完整的集成测试套件")
        print("   - 根据测试结果优化系统配置和资源分配")
    
    def save_test_report(self, filename: str = None):
        """保存测试报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integration_test_report_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("视频处理API集成测试报告\\n")
                f.write("=" * 50 + "\\n\\n")
                
                f.write(f"测试时间: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"总耗时: {(self.end_time - self.start_time):.1f}秒\\n\\n")
                
                for name, result in self.results.items():
                    f.write(f"测试套件: {name}\\n")
                    f.write(f"文件: {result['file']}\\n")
                    f.write(f"结果: {'通过' if result['success'] else '失败'}\\n")
                    f.write(f"耗时: {result['duration']:.1f}秒\\n")
                    
                    if not result['success']:
                        f.write(f"错误信息:\\n{result['stderr']}\\n")
                    
                    f.write("\\n" + "-" * 30 + "\\n\\n")
            
            print(f"📄 测试报告已保存到: {filename}")
            
        except Exception as e:
            print(f"⚠️ 保存测试报告失败: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='视频处理API集成测试运行器')
    parser.add_argument('--tests', nargs='*', help='指定要运行的测试 (测试名称或文件名)')
    parser.add_argument('--save-report', action='store_true', help='保存测试报告到文件')
    parser.add_argument('--report-file', help='指定报告文件名')
    parser.add_argument('--skip-check', action='store_true', help='跳过前提条件检查')
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    
    # 检查前提条件
    if not args.skip_check:
        if not runner.check_prerequisites():
            print("❌ 前提条件检查失败，测试终止")
            sys.exit(1)
    
    # 运行测试
    success = runner.run_all_tests(args.tests)
    
    # 保存报告
    if args.save_report:
        runner.save_test_report(args.report_file)
    
    # 退出
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()