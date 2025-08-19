#!/usr/bin/env python3
"""
视频处理API测试运行器
统一运行所有测试并生成报告
"""

import subprocess
import sys
import time
import os
import json
from datetime import datetime
from typing import Dict, List, Any

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_api_server(self) -> bool:
        """检查API服务器是否运行"""
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def run_gradio_interface(self) -> bool:
        """启动Gradio测试界面"""
        print("🌐 启动Gradio测试界面...")
        try:
            # 检查gradio是否安装
            subprocess.run([sys.executable, "-c", "import gradio"], 
                         check=True, capture_output=True)
            
            print("   ✅ Gradio已安装")
            print("   🚀 启动测试界面...")
            print("   📱 界面地址: http://localhost:7860")
            print("   💡 提示: 在浏览器中打开上述地址进行交互式测试")
            
            # 启动Gradio界面（后台运行）
            process = subprocess.Popen([
                sys.executable, "gradio_test_interface.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 等待几秒钟让界面启动
            time.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                print("   ✅ Gradio界面已启动")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"   ❌ Gradio界面启动失败: {stderr.decode()}")
                return False
                
        except subprocess.CalledProcessError:
            print("   ❌ Gradio未安装，请运行: pip install gradio")
            return False
        except Exception as e:
            print(f"   ❌ 启动Gradio界面失败: {str(e)}")
            return False
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """运行单元测试"""
        print("\n🧪 运行单元测试...")
        try:
            result = subprocess.run([
                sys.executable, "test_unit_tests.py"
            ], capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            
            return {
                'name': '单元测试',
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': 0  # 实际运行时间会在调用处计算
            }
            
        except subprocess.TimeoutExpired:
            return {
                'name': '单元测试',
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': '测试超时',
                'duration': 300
            }
        except Exception as e:
            return {
                'name': '单元测试',
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': 0
            }
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """运行集成测试"""
        print("\n🔗 运行集成测试...")
        try:
            result = subprocess.run([
                sys.executable, "test_integration_tests.py"
            ], capture_output=True, text=True, timeout=600)
            
            success = result.returncode == 0
            
            return {
                'name': '集成测试',
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                'name': '集成测试',
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': '测试超时',
                'duration': 600
            }
        except Exception as e:
            return {
                'name': '集成测试',
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': 0
            }
    
    def run_existing_tests(self) -> List[Dict[str, Any]]:
        """运行现有的测试脚本"""
        print("\n📋 运行现有测试脚本...")
        
        existing_tests = [
            ("资源监控测试", "test_resource_monitoring.py"),
            ("错误处理测试", "test_error_handling.py"),
            ("合成功能测试", "test_composition.py"),
            ("音频处理测试", "test_audio_processing.py"),
        ]
        
        results = []
        
        for test_name, test_file in existing_tests:
            if os.path.exists(test_file):
                print(f"   🔍 运行 {test_name}...")
                try:
                    start_time = time.time()
                    result = subprocess.run([
                        sys.executable, test_file, "--test", "all"
                    ], capture_output=True, text=True, timeout=180)
                    
                    duration = time.time() - start_time
                    success = result.returncode == 0
                    
                    results.append({
                        'name': test_name,
                        'success': success,
                        'returncode': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'duration': duration
                    })
                    
                    if success:
                        print(f"      ✅ {test_name} 通过")
                    else:
                        print(f"      ❌ {test_name} 失败")
                        
                except subprocess.TimeoutExpired:
                    results.append({
                        'name': test_name,
                        'success': False,
                        'returncode': -1,
                        'stdout': '',
                        'stderr': '测试超时',
                        'duration': 180
                    })
                    print(f"      ⏰ {test_name} 超时")
                    
                except Exception as e:
                    results.append({
                        'name': test_name,
                        'success': False,
                        'returncode': -1,
                        'stdout': '',
                        'stderr': str(e),
                        'duration': 0
                    })
                    print(f"      💥 {test_name} 异常: {str(e)}")
            else:
                print(f"   ⚠️ 跳过 {test_name} (文件不存在: {test_file})")
        
        return results
    
    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("# 视频处理API测试报告")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**总耗时**: {self.end_time - self.start_time:.2f} 秒")
        report.append("")
        
        # 统计总体结果
        all_results = []
        for category, tests in self.results.items():
            if isinstance(tests, list):
                all_results.extend(tests)
            else:
                all_results.append(tests)
        
        total_tests = len(all_results)
        passed_tests = sum(1 for r in all_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        report.append("## 📊 测试概览")
        report.append(f"- **总测试数**: {total_tests}")
        report.append(f"- **通过**: {passed_tests} ✅")
        report.append(f"- **失败**: {failed_tests} ❌")
        report.append(f"- **成功率**: {(passed_tests/total_tests*100):.1f}%")
        report.append("")
        
        # 详细结果
        for category, tests in self.results.items():
            report.append(f"## 🔍 {category}")
            
            if isinstance(tests, list):
                for test in tests:
                    status = "✅" if test['success'] else "❌"
                    report.append(f"- **{test['name']}**: {status}")
                    report.append(f"  - 耗时: {test['duration']:.2f}秒")
                    if not test['success']:
                        report.append(f"  - 错误: {test['stderr'][:100]}...")
            else:
                status = "✅" if tests['success'] else "❌"
                report.append(f"- **{tests['name']}**: {status}")
                report.append(f"  - 耗时: {tests['duration']:.2f}秒")
                if not tests['success']:
                    report.append(f"  - 错误: {tests['stderr'][:100]}...")
            
            report.append("")
        
        # 建议
        report.append("## 💡 建议")
        if failed_tests == 0:
            report.append("🎉 所有测试都通过了！系统运行良好。")
        else:
            report.append("⚠️ 部分测试失败，建议检查以下方面：")
            report.append("- API服务是否正常运行")
            report.append("- 系统资源是否充足")
            report.append("- 网络连接是否正常")
            report.append("- 依赖服务是否可用")
        
        report.append("")
        report.append("## 🔧 使用Gradio界面进行交互式测试")
        report.append("运行以下命令启动Web测试界面：")
        report.append("```bash")
        report.append("python gradio_test_interface.py")
        report.append("```")
        report.append("然后在浏览器中访问 http://localhost:7860")
        
        return "\n".join(report)
    
    def run_all_tests(self, include_gradio: bool = True):
        """运行所有测试"""
        self.start_time = time.time()
        
        print("🚀 开始运行视频处理API测试套件")
        print("=" * 60)
        
        # 检查API服务器
        if not self.check_api_server():
            print("❌ API服务器未运行，请先启动API服务器")
            print("   启动命令: python api.py")
            return False
        
        print("✅ API服务器运行正常")
        
        # 启动Gradio界面（可选）
        if include_gradio:
            gradio_success = self.run_gradio_interface()
            if gradio_success:
                print("   💡 您可以在浏览器中打开 http://localhost:7860 进行交互式测试")
        
        # 运行单元测试
        start_time = time.time()
        unit_test_result = self.run_unit_tests()
        unit_test_result['duration'] = time.time() - start_time
        self.results['单元测试'] = unit_test_result
        
        # 运行集成测试
        start_time = time.time()
        integration_test_result = self.run_integration_tests()
        integration_test_result['duration'] = time.time() - start_time
        self.results['集成测试'] = integration_test_result
        
        # 运行现有测试
        existing_test_results = self.run_existing_tests()
        self.results['现有测试'] = existing_test_results
        
        self.end_time = time.time()
        
        # 生成报告
        print("\n" + "=" * 60)
        print("📋 生成测试报告...")
        
        report = self.generate_report()
        
        # 保存报告到文件
        with open("test_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print("✅ 测试报告已保存到: test_report.md")
        
        # 输出简要结果
        print("\n📊 测试结果摘要:")
        all_results = []
        for category, tests in self.results.items():
            if isinstance(tests, list):
                all_results.extend(tests)
            else:
                all_results.append(tests)
        
        total_tests = len(all_results)
        passed_tests = sum(1 for r in all_results if r['success'])
        
        print(f"   总测试数: {total_tests}")
        print(f"   通过: {passed_tests}")
        print(f"   失败: {total_tests - passed_tests}")
        print(f"   成功率: {(passed_tests/total_tests*100):.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 所有测试通过！")
            return True
        else:
            print("⚠️ 部分测试失败，请查看详细报告")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="视频处理API测试运行器")
    parser.add_argument(
        "--no-gradio", 
        action="store_true",
        help="不启动Gradio测试界面"
    )
    parser.add_argument(
        "--gradio-only",
        action="store_true", 
        help="只启动Gradio测试界面"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.gradio_only:
        # 只启动Gradio界面
        print("🌐 启动Gradio测试界面...")
        if runner.check_api_server():
            success = runner.run_gradio_interface()
            if success:
                print("✅ Gradio界面已启动，请在浏览器中访问 http://localhost:7860")
                print("💡 按 Ctrl+C 退出")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 再见！")
            else:
                print("❌ Gradio界面启动失败")
                sys.exit(1)
        else:
            print("❌ API服务器未运行，请先启动API服务器")
            sys.exit(1)
    else:
        # 运行所有测试
        success = runner.run_all_tests(include_gradio=not args.no_gradio)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()