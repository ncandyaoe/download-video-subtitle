#!/usr/bin/env python3
"""
检查系统中文字体路径的工具
"""

import os
import platform
import subprocess
from pathlib import Path

def check_macos_fonts():
    """检查macOS系统字体"""
    font_paths = []
    
    # macOS系统字体路径
    system_font_dirs = [
        '/System/Library/Fonts',
        '/Library/Fonts',
        '~/Library/Fonts'
    ]
    
    # 常见中文字体文件名
    chinese_fonts = [
        'PingFang.ttc',
        'PingFangSC-Regular.otf',
        'PingFangSC-Medium.otf',
        'Hiragino Sans GB.ttc',
        'STHeiti Light.ttc',
        'STHeiti Medium.ttc',
        'Arial Unicode.ttf'
    ]
    
    print("🔍 检查macOS中文字体...")
    
    for font_dir in system_font_dirs:
        expanded_dir = os.path.expanduser(font_dir)
        if os.path.exists(expanded_dir):
            print(f"\n📁 检查目录: {expanded_dir}")
            
            for font_file in chinese_fonts:
                font_path = os.path.join(expanded_dir, font_file)
                if os.path.exists(font_path):
                    font_paths.append(font_path)
                    print(f"   ✅ 找到: {font_file}")
                else:
                    print(f"   ❌ 未找到: {font_file}")
    
    # 使用fc-list命令查找字体（如果可用）
    try:
        result = subprocess.run(['fc-list', ':lang=zh'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"\n🔍 fc-list找到的中文字体:")
            for line in result.stdout.strip().split('\n')[:10]:  # 只显示前10个
                if line.strip():
                    print(f"   • {line}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("\n⚠️  fc-list命令不可用")
    
    return font_paths

def check_linux_fonts():
    """检查Linux系统字体"""
    font_paths = []
    
    # Linux系统字体路径
    system_font_dirs = [
        '/usr/share/fonts',
        '/usr/local/share/fonts',
        '~/.fonts',
        '~/.local/share/fonts'
    ]
    
    print("🔍 检查Linux中文字体...")
    
    for font_dir in system_font_dirs:
        expanded_dir = os.path.expanduser(font_dir)
        if os.path.exists(expanded_dir):
            print(f"\n📁 检查目录: {expanded_dir}")
            
            # 递归查找中文字体
            for root, dirs, files in os.walk(expanded_dir):
                for file in files:
                    if any(keyword in file.lower() for keyword in ['noto', 'cjk', 'chinese', 'han']):
                        font_path = os.path.join(root, file)
                        font_paths.append(font_path)
                        print(f"   ✅ 找到: {file}")
    
    return font_paths

def check_windows_fonts():
    """检查Windows系统字体"""
    font_paths = []
    
    # Windows系统字体路径
    windows_font_dir = 'C:\\Windows\\Fonts'
    
    chinese_fonts = [
        'msyh.ttc',      # Microsoft YaHei
        'msyhbd.ttc',    # Microsoft YaHei Bold
        'simsun.ttc',    # SimSun
        'simhei.ttf',    # SimHei
        'ARIALUNI.TTF'   # Arial Unicode MS
    ]
    
    print("🔍 检查Windows中文字体...")
    
    if os.path.exists(windows_font_dir):
        print(f"\n📁 检查目录: {windows_font_dir}")
        
        for font_file in chinese_fonts:
            font_path = os.path.join(windows_font_dir, font_file)
            if os.path.exists(font_path):
                font_paths.append(font_path)
                print(f"   ✅ 找到: {font_file}")
            else:
                print(f"   ❌ 未找到: {font_file}")
    
    return font_paths

def get_recommended_font_path():
    """获取推荐的字体路径"""
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        # 优先级顺序的字体路径
        candidates = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf'
        ]
        
        for font_path in candidates:
            if os.path.exists(font_path):
                return font_path
                
    elif system == 'Linux':
        # 查找Noto字体
        possible_paths = [
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
        ]
        
        for font_path in possible_paths:
            if os.path.exists(font_path):
                return font_path
                
    elif system == 'Windows':
        # Windows字体
        candidates = [
            'C:\\Windows\\Fonts\\msyh.ttc',
            'C:\\Windows\\Fonts\\ARIALUNI.TTF'
        ]
        
        for font_path in candidates:
            if os.path.exists(font_path):
                return font_path
    
    return None

def main():
    """主函数"""
    print("🎨 系统中文字体路径检查工具")
    print("=" * 50)
    
    system = platform.system()
    print(f"🖥️  操作系统: {system}")
    
    font_paths = []
    
    if system == 'Darwin':
        font_paths = check_macos_fonts()
    elif system == 'Linux':
        font_paths = check_linux_fonts()
    elif system == 'Windows':
        font_paths = check_windows_fonts()
    else:
        print(f"⚠️  不支持的操作系统: {system}")
        return
    
    print(f"\n📊 总结:")
    print(f"   找到 {len(font_paths)} 个中文字体文件")
    
    # 获取推荐字体路径
    recommended_path = get_recommended_font_path()
    if recommended_path:
        print(f"\n🎯 推荐使用的字体路径:")
        print(f"   {recommended_path}")
        
        # 生成FFmpeg字幕滤镜示例
        print(f"\n💡 FFmpeg字幕滤镜示例:")
        escaped_path = recommended_path.replace('\\', '\\\\').replace(':', '\\:')
        print(f"   subtitles='subtitle.srt':force_style='FontFile={escaped_path},FontSize=24'")
    else:
        print(f"\n⚠️  未找到推荐的字体路径")
        print(f"   建议使用字体名称而不是文件路径")

if __name__ == "__main__":
    main()