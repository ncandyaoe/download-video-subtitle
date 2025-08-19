#!/usr/bin/env python3
"""
测试中文字幕显示
"""

import requests
import json
import time
import tempfile
import os

def create_chinese_subtitle():
    """创建中文字幕测试文件"""
    content = """你好世界！这是中文字幕测试。
欢迎使用视频处理API。
中文字幕应该能正常显示。"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name

def test_chinese_subtitle():
    """测试中文字幕显示"""
    print("🔤 测试中文字幕显示")
    print("=" * 40)
    
    txt_file = create_chinese_subtitle()
    print(f"📝 创建中文字幕文件: {os.path.basename(txt_file)}")
    
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"📄 字幕内容: {content}")
    
    # 构建请求
    request_data = {
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
    
    try:
        print("🚀 发送请求...")
        response = requests.post(
            "http://localhost:7878/compose_video",
            headers={"Content-Type": "application/json"},
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"✅ 任务创建成功: {task_id}")
            
            # 监控任务进度
            for i in range(24):  # 等待2分钟
                time.sleep(5)
                
                try:
                    status_response = requests.get(f"http://localhost:7878/composition_status/{task_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        current_status = status.get('status')
                        progress = status.get('progress', 0)
                        message = status.get('message', '')
                        
                        print(f"📊 {i*5}s - 状态: {current_status}, 进度: {progress}%, 消息: {message}")
                        
                        if current_status == 'completed':
                            print("🎉 合成成功！")
                            
                            # 获取结果
                            result_response = requests.get(f"http://localhost:7878/composition_result/{task_id}")
                            if result_response.status_code == 200:
                                result_data = result_response.json()
                                result_info = result_data.get('result', {})
                                output_file = result_info.get('output_file_path', 'N/A')
                                
                                print(f"📁 输出文件: {output_file}")
                                print(f"⏱️ 处理时间: {result_info.get('processing_time', 'N/A')}")
                                
                                # 检查文件是否存在
                                if output_file != 'N/A' and os.path.exists(output_file):
                                    file_size = os.path.getsize(output_file)
                                    print(f"📊 文件大小: {file_size / 1024 / 1024:.1f}MB")
                                    print(f"✅ 视频文件生成成功，请检查中文字幕是否正常显示")
                                    
                                    # 提供播放建议
                                    print(f"\n💡 测试建议:")
                                    print(f"   1. 使用视频播放器打开: {output_file}")
                                    print(f"   2. 检查中文字幕是否清晰可见")
                                    print(f"   3. 确认字体渲染是否正常")
                                    
                                    return True
                                else:
                                    print(f"❌ 输出文件不存在: {output_file}")
                                    return False
                            else:
                                print(f"❌ 获取结果失败: {result_response.status_code}")
                                return False
                                
                        elif current_status == 'failed':
                            error_msg = status.get('error', '未知错误')
                            print(f"❌ 合成失败: {error_msg}")
                            return False
                    else:
                        print(f"⚠️ 状态查询失败: {status_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ 状态查询异常: {e}")
            
            print("⏰ 测试超时")
            return False
                
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 异常: {e}")
        return False
    finally:
        try:
            os.unlink(txt_file)
        except:
            pass

def test_system_fonts():
    """测试系统字体"""
    print("\n🔍 检查系统字体...")
    
    import platform
    system = platform.system()
    print(f"系统: {system}")
    
    if system == 'Darwin':  # macOS
        # 检查常用中文字体
        fonts_to_check = [
            'PingFang SC',
            'Hiragino Sans GB', 
            'STHeiti',
            'Arial Unicode MS'
        ]
        
        print("检查macOS中文字体:")
        for font in fonts_to_check:
            print(f"  - {font}")
        
        # 可以尝试使用系统命令检查字体
        try:
            import subprocess
            result = subprocess.run(['fc-list', ':lang=zh'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                print("✅ 系统支持中文字体")
            else:
                print("⚠️ 可能缺少中文字体支持")
        except:
            print("ℹ️ 无法检查字体列表（fc-list不可用）")

if __name__ == "__main__":
    test_system_fonts()
    success = test_chinese_subtitle()
    
    if success:
        print("\n🎉 中文字幕测试完成！请检查生成的视频文件。")
    else:
        print("\n❌ 中文字幕测试失败。")
        print("\n🔧 故障排除建议:")
        print("1. 检查系统是否安装了中文字体")
        print("2. 确认FFmpeg是否支持字幕滤镜")
        print("3. 检查字幕文件编码是否为UTF-8")
        print("4. 尝试使用其他字体名称")