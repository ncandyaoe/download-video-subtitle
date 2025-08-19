#!/usr/bin/env python3
"""
调试并排视频FFmpeg命令构建
"""

import sys
import os
sys.path.append('.')

from api import FFmpegCommandBuilder

def test_vertical_layout():
    """测试垂直布局FFmpeg命令"""
    print("🔧 测试垂直布局FFmpeg命令构建")
    
    # 模拟视频文件
    videos = [
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4",
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4"
    ]
    output_file = "./compositions/test_vertical_output.mp4"
    
    # 模拟网格布局信息
    grid_layout = {
        'cell_width': 960,
        'cell_height': 540,
        'output_width': 960,
        'output_height': 1080,
        'layout': 'vertical',
        'video_count': 2
    }
    
    # 构建FFmpeg命令
    builder = FFmpegCommandBuilder()
    
    # 添加所有视频输入
    for video_file in videos:
        builder.add_input(video_file)
    
    # 构建滤镜链
    filters = []
    
    # 缩放所有视频到统一尺寸
    for i in range(len(videos)):
        scale_filter = f"[{i}:v]scale={grid_layout['cell_width']}:{grid_layout['cell_height']}[scaled_{i}]"
        filters.append(scale_filter)
    
    # 垂直布局
    vstack_filter = "[scaled_0][scaled_1]vstack=inputs=2[output]"
    filters.append(vstack_filter)
    
    # 添加滤镜到构建器
    for filter_str in filters:
        builder.add_filter(filter_str)
    
    # 输出选项
    output_options = {
        'c:v': 'libx264',
        'c:a': 'copy',
        'b:v': '3M'
    }
    
    builder.add_output(output_file, output_options)
    
    # 构建命令
    cmd = builder.build()
    
    print("📝 基础命令:")
    print(" ".join(cmd))
    print()
    
    # 手动添加映射选项
    output_file_index = cmd.index(output_file)
    cmd.insert(output_file_index, '-map')
    cmd.insert(output_file_index + 1, '[output]')
    cmd.insert(output_file_index + 2, '-map')
    cmd.insert(output_file_index + 3, '0:a')
    
    print("✅ 最终命令:")
    print(" ".join(cmd))
    print()
    
    # 验证命令
    if builder.validate_command(cmd):
        print("✅ 命令验证通过")
    else:
        print("❌ 命令验证失败")
    
    # 分析滤镜
    print("\n🔍 滤镜分析:")
    for i, filter_str in enumerate(filters):
        print(f"  {i+1}. {filter_str}")

def test_grid_layout():
    """测试2x2网格布局FFmpeg命令"""
    print("\n🔧 测试2x2网格布局FFmpeg命令构建")
    
    # 模拟视频文件
    videos = [
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4",
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4",
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4",
        "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4"
    ]
    output_file = "./compositions/test_grid_output.mp4"
    
    # 模拟网格布局信息
    grid_layout = {
        'cell_width': 960,
        'cell_height': 540,
        'output_width': 1920,
        'output_height': 1080,
        'layout': 'grid',
        'video_count': 4
    }
    
    # 构建FFmpeg命令
    builder = FFmpegCommandBuilder()
    
    # 添加所有视频输入
    for video_file in videos:
        builder.add_input(video_file)
    
    # 构建滤镜链
    filters = []
    
    # 缩放所有视频到统一尺寸
    for i in range(len(videos)):
        scale_filter = f"[{i}:v]scale={grid_layout['cell_width']}:{grid_layout['cell_height']}[scaled_{i}]"
        filters.append(scale_filter)
    
    # 2x2网格布局
    # 先创建两行
    hstack1_filter = "[scaled_0][scaled_1]hstack=inputs=2[row1]"
    hstack2_filter = "[scaled_2][scaled_3]hstack=inputs=2[row2]"
    # 然后垂直堆叠两行
    vstack_filter = "[row1][row2]vstack=inputs=2[output]"
    filters.extend([hstack1_filter, hstack2_filter, vstack_filter])
    
    # 添加滤镜到构建器
    for filter_str in filters:
        builder.add_filter(filter_str)
    
    # 输出选项
    output_options = {
        'c:v': 'libx264',
        'c:a': 'copy',
        'b:v': '3M'
    }
    
    builder.add_output(output_file, output_options)
    
    # 构建命令
    cmd = builder.build()
    
    print("📝 基础命令:")
    print(" ".join(cmd))
    print()
    
    # 手动添加映射选项
    output_file_index = cmd.index(output_file)
    cmd.insert(output_file_index, '-map')
    cmd.insert(output_file_index + 1, '[output]')
    cmd.insert(output_file_index + 2, '-map')
    cmd.insert(output_file_index + 3, '0:a')
    
    print("✅ 最终命令:")
    print(" ".join(cmd))
    print()
    
    # 验证命令
    if builder.validate_command(cmd):
        print("✅ 命令验证通过")
    else:
        print("❌ 命令验证失败")
    
    # 分析滤镜
    print("\n🔍 滤镜分析:")
    for i, filter_str in enumerate(filters):
        print(f"  {i+1}. {filter_str}")

if __name__ == "__main__":
    test_vertical_layout()
    test_grid_layout()