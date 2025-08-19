#!/usr/bin/env python3
"""
调试音频偏移问题
"""

import subprocess
import json
import os

def analyze_audio_file(audio_file):
    """分析音频文件的详细信息"""
    print(f"🔍 分析音频文件: {audio_file}")
    print("=" * 60)
    
    if not os.path.exists(audio_file):
        print(f"❌ 文件不存在: {audio_file}")
        return
    
    try:
        # 使用ffprobe获取详细信息
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", audio_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ ffprobe执行失败: {result.stderr}")
            return
        
        info = json.loads(result.stdout)
        
        # 分析格式信息
        format_info = info.get('format', {})
        print(f"📊 格式信息:")
        print(f"   文件名: {format_info.get('filename', 'N/A')}")
        print(f"   格式: {format_info.get('format_name', 'N/A')}")
        print(f"   时长: {float(format_info.get('duration', 0)):.3f}秒")
        print(f"   开始时间: {float(format_info.get('start_time', 0)):.3f}秒")  # 关键！
        print(f"   比特率: {format_info.get('bit_rate', 'N/A')}")
        
        # 分析流信息
        streams = info.get('streams', [])
        for i, stream in enumerate(streams):
            if stream.get('codec_type') == 'audio':
                print(f"\n🎵 音频流 {i}:")
                print(f"   编码器: {stream.get('codec_name', 'N/A')}")
                print(f"   时长: {float(stream.get('duration', 0)):.3f}秒")
                print(f"   开始时间: {float(stream.get('start_time', 0)):.3f}秒")  # 关键！
                print(f"   采样率: {stream.get('sample_rate', 'N/A')} Hz")
                print(f"   声道数: {stream.get('channels', 'N/A')}")
                print(f"   比特率: {stream.get('bit_rate', 'N/A')}")
                
                # 检查是否有起始偏移
                start_time = float(stream.get('start_time', 0))
                if start_time > 0:
                    print(f"   ⚠️  检测到音频起始偏移: {start_time:.3f}秒")
                else:
                    print(f"   ✅ 音频从0秒开始")
        
        # 检查元数据
        metadata = format_info.get('tags', {})
        if metadata:
            print(f"\n📝 元数据:")
            for key, value in metadata.items():
                print(f"   {key}: {value}")
        
        return info
        
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")
        return None

def test_subtitle_timing():
    """测试字幕时间分配"""
    print(f"\n🕐 测试字幕时间分配")
    print("=" * 60)
    
    # 模拟字幕内容
    subtitle_lines = [
        "第一段：欢迎收听我们的音频内容",
        "第二段：今天我们要讲述一个有趣的故事", 
        "第三段：故事发生在一个美丽的春天"
    ]
    
    # 假设音频时长
    audio_duration = 10.0  # 10秒
    
    print(f"📊 测试参数:")
    print(f"   音频时长: {audio_duration}秒")
    print(f"   字幕行数: {len(subtitle_lines)}")
    
    # 模拟当前的时间分配算法
    total_chars = sum(len(line) for line in subtitle_lines)
    time_per_char = min(audio_duration * 0.9 / total_chars, 0.3)
    
    print(f"\n🔢 时间分配计算:")
    print(f"   总字符数: {total_chars}")
    print(f"   每字符时间: {time_per_char:.3f}秒")
    
    current_time = 0.0
    for i, line in enumerate(subtitle_lines):
        duration = max(1.5, min(6.0, len(line) * time_per_char + 0.5))
        end_time = current_time + duration
        
        print(f"\n📝 字幕 {i+1}:")
        print(f"   内容: {line}")
        print(f"   字符数: {len(line)}")
        print(f"   开始时间: {current_time:.3f}秒")
        print(f"   结束时间: {end_time:.3f}秒")
        print(f"   持续时间: {duration:.3f}秒")
        
        current_time = end_time
    
    print(f"\n📊 总结:")
    print(f"   字幕总时长: {current_time:.3f}秒")
    print(f"   音频时长: {audio_duration:.3f}秒")
    print(f"   时长差异: {abs(current_time - audio_duration):.3f}秒")

def main():
    """主函数"""
    print("🔍 音频偏移问题调试工具")
    print("=" * 60)
    
    # 分析测试音频文件
    audio_file = "test_audio/test_bilibili_auto.mp4"
    
    if os.path.exists(audio_file):
        audio_info = analyze_audio_file(audio_file)
        
        if audio_info:
            # 检查是否有起始时间偏移
            format_start_time = float(audio_info.get('format', {}).get('start_time', 0))
            
            audio_streams = [s for s in audio_info.get('streams', []) 
                           if s.get('codec_type') == 'audio']
            
            if audio_streams:
                stream_start_time = float(audio_streams[0].get('start_time', 0))
                
                print(f"\n🎯 偏移分析:")
                print(f"   格式起始时间: {format_start_time:.3f}秒")
                print(f"   音频流起始时间: {stream_start_time:.3f}秒")
                
                if format_start_time > 0 or stream_start_time > 0:
                    print(f"   ⚠️  发现音频起始偏移!")
                    print(f"   💡 建议: 在FFmpeg命令中添加 -ss 0 参数")
                else:
                    print(f"   ✅ 音频没有起始偏移")
    else:
        print(f"❌ 测试音频文件不存在: {audio_file}")
    
    # 测试字幕时间分配
    test_subtitle_timing()
    
    print(f"\n💡 可能的解决方案:")
    print(f"   1. 检查音频文件是否有起始时间偏移")
    print(f"   2. 在FFmpeg命令中添加 -ss 0 确保从0秒开始")
    print(f"   3. 调整字幕起始时间，添加1秒延迟")
    print(f"   4. 使用 -avoid_negative_ts make_zero 参数")

if __name__ == "__main__":
    main()