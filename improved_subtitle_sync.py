#!/usr/bin/env python3
"""
改进的字幕同步解决方案
"""

import os
import re
from moviepy.editor import AudioFileClip
from text_to_speech import MinimaxiT2A
from subtitle import split_string_by_punctuations, text_to_srt

def generate_synced_subtitle_from_txt(txt_content, output_srt_path, tts_audio_path=None):
    """
    从TXT文本生成同步的字幕文件
    
    Args:
        txt_content: TXT文本内容
        output_srt_path: 输出SRT文件路径
        tts_audio_path: TTS生成的音频文件路径（可选）
    
    Returns:
        str: 生成的SRT文件路径
    """
    
    # 1. 分割文本为句子
    sentences = split_string_by_punctuations(txt_content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        raise ValueError("没有有效的文本内容")
    
    # 2. 如果有TTS音频，基于音频时长分配时间
    if tts_audio_path and os.path.exists(tts_audio_path):
        audio = AudioFileClip(tts_audio_path)
        total_duration = audio.duration
        audio.close()
        
        # 基于字符数量按比例分配时间
        total_chars = sum(len(s) for s in sentences)
        
        subtitles = []
        current_time = 0.0
        
        for sentence in sentences:
            # 按字符比例分配时间，最少2秒，最多8秒
            char_ratio = len(sentence) / total_chars if total_chars > 0 else 1.0 / len(sentences)
            duration = max(2.0, min(8.0, total_duration * char_ratio))
            
            # 确保不超过总时长
            if current_time + duration > total_duration:
                duration = total_duration - current_time
            
            subtitles.append({
                'text': sentence,
                'start': current_time,
                'end': current_time + duration
            })
            
            current_time += duration
            
            if current_time >= total_duration:
                break
    else:
        # 没有音频文件，使用估算时长
        subtitles = []
        current_time = 0.0
        
        for sentence in sentences:
            # 基于字符数估算时长：中文约0.15秒/字，英文约0.1秒/字
            estimated_duration = max(2.0, len(sentence) * 0.15)
            
            subtitles.append({
                'text': sentence,
                'start': current_time,
                'end': current_time + estimated_duration
            })
            
            current_time += estimated_duration
    
    # 3. 生成SRT文件
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles, 1):
            srt_content = text_to_srt(
                i, 
                subtitle['text'], 
                subtitle['start'], 
                subtitle['end']
            )
            f.write(srt_content)
    
    print(f"同步字幕已生成: {output_srt_path}")
    print(f"总时长: {current_time:.2f}秒, 字幕条数: {len(subtitles)}")
    
    return output_srt_path

def create_synced_video_with_tts(txt_file, output_dir="output"):
    """
    使用TTS创建完全同步的视频
    
    Args:
        txt_file: TXT脚本文件路径
        output_dir: 输出目录
    
    Returns:
        dict: 包含音频文件和字幕文件路径的字典
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 读取TXT内容
    with open(txt_file, 'r', encoding='utf-8') as f:
        txt_content = f.read().strip()
    
    if not txt_content:
        raise ValueError("TXT文件为空")
    
    # 2. 使用TTS生成音频
    print("🎵 正在生成TTS音频...")
    try:
        t2a = MinimaxiT2A()
        tts_audio_path = t2a.text_to_speech(
            txt_content,
            voice_id="female-qn-qingse",  # 可以根据需要调整
            output_format="mp3"
        )
        
        if not tts_audio_path:
            raise Exception("TTS音频生成失败")
            
        # 移动到输出目录
        final_audio_path = os.path.join(output_dir, "synced_audio.mp3")
        if tts_audio_path != final_audio_path:
            import shutil
            shutil.move(tts_audio_path, final_audio_path)
            tts_audio_path = final_audio_path
            
        print(f"✅ TTS音频生成成功: {tts_audio_path}")
        
    except Exception as e:
        print(f"❌ TTS生成失败: {e}")
        print("🔄 将使用估算时长生成字幕")
        tts_audio_path = None
    
    # 3. 生成同步字幕
    print("📝 正在生成同步字幕...")
    srt_path = os.path.join(output_dir, "synced_subtitle.srt")
    generate_synced_subtitle_from_txt(txt_content, srt_path, tts_audio_path)
    
    return {
        'audio_file': tts_audio_path,
        'subtitle_file': srt_path,
        'txt_content': txt_content
    }

def improved_video_merge_workflow(txt_file, video_files=None, aspect_ratio="16:9", output_dir="output"):
    """
    改进的视频合成工作流，确保音频和字幕完全同步
    
    Args:
        txt_file: TXT脚本文件
        video_files: 视频文件列表（可选）
        aspect_ratio: 宽高比
        output_dir: 输出目录
    """
    
    print("🚀 开始改进的视频合成流程")
    print("=" * 50)
    
    # 1. 创建同步的音频和字幕
    sync_result = create_synced_video_with_tts(txt_file, output_dir)
    
    if not sync_result['audio_file']:
        print("❌ 无法生成TTS音频，流程终止")
        return None
    
    # 2. 如果没有视频文件，创建纯色背景
    if not video_files:
        print("📺 创建纯色背景视频...")
        from moviepy.editor import ColorClip, AudioFileClip
        
        audio = AudioFileClip(sync_result['audio_file'])
        color_clip = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=audio.duration)
        bg_video_path = os.path.join(output_dir, "background.mp4")
        color_clip.write_videofile(bg_video_path, fps=25, codec="libx264", audio=False)
        video_files = [bg_video_path]
        audio.close()
    
    # 3. 合成视频（使用你现有的逻辑）
    print("🎬 合成最终视频...")
    from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
    
    # 加载音频
    audio_clip = AudioFileClip(sync_result['audio_file'])
    audio_duration = audio_clip.duration
    
    # 处理视频文件
    clips = [VideoFileClip(v) for v in video_files]
    
    # 循环拼接视频直到匹配音频长度
    final_clips = []
    current_duration = 0
    i = 0
    while current_duration < audio_duration:
        clip = clips[i % len(clips)]
        final_clips.append(clip)
        current_duration += clip.duration
        i += 1
    
    # 拼接并设置音频
    video = concatenate_videoclips(final_clips).subclip(0, audio_duration)
    video = video.set_audio(audio_clip)
    
    # 保存无字幕版本
    video_without_sub = os.path.join(output_dir, "video_without_subtitle.mp4")
    video.write_videofile(video_without_sub, codec="libx264", audio_codec="aac")
    
    # 4. 添加字幕
    print("📝 添加同步字幕...")
    final_video = os.path.join(output_dir, "final_video_with_subtitle.mp4")
    
    # 使用改进的字幕添加命令
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-i", video_without_sub,
        "-vf", f"subtitles={sync_result['subtitle_file']}:force_style='FontName=PingFang SC,FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2'",
        "-c:a", "copy",
        final_video
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ 最终视频生成成功: {final_video}")
        
        return {
            'final_video': final_video,
            'audio_file': sync_result['audio_file'],
            'subtitle_file': sync_result['subtitle_file'],
            'video_without_subtitle': video_without_sub
        }
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 字幕添加失败: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 示例用法
    txt_file = "example_script.txt"
    
    # 创建示例TXT文件
    sample_content = """欢迎观看猴子捞月的故事！
看，一群可爱的小猴子在月光下快乐地玩耍呢！
它们在树枝间跳跃，发出欢快的叫声。
突然，小猴子们发现了水中的月亮。
"哇！月亮掉到水里了！"一只小猴子惊呼道。
"我们要把月亮捞上来！"另一只小猴子说。
于是，小猴子们开始了捞月亮的行动。"""
    
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    # 执行改进的工作流
    result = improved_video_merge_workflow(txt_file)
    
    if result:
        print("\n🎉 视频合成完成！")
        print(f"📁 最终视频: {result['final_video']}")
        print(f"🎵 音频文件: {result['audio_file']}")
        print(f"📝 字幕文件: {result['subtitle_file']}")
    else:
        print("\n❌ 视频合成失败")