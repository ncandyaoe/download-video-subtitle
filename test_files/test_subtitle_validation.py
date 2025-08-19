#!/usr/bin/env python3
"""
测试字幕文件验证功能
"""

import os
import tempfile
import asyncio
import sys

# 添加当前目录到路径
sys.path.append('.')

async def test_subtitle_validation():
    """测试字幕文件验证功能"""
    from api import VideoComposer
    
    composer = VideoComposer()
    
    print("🧪 测试字幕文件验证功能")
    print("=" * 50)
    
    # 测试支持的格式
    test_files = {}
    
    # 创建TXT测试文件
    txt_content = "这是一个测试字幕文件。\n包含多行内容。"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(txt_content)
        test_files['txt'] = f.name
    
    # 创建SRT测试文件
    srt_content = """1
00:00:00,000 --> 00:00:03,000
测试SRT字幕

2
00:00:03,000 --> 00:00:06,000
第二行字幕
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
        f.write(srt_content)
        test_files['srt'] = f.name
    
    # 创建不支持的格式
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False, encoding='utf-8') as f:
        f.write("不支持的格式")
        test_files['xyz'] = f.name
    
    # 创建空TXT文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("")
        test_files['empty_txt'] = f.name
    
    try:
        # 测试各种格式
        for format_name, file_path in test_files.items():
            print(f"\n📝 测试 {format_name.upper()} 格式: {os.path.basename(file_path)}")
            
            try:
                await composer._validate_subtitle_file(file_path)
                print(f"   ✅ 验证通过")
            except Exception as e:
                print(f"   ❌ 验证失败: {str(e)}")
        
        # 测试不存在的文件
        print(f"\n📝 测试不存在的文件")
        try:
            await composer._validate_subtitle_file("/path/to/nonexistent/file.srt")
            print(f"   ❌ 应该失败但通过了")
        except Exception as e:
            print(f"   ✅ 正确拒绝: {str(e)}")
        
        print(f"\n🔄 测试TXT到SRT转换")
        srt_output = test_files['txt'].replace('.txt', '_converted.srt')
        try:
            result = composer.convert_txt_to_srt(test_files['txt'], srt_output)
            print(f"   ✅ 转换成功: {os.path.basename(result)}")
            
            # 验证转换后的文件
            await composer._validate_subtitle_file(result)
            print(f"   ✅ 转换后的SRT文件验证通过")
            
            # 显示转换结果
            with open(result, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   转换结果预览:")
            for line in content.split('\n')[:6]:  # 显示前6行
                if line.strip():
                    print(f"     {line}")
            
        except Exception as e:
            print(f"   ❌ 转换失败: {str(e)}")
    
    finally:
        # 清理测试文件
        for file_path in test_files.values():
            try:
                os.unlink(file_path)
            except:
                pass
        
        # 清理转换后的文件
        srt_output = test_files['txt'].replace('.txt', '_converted.srt')
        try:
            os.unlink(srt_output)
        except:
            pass

async def main():
    await test_subtitle_validation()
    print(f"\n🎉 字幕验证测试完成！")

if __name__ == "__main__":
    asyncio.run(main())