#!/usr/bin/env python3
"""
TXT字幕格式使用示例
"""

import requests
import json
import time
import tempfile
import os

def create_sample_txt_subtitle():
    """创建示例TXT字幕文件"""
    content = """欢迎来到视频处理API演示！
这是一个支持TXT格式字幕的示例。
您可以直接使用纯文本文件作为字幕。
系统会自动将其转换为SRT格式。
每行文本会根据标点符号智能分割。
感谢您的使用！"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name

def demo_txt_subtitle_composition():
    """演示TXT字幕合成功能"""
    print("🎬 TXT字幕格式使用演示")
    print("=" * 50)
    
    # 创建示例TXT字幕文件
    txt_subtitle = create_sample_txt_subtitle()
    print(f"📝 创建示例TXT字幕文件: {os.path.basename(txt_subtitle)}")
    
    # 显示TXT内容
    with open(txt_subtitle, 'r', encoding='utf-8') as f:
        content = f.read()
    print("📄 TXT字幕内容:")
    for i, line in enumerate(content.split('\n'), 1):
        if line.strip():
            print(f"   {i}. {line}")
    
    print(f"\n🚀 发送视频合成请求...")
    
    # 构建请求数据
    request_data = {
        "composition_type": "audio_video_subtitle",
        "videos": [
            {
                "video_url": "/path/to/your/video.mp4"  # 请替换为实际视频路径
            }
        ],
        "audio_file": "/path/to/your/audio.mp3",  # 请替换为实际音频路径
        "subtitle_file": txt_subtitle,  # 使用TXT格式字幕
        "output_format": "mp4",
        "subtitle_settings": {
            "font_size": 24,
            "font_color": "white",
            "background_color": "black"
        }
    }
    
    print("📋 请求参数:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        # 发送请求（注意：这里只是演示，实际使用时需要有效的视频和音频文件）
        print(f"\n💡 使用示例:")
        print(f"curl -X POST \"http://localhost:7878/compose_video\" \\")
        print(f"-H \"Content-Type: application/json\" \\")
        print(f"-d '{json.dumps(request_data, ensure_ascii=False)}'")
        
        print(f"\n✨ TXT字幕的优势:")
        print(f"   • 📝 简单易用 - 直接编写纯文本")
        print(f"   • 🔄 自动转换 - 无需手动制作SRT")
        print(f"   • ⏰ 智能时间轴 - 根据文本长度自动分配")
        print(f"   • 🎯 标点分割 - 按标点符号智能分段")
        
        print(f"\n📋 支持的字幕格式:")
        formats = [
            ("SRT", ".srt", "SubRip字幕格式", "直接使用"),
            ("TXT", ".txt", "纯文本格式", "自动转换为SRT"),
            ("ASS", ".ass", "Advanced SubStation Alpha", "直接使用"),
            ("SSA", ".ssa", "SubStation Alpha", "直接使用"),
            ("VTT", ".vtt", "WebVTT字幕格式", "直接使用")
        ]
        
        for name, ext, desc, process in formats:
            print(f"   • {name:3} ({ext:4}) - {desc:25} - {process}")
        
    finally:
        # 清理示例文件
        try:
            os.unlink(txt_subtitle)
            print(f"\n🧹 清理示例文件完成")
        except:
            pass

if __name__ == "__main__":
    demo_txt_subtitle_composition()