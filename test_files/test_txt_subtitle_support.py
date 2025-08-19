#!/usr/bin/env python3
"""
测试TXT字幕格式支持
"""

import os
import tempfile
import requests
import json
import time

def create_test_txt_subtitle():
    """创建测试用的TXT字幕文件"""
    content = """看，一群可爱的小猴子在月光下快乐地玩耍呢！
它们在树枝间跳跃，发出欢快的叫声。
突然，小猴子们发现了水中的月亮。
"哇！月亮掉到水里了！"一只小猴子惊呼道。
"我们要把月亮捞上来！"另一只小猴子说。
于是，小猴子们开始了捞月亮的行动。"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name

def test_txt_subtitle_validation():
    """测试TXT字幕文件验证"""
    print("🧪 测试TXT字幕文件验证...")
    
    # 创建测试TXT文件
    txt_file = create_test_txt_subtitle()
    print(f"   创建测试TXT文件: {txt_file}")
    
    try:
        # 测试视频合成请求
        test_data = {
            "composition_type": "audio_video_subtitle",
            "videos": [
                {
                    "video_url": "/Users/mulele/Documents/4-n8ndata/video/猴子捞月/monkey_story.mp4"
                }
            ],
            "audio_file": "/Users/mulele/Documents/4-n8ndata/video/猴子捞月/monkey_story.mp3",
            "subtitle_file": txt_file,
            "output_format": "mp4"
        }
        
        print("   发送合成请求...")
        response = requests.post(
            "http://localhost:7878/compose_video",
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"   ✅ 请求成功，任务ID: {task_id}")
            
            # 检查任务状态
            print("   检查任务状态...")
            for i in range(10):  # 最多检查10次
                status_response = requests.get(f"http://localhost:7878/composition_status/{task_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"   状态: {status.get('status')} - {status.get('message')} ({status.get('progress', 0)}%)")
                    
                    if status.get('status') == 'completed':
                        print("   ✅ TXT字幕合成成功！")
                        return True
                    elif status.get('status') == 'failed':
                        print(f"   ❌ 合成失败: {status.get('error', '未知错误')}")
                        return False
                
                time.sleep(5)
            
            print("   ⏰ 任务超时")
            return False
            
        else:
            print(f"   ❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"   💥 测试异常: {str(e)}")
        return False
    finally:
        # 清理测试文件
        try:
            os.unlink(txt_file)
        except:
            pass

def test_txt_to_srt_conversion():
    """测试TXT到SRT转换功能"""
    print("🔄 测试TXT到SRT转换...")
    
    # 创建测试TXT文件
    txt_content = """第一行字幕内容。
第二行字幕内容！
第三行字幕内容？"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_f:
        txt_f.write(txt_content)
        txt_file = txt_f.name
    
    try:
        # 导入VideoComposer进行测试
        import sys
        sys.path.append('.')
        from api import VideoComposer
        
        composer = VideoComposer()
        
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as srt_f:
            srt_file = srt_f.name
        
        # 执行转换
        result_file = composer.convert_txt_to_srt(txt_file, srt_file)
        
        # 检查结果
        with open(result_file, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        print("   转换结果:")
        print("   " + "="*50)
        for line in srt_content.split('\n'):
            if line.strip():
                print(f"   {line}")
        print("   " + "="*50)
        
        # 验证SRT格式
        if "00:00:00,000 --> " in srt_content and "1\n" in srt_content:
            print("   ✅ TXT到SRT转换成功！")
            return True
        else:
            print("   ❌ SRT格式不正确")
            return False
            
    except Exception as e:
        print(f"   💥 转换测试异常: {str(e)}")
        return False
    finally:
        # 清理测试文件
        try:
            os.unlink(txt_file)
            os.unlink(srt_file)
        except:
            pass

def main():
    print("🚀 TXT字幕格式支持测试")
    print("=" * 60)
    
    # 测试转换功能
    conversion_success = test_txt_to_srt_conversion()
    
    print()
    
    # 测试完整的字幕验证和合成
    validation_success = test_txt_subtitle_validation()
    
    print()
    print("=" * 60)
    print("📋 测试总结:")
    print(f"   TXT到SRT转换: {'✅ 通过' if conversion_success else '❌ 失败'}")
    print(f"   TXT字幕合成: {'✅ 通过' if validation_success else '❌ 失败'}")
    
    if conversion_success and validation_success:
        print("🎉 所有测试通过！TXT字幕格式支持已成功添加。")
    else:
        print("⚠️ 部分测试失败，请检查实现。")

if __name__ == "__main__":
    main()