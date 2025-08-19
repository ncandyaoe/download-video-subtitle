#!/usr/bin/env python3
"""
测试音频文本对齐功能
"""

import os
import tempfile
from simple_audio_text_aligner import align_mp3_with_txt

def create_test_files():
    """创建测试用的音频和文本文件"""
    
    # 创建测试文本
    test_text = """欢迎观看猴子捞月的故事！
看，一群可爱的小猴子在月光下快乐地玩耍呢！
它们在树枝间跳跃，发出欢快的叫声。
突然，小猴子们发现了水中的月亮。
"哇！月亮掉到水里了！"一只小猴子惊呼道。
"我们要把月亮捞上来！"另一只小猴子说。
于是，小猴子们开始了捞月亮的行动。
它们一个接一个地倒挂在树枝上。
最小的猴子伸手去捞水中的月亮。
但是，当它的手碰到水面时，月亮竟然碎了！
小猴子们这才明白，那只是月亮的倒影。
真正的月亮还在天空中对它们微笑呢！"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_text)
        txt_file = f.name
    
    return txt_file, test_text

def test_alignment_with_real_files():
    """使用真实文件测试对齐功能"""
    
    print("🧪 音频文本对齐功能测试")
    print("=" * 60)
    
    # 检查是否有真实的测试文件
    test_mp3 = "/Users/mulele/Documents/4-n8ndata/video/猴子捞月/monkey_story.mp3"
    test_txt = None
    
    if os.path.exists(test_mp3):
        print(f"✅ 找到测试音频文件: {test_mp3}")
        
        # 创建测试文本文件
        txt_file, txt_content = create_test_files()
        test_txt = txt_file
        
        print(f"📝 创建测试文本文件: {test_txt}")
        print(f"📄 文本内容预览:")
        lines = txt_content.split('\n')
        for i, line in enumerate(lines[:5], 1):
            if line.strip():
                print(f"   {i}. {line}")
        print(f"   ... (共{len([l for l in lines if l.strip()])}行)")
        
        try:
            # 执行对齐测试
            print(f"\n🚀 开始对齐测试...")
            output_srt = txt_file.replace('.txt', '_aligned.srt')
            
            result = align_mp3_with_txt(test_mp3, test_txt, output_srt)
            
            if result['success']:
                print(f"\n🎉 对齐测试成功!")
                print(f"📁 输出文件: {result['srt_file']}")
                print(f"🌍 检测语言: {result['language']}")
                print(f"📊 字幕段落: {result['total_segments']} 个")
                print(f"⏱️ 总时长: {result['total_duration']:.1f} 秒")
                print(f"🎯 平均置信度: {result['average_confidence']:.2f}")
                
                # 显示对齐结果
                print(f"\n📋 对齐结果预览:")
                for i, segment in enumerate(result['segments_preview']):
                    print(f"  {i+1}. [{segment['start_time']:.1f}s - {segment['end_time']:.1f}s] "
                          f"置信度: {segment['confidence']:.2f}")
                    print(f"     {segment['text'][:60]}...")
                
                # 显示生成的SRT内容
                print(f"\n📝 生成的SRT字幕预览:")
                with open(result['srt_file'], 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                
                lines = srt_content.split('\n')
                for line in lines[:15]:  # 显示前15行
                    print(f"     {line}")
                print(f"     ... (完整内容请查看文件)")
                
                print(f"\n💡 使用建议:")
                if result['average_confidence'] > 0.7:
                    print(f"   ✅ 对齐质量良好，可以直接使用")
                elif result['average_confidence'] > 0.5:
                    print(f"   ⚠️ 对齐质量一般，建议检查关键段落")
                else:
                    print(f"   ❌ 对齐质量较差，建议检查音频和文本是否匹配")
                
                return True
            else:
                print(f"❌ 对齐测试失败")
                return False
                
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # 清理测试文件
            try:
                if test_txt and os.path.exists(test_txt):
                    os.unlink(test_txt)
                srt_file = test_txt.replace('.txt', '_aligned.srt') if test_txt else None
                if srt_file and os.path.exists(srt_file):
                    print(f"🧹 保留生成的SRT文件: {srt_file}")
                    # os.unlink(srt_file)  # 保留SRT文件供查看
            except:
                pass
    
    else:
        print(f"❌ 未找到测试音频文件: {test_mp3}")
        print(f"💡 请将你的MP3文件放在指定位置，或修改测试路径")
        return False

def test_text_splitting():
    """测试文本分割功能"""
    print(f"\n🔍 测试文本分割功能")
    print("=" * 40)
    
    from simple_audio_text_aligner import split_text_by_punctuation
    
    test_texts = [
        "这是一个简单的句子。",
        "第一句话。第二句话！第三句话？",
        "这是一个很长的句子，包含逗号，还有更多内容，需要进行分割处理。",
        "短句。很长的句子包含很多内容需要分割，因为太长了，所以要处理。又一句。"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n测试文本 {i}: {text}")
        segments = split_text_by_punctuation(text)
        print(f"分割结果 ({len(segments)} 段):")
        for j, segment in enumerate(segments, 1):
            print(f"  {j}. {segment}")

def main():
    """主测试函数"""
    print("🚀 音频文本对齐工具测试套件")
    print("=" * 80)
    
    # 测试文本分割
    test_text_splitting()
    
    # 测试完整对齐流程
    success = test_alignment_with_real_files()
    
    print(f"\n" + "=" * 80)
    if success:
        print("🎉 所有测试通过！音频文本对齐功能正常工作。")
    else:
        print("⚠️ 部分测试失败，请检查配置和文件。")

if __name__ == "__main__":
    main()