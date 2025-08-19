#!/usr/bin/env python3
"""
任务8-9综合测试脚本
运行任务8（关键帧幻灯片）和任务9（高级音频处理）的所有测试
"""

import sys
import os
import subprocess
import time
import json

def run_test_script(script_name, task_name):
    """运行测试脚本"""
    print(f"\n🚀 开始运行 {task_name} 测试...")
    print("=" * 60)
    
    try:
        # 运行测试脚本
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {task_name} 测试通过")
            return True
        else:
            print(f"❌ {task_name} 测试失败 (退出码: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {task_name} 测试超时")
        return False
    except FileNotFoundError:
        print(f"❌ 测试脚本不存在: {script_name}")
        return False
    except Exception as e:
        print(f"❌ 运行 {task_name} 测试时出现异常: {str(e)}")
        return False

def check_test_files():
    """检查测试文件是否存在"""
    test_files = [
        ("test_slideshow_complete.py", "任务8 - 关键帧幻灯片测试"),
        ("test_audio_processing.py", "任务9 - 音频处理测试")
    ]
    
    missing_files = []
    for file_name, description in test_files:
        if not os.path.exists(file_name):
            missing_files.append((file_name, description))
    
    if missing_files:
        print("❌ 缺少以下测试文件:")
        for file_name, description in missing_files:
            print(f"   - {file_name} ({description})")
        return False
    
    print("✅ 所有测试文件都存在")
    return True

def generate_combined_report(task8_success, task9_success):
    """生成综合测试报告"""
    print("\n" + "=" * 60)
    print("📊 任务8-9综合测试报告")
    print("=" * 60)
    
    # 读取各个测试的详细报告
    reports = {}
    
    # 读取任务8报告
    if os.path.exists("test_slideshow_report.json"):
        try:
            with open("test_slideshow_report.json", 'r', encoding='utf-8') as f:
                reports['task8'] = json.load(f)
        except:
            pass
    
    # 读取任务9报告
    if os.path.exists("test_audio_processing_report.json"):
        try:
            with open("test_audio_processing_report.json", 'r', encoding='utf-8') as f:
                reports['task9'] = json.load(f)
        except:
            pass
    
    # 统计信息
    total_tests = 0
    passed_tests = 0
    
    print("📋 各任务测试结果:")
    
    # 任务8结果
    task8_icon = "✅" if task8_success else "❌"
    print(f"   {task8_icon} 任务8 - 关键帧幻灯片制作功能: {'通过' if task8_success else '失败'}")
    if 'task8' in reports:
        task8_total = reports['task8']['total_tests']
        task8_passed = reports['task8']['passed_tests']
        print(f"      详细: {task8_passed}/{task8_total} 测试通过")
        total_tests += task8_total
        passed_tests += task8_passed
    
    # 任务9结果
    task9_icon = "✅" if task9_success else "❌"
    print(f"   {task9_icon} 任务9 - 高级音频处理功能: {'通过' if task9_success else '失败'}")
    if 'task9' in reports:
        task9_total = reports['task9']['total_tests']
        task9_passed = reports['task9']['passed_tests']
        print(f"      详细: {task9_passed}/{task9_total} 测试通过")
        total_tests += task9_total
        passed_tests += task9_passed
    
    # 总体统计
    print(f"\n📈 总体统计:")
    print(f"   总任务数: 2")
    print(f"   通过任务: {int(task8_success) + int(task9_success)}")
    if total_tests > 0:
        print(f"   总测试数: {total_tests}")
        print(f"   通过测试: {passed_tests}")
        print(f"   通过率: {passed_tests/total_tests*100:.1f}%")
    
    # 保存综合报告
    combined_report = {
        'task8_success': task8_success,
        'task9_success': task9_success,
        'total_tasks': 2,
        'passed_tasks': int(task8_success) + int(task9_success),
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'timestamp': time.time(),
        'individual_reports': reports
    }
    
    with open("test_tasks_8_9_report.json", 'w', encoding='utf-8') as f:
        json.dump(combined_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 综合报告已保存到: test_tasks_8_9_report.json")
    
    # 最终结果
    if task8_success and task9_success:
        print("\n🎉 所有任务测试通过！任务8-9功能开发完成")
        return True
    else:
        failed_tasks = []
        if not task8_success:
            failed_tasks.append("任务8")
        if not task9_success:
            failed_tasks.append("任务9")
        
        print(f"\n❌ 以下任务测试失败: {', '.join(failed_tasks)}")
        print("请修复问题后重新测试")
        return False

def main():
    """主函数"""
    print("🧪 任务8-9综合测试套件")
    print("=" * 60)
    print("测试范围:")
    print("- 任务8: 关键帧幻灯片制作功能")
    print("  - 8.1 图片序列视频生成器")
    print("  - 8.2 转场效果和背景音乐")
    print("- 任务9: 高级音频处理功能")
    print("  - 9.1 音频处理工具集")
    print("  - 9.2 多轨音频混合")
    print("=" * 60)
    
    # 检查测试文件
    if not check_test_files():
        sys.exit(1)
    
    # 运行测试
    task8_success = run_test_script("test_slideshow_complete.py", "任务8")
    task9_success = run_test_script("test_audio_processing.py", "任务9")
    
    # 生成综合报告
    overall_success = generate_combined_report(task8_success, task9_success)
    
    # 退出
    if overall_success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()