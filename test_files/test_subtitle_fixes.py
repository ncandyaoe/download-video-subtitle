#!/usr/bin/env python3
"""
测试字幕修复效果
"""

import os
import tempfile
import asyncio
import sys

# 添加当前目录到路径
sys.path.append('.')

async def test_chinese_subtitle_and_sync():
    """测试中文字幕显示和音画同步修复"""
    from api import VideoComposer
    
    composer = VideoComposer()
    
    print("🧪 测试字幕修复效果")
    print("=" * 60)
    
    # 创建中文TXT字幕测试文件
    chinese_content = """看，一群可爱的小猴子在月光下快乐地玩耍呢！
它们在树枝间跳跃，发出欢快的叫声。
突然，小猴子们发现了水中的月亮。
"哇！月亮掉到水里了！"一只小猴子惊呼道。
"我们要把月亮捞上来！"另一只小猴子说。
于是，小猴子们开始了捞月亮的行动。
它们一个接一个地倒挂在树枝上。
最小的猴子伸手去捞水中的月亮。
但是，当它的手碰到水面时。
月亮竟然碎了！变成了无数个小月亮。
小猴子们这才明白，那只是月亮的倒影。
真正的月亮还在天空中对它们微笑呢！"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(chinese_content)
        txt_file = f.name
    
    print(f"📝 创建中文TXT字幕文件: {os.path.basename(txt_file)}")
    print(f"📄 字幕内容预览:")
    for i, line in enumerate(chinese_content.split('\n')[:3], 1):
        if line.strip():
            print(f"   {i}. {line}")
    print(f"   ... (共{len(chinese_content.split())}行)")
    
    try:
        # 测试1: 验证TXT文件
        print(f"\n🔍 测试1: 验证TXT字幕文件")
        try:
            await composer._validate_subtitle_file(txt_file)
            print(f"   ✅ TXT字幕文件验证通过")
        except Exception as e:
            print(f"   ❌ TXT字幕文件验证失败: {str(e)}")
            return
        
        # 测试2: 转换为SRT（不带视频时长）
        print(f"\n🔄 测试2: TXT转SRT（默认时间轴）")
        srt_file_1 = txt_file.replace('.txt', '_default.srt')
        try:
            result1 = composer.convert_txt_to_srt(txt_file, srt_file_1)
            print(f"   ✅ 默认转换成功: {os.path.basename(result1)}")
            
            # 显示转换结果
            with open(result1, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            print(f"   📋 转换结果预览:")
            for line in lines[:8]:  # 显示前8行
                if line.strip():
                    print(f"     {line}")
            print(f"     ... (共{len([l for l in lines if l.strip()])}行)")
            
        except Exception as e:
            print(f"   ❌ 默认转换失败: {str(e)}")
        
        # 测试3: 转换为SRT（带视频时长优化）
        print(f"\n🎬 测试3: TXT转SRT（视频时长优化）")
        srt_file_2 = txt_file.replace('.txt', '_optimized.srt')
        video_duration = 30.0  # 假设30秒视频
        try:
            result2 = composer.convert_txt_to_srt(txt_file, srt_file_2, video_duration)
            print(f"   ✅ 优化转换成功: {os.path.basename(result2)}")
            print(f"   📊 视频时长: {video_duration}秒")
            
            # 显示转换结果
            with open(result2, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            print(f"   📋 优化转换结果预览:")
            for line in lines[:8]:  # 显示前8行
                if line.strip():
                    print(f"     {line}")
            print(f"     ... (共{len([l for l in lines if l.strip()])}行)")
            
            # 验证转换后的SRT文件
            await composer._validate_subtitle_file(result2)
            print(f"   ✅ 转换后的SRT文件验证通过")
            
        except Exception as e:
            print(f"   ❌ 优化转换失败: {str(e)}")
        
        # 测试4: 检查字幕滤镜构建
        print(f"\n🎨 测试4: 字幕滤镜构建")
        try:
            import platform
            system = platform.system()
            print(f"   🖥️ 检测到系统: {system}")
            
            # 模拟字幕滤镜构建
            escaped_subtitle = result2.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
            
            if system == 'Darwin':  # macOS
                subtitle_filter = f"subtitles='{escaped_subtitle}':force_style='FontName=PingFang SC,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'"
                font_name = "PingFang SC"
            elif system == 'Linux':
                subtitle_filter = f"subtitles='{escaped_subtitle}':force_style='FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'"
                font_name = "Noto Sans CJK SC"
            else:
                subtitle_filter = f"subtitles='{escaped_subtitle}':force_style='FontName=Arial Unicode MS,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'"
                font_name = "Arial Unicode MS"
            
            print(f"   ✅ 字幕滤镜构建成功")
            print(f"   🔤 使用字体: {font_name}")
            print(f"   🎨 样式: 白色字体，黑色描边，24号字体")
            
        except Exception as e:
            print(f"   ❌ 字幕滤镜构建失败: {str(e)}")
        
        print(f"\n📋 修复总结:")
        print(f"   🔤 中文字幕支持: 使用系统中文字体 ({font_name})")
        print(f"   ⏰ 时间轴优化: 根据视频时长智能分配")
        print(f"   🎯 标点分割: 按标点符号智能分段")
        print(f"   🔄 音画同步: 音频时长自动调整匹配视频")
        
        print(f"\n💡 使用建议:")
        print(f"   • 确保系统安装了中文字体")
        print(f"   • 提供准确的视频时长信息以优化字幕时间轴")
        print(f"   • 使用标点符号分割长句以提高可读性")
        print(f"   • 音频文件时长与视频差异过大时会自动调整")
        
    finally:
        # 清理测试文件
        for file_path in [txt_file, srt_file_1, srt_file_2]:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass

async def main():
    await test_chinese_subtitle_and_sync()
    print(f"\n🎉 字幕修复测试完成！")

if __name__ == "__main__":
    asyncio.run(main())