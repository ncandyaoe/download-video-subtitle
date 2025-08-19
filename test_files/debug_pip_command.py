#!/usr/bin/env python3
"""
调试画中画FFmpeg命令构建
"""

import sys
import os
sys.path.append('.')

from api import FFmpegCommandBuilder, Position

def test_pip_command_building():
    """测试画中画FFmpeg命令构建"""
    print("🔧 测试画中画FFmpeg命令构建")
    
    # 模拟文件路径
    main_video = "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4"
    overlay_video = "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4"
    output_file = "./compositions/test_pip_output.mp4"
    
    # 模拟布局信息
    layout = {
        'x': 50,
        'y': 50,
        'overlay_width': 320,
        'overlay_height': 180,
        'needs_scaling': True,
        'opacity': 0.8
    }
    
    # 构建FFmpeg命令
    builder = FFmpegCommandBuilder()
    
    # 添加主视频输入
    builder.add_input(main_video)
    
    # 添加叠加视频输入
    builder.add_input(overlay_video)
    
    # 构建滤镜链
    filters = []
    
    # 缩放叠加视频
    if layout['needs_scaling']:
        scale_filter = f"[1:v]scale={layout['overlay_width']}:{layout['overlay_height']}[scaled]"
        filters.append(scale_filter)
        overlay_stream = "[scaled]"
    else:
        overlay_stream = "[1:v]"
    
    # 画中画叠加滤镜
    overlay_filter = f"[0:v]{overlay_stream}overlay={layout['x']}:{layout['y']}"
    if layout['opacity'] < 1.0:
        # 添加透明度
        opacity_filter = f"{overlay_stream}format=yuva420p,colorchannelmixer=aa={layout['opacity']}[overlay_alpha]"
        filters.append(opacity_filter)
        overlay_filter = f"[0:v][overlay_alpha]overlay={layout['x']}:{layout['y']}"
    
    filters.append(overlay_filter + "[pip_output]")
    
    # 添加滤镜到构建器
    for filter_str in filters:
        builder.add_filter(filter_str)
    
    # 输出选项
    output_options = {
        'c:v': 'libx264',
        'c:a': 'copy',  # 复制主视频的音频
        'b:v': '2M'
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
    cmd.insert(output_file_index + 1, '[pip_output]')
    cmd.insert(output_file_index + 2, '-map')
    cmd.insert(output_file_index + 3, '0:a')  # 使用主视频的音频
    
    print("✅ 最终命令:")
    print(" ".join(cmd))
    print()
    
    # 验证命令
    if builder.validate_command(cmd):
        print("✅ 命令验证通过")
    else:
        print("❌ 命令验证失败")
    
    # 检查输出文件是否在命令中
    if output_file in cmd:
        print(f"✅ 输出文件正确: {output_file}")
    else:
        print("❌ 输出文件丢失!")
        print(f"期望: {output_file}")
        print(f"命令: {cmd}")
    
    # 分析滤镜
    print("\n🔍 滤镜分析:")
    for i, filter_str in enumerate(filters):
        print(f"  {i+1}. {filter_str}")

if __name__ == "__main__":
    test_pip_command_building()