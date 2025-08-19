#!/usr/bin/env python3
"""
调试FFmpeg命令构建
"""

import sys
import os
sys.path.append('.')

from api import FFmpegCommandBuilder

def test_command_building():
    """测试FFmpeg命令构建"""
    print("🔧 测试FFmpeg命令构建")
    
    # 模拟文件路径
    video_file = "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test_bilibili_auto.mp4"
    audio_file = "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/test.mp3"
    subtitle_file = "/Users/mulele/Projects/3-video_download/download-video-subtitle-all/output/gWNFna6fgS8.srt"
    output_file = "./compositions/test_output.mp4"
    
    # 构建FFmpeg命令
    builder = FFmpegCommandBuilder()
    
    # 添加视频输入
    builder.add_input(video_file)
    
    # 添加音频输入
    builder.add_input(audio_file)
    
    # 构建滤镜链
    filters = []
    
    # 如果有字幕文件，添加字幕滤镜
    if subtitle_file:
        # 转义字幕文件路径中的特殊字符
        escaped_subtitle = subtitle_file.replace('\\', '\\\\').replace(':', '\\:')
        subtitle_filter = f"subtitles='{escaped_subtitle}'"
        filters.append(f"[0:v]{subtitle_filter}[v_with_sub]")
        video_stream = "[v_with_sub]"
    else:
        video_stream = "[0:v]"
    
    # 添加滤镜到构建器
    if filters:
        for filter_str in filters:
            builder.add_filter(filter_str)
    
    # 输出选项
    output_options = {
        'c:v': 'libx264',      # 视频编码器
        'c:a': 'aac',          # 音频编码器
        'b:v': '2M',           # 视频比特率
        'b:a': '128k',         # 音频比特率
        'ar': '48000'          # 音频采样率
    }
    
    builder.add_output(output_file, output_options)
    
    # 构建命令
    cmd = builder.build()
    
    print("📝 基础命令:")
    print(" ".join(cmd))
    print()
    
    # 手动添加映射选项和其他选项
    output_file_index = cmd.index(output_file)
    
    # 添加-shortest选项
    cmd.insert(output_file_index, '-shortest')
    output_file_index += 1  # 更新索引
    
    if subtitle_file and filters:
        # 有字幕时使用滤镜输出的视频流
        cmd.insert(output_file_index, '-map')
        cmd.insert(output_file_index + 1, video_stream)
        cmd.insert(output_file_index + 2, '-map')
        cmd.insert(output_file_index + 3, '1:a:0')
    else:
        # 无字幕时直接映射原始流
        cmd.insert(output_file_index, '-map')
        cmd.insert(output_file_index + 1, '0:v:0')
        cmd.insert(output_file_index + 2, '-map')
        cmd.insert(output_file_index + 3, '1:a:0')
    
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

if __name__ == "__main__":
    test_command_building()