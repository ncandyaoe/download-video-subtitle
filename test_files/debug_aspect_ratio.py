#!/usr/bin/env python3
"""
调试宽高比保持功能的FFmpeg命令
"""

import sys
import os
sys.path.append('.')

# 导入API中的类
from api import FFmpegCommandBuilder, VideoInfo, video_validator

async def debug_aspect_ratio_command():
    """调试宽高比保持的FFmpeg命令"""
    print("🔍 调试宽高比保持的FFmpeg命令")
    
    video1 = "downloads/test_16_9.mp4"      # 16:9 视频
    video2 = "downloads/test_video_4_3.mp4" # 4:3 视频
    
    if not os.path.exists(video1) or not os.path.exists(video2):
        print("❌ 测试视频文件不存在")
        return
    
    # 获取视频信息
    print("📊 获取视频信息...")
    video_info1 = await video_validator.validate_video_file(video1)
    video_info2 = await video_validator.validate_video_file(video2)
    
    print(f"视频1: {video_info1.width}x{video_info1.height} (宽高比: {video_info1.width/video_info1.height:.2f})")
    print(f"视频2: {video_info2.width}x{video_info2.height} (宽高比: {video_info2.width/video_info2.height:.2f})")
    
    # 计算网格布局
    video_infos = [video_info1, video_info2]
    widths = [info.width for info in video_infos]
    heights = [info.height for info in video_infos]
    
    max_width = max(widths)
    max_height = max(heights)
    base_width = max_width
    base_height = max_height
    
    # 水平布局
    cell_width = base_width // 2
    cell_height = base_height
    output_width = cell_width * 2
    output_height = cell_height
    
    # 确保尺寸是偶数
    cell_width = cell_width - (cell_width % 2)
    cell_height = cell_height - (cell_height % 2)
    output_width = output_width - (output_width % 2)
    output_height = output_height - (output_height % 2)
    
    print(f"\n📐 布局计算:")
    print(f"单元格尺寸: {cell_width}x{cell_height}")
    print(f"输出尺寸: {output_width}x{output_height}")
    
    # 构建FFmpeg命令
    print(f"\n🔧 构建FFmpeg命令:")
    builder = FFmpegCommandBuilder()
    
    # 添加输入
    builder.add_input(video1)
    builder.add_input(video2)
    
    # 构建滤镜
    filters = []
    
    # 缩放并保持宽高比，然后填充
    for i in range(2):
        scale_filter = f"[{i}:v]scale={cell_width}:{cell_height}:force_original_aspect_ratio=decrease[scaled_temp_{i}]"
        pad_filter = f"[scaled_temp_{i}]pad={cell_width}:{cell_height}:(ow-iw)/2:(oh-ih)/2:color=black[scaled_{i}]"
        filters.extend([scale_filter, pad_filter])
    
    # 水平并排
    hstack_filter = "[scaled_0][scaled_1]hstack=inputs=2[output]"
    filters.append(hstack_filter)
    
    # 添加滤镜
    for filter_str in filters:
        builder.add_filter(filter_str)
        print(f"  滤镜: {filter_str}")
    
    # 输出选项
    output_file = "debug_aspect_ratio_output.mp4"
    output_options = {
        'c:v': 'libx264',
        'c:a': 'copy',
        'b:v': '3M'
    }
    
    builder.add_output(output_file, output_options)
    
    # 构建命令
    cmd = builder.build()
    
    # 添加映射
    output_file_index = cmd.index(output_file)
    cmd.insert(output_file_index, '-map')
    cmd.insert(output_file_index + 1, '[output]')
    cmd.insert(output_file_index + 2, '-map')
    cmd.insert(output_file_index + 3, '1:a')  # 使用第二个视频的音频
    
    print(f"\n💻 完整FFmpeg命令:")
    print(' '.join(cmd))
    
    print(f"\n📝 命令解释:")
    print("1. scale滤镜使用force_original_aspect_ratio=decrease保持宽高比")
    print("2. pad滤镜将视频居中并用黑色填充到目标尺寸")
    print("3. hstack滤镜将两个视频水平并排")
    print("4. 这样可以避免视频拉伸变形")

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_aspect_ratio_command())