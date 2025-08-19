#!/usr/bin/env python3
"""
简化的音频文本对齐工具
专门用于将现有MP3音频与TXT文本对齐生成字幕
"""

import os
import re
from faster_whisper import WhisperModel
from moviepy.editor import AudioFileClip
from loguru import logger

def split_text_by_punctuation(text):
    """按标点符号智能分割文本"""
    # 按标点符号分割，但保持合理的句子长度
    sentences = re.split(r'[。！？；]', text)
    
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 如果句子太长，按逗号进一步分割
        if len(sentence) > 50:
            parts = re.split(r'[，,]', sentence)
            current = ""
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                if len(current + part) < 50:
                    current += part + "，"
                else:
                    if current:
                        result.append(current.rstrip("，"))
                    current = part + "，"
            
            if current:
                result.append(current.rstrip("，"))
        else:
            result.append(sentence)
    
    return [s for s in result if s.strip()]

def transcribe_audio_with_timestamps(audio_file, model_size="large-v3"):
    """转录音频并获取段落级时间戳"""
    logger.info(f"开始转录音频: {audio_file}")
    
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        word_timestamps=False,  # 使用段落级时间戳，更稳定
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    
    logger.info(f"检测语言: {info.language}, 置信度: {info.language_probability:.2f}")
    
    transcribed_segments = []
    for segment in segments:
        transcribed_segments.append({
            'text': segment.text.strip(),
            'start': segment.start,
            'end': segment.end
        })
    
    return transcribed_segments, info.language

def calculate_text_similarity(text1, text2):
    """计算两个文本的相似度"""
    # 移除标点符号和空格，转为小写
    clean1 = re.sub(r'[^\w]', '', text1.lower())
    clean2 = re.sub(r'[^\w]', '', text2.lower())
    
    if not clean1 or not clean2:
        return 0.0
    
    # 计算字符级相似度
    shorter = min(len(clean1), len(clean2))
    longer = max(len(clean1), len(clean2))
    
    if longer == 0:
        return 1.0
    
    # 计算公共字符数
    common_chars = 0
    for i in range(shorter):
        if i < len(clean1) and i < len(clean2) and clean1[i] == clean2[i]:
            common_chars += 1
    
    return common_chars / longer

def align_text_with_audio(txt_segments, transcribed_segments):
    """将文本段落与音频转录对齐"""
    logger.info(f"开始对齐 {len(txt_segments)} 个文本段落和 {len(transcribed_segments)} 个音频段落")
    
    aligned_segments = []
    
    # 获取音频总时长
    if transcribed_segments:
        total_audio_duration = transcribed_segments[-1]['end']
    else:
        total_audio_duration = 60.0  # 默认60秒
    
    # 如果文本段落数量与音频段落数量相近，直接对应
    if abs(len(txt_segments) - len(transcribed_segments)) <= 2:
        logger.info("段落数量相近，使用直接对应策略")
        
        for i, txt_segment in enumerate(txt_segments):
            if i < len(transcribed_segments):
                # 使用音频的时间戳
                audio_seg = transcribed_segments[i]
                aligned_segments.append({
                    'text': txt_segment,
                    'start_time': audio_seg['start'],
                    'end_time': audio_seg['end'],
                    'confidence': calculate_text_similarity(txt_segment, audio_seg['text'])
                })
            else:
                # 超出部分使用估算时间
                if aligned_segments:
                    last_end = aligned_segments[-1]['end_time']
                    duration = len(txt_segment) * 0.15  # 估算每字符0.15秒
                    aligned_segments.append({
                        'text': txt_segment,
                        'start_time': last_end,
                        'end_time': min(last_end + duration, total_audio_duration),
                        'confidence': 0.5
                    })
    
    else:
        # 段落数量差异较大，使用时间比例分配
        logger.info("段落数量差异较大，使用时间比例分配策略")
        
        # 计算每个文本段落的相对权重（基于字符数）
        total_chars = sum(len(seg) for seg in txt_segments)
        
        current_time = 0.0
        for i, txt_segment in enumerate(txt_segments):
            char_ratio = len(txt_segment) / total_chars if total_chars > 0 else 1.0 / len(txt_segments)
            duration = total_audio_duration * char_ratio
            
            # 确保最小和最大时长
            duration = max(1.0, min(duration, 10.0))
            
            end_time = min(current_time + duration, total_audio_duration)
            
            aligned_segments.append({
                'text': txt_segment,
                'start_time': current_time,
                'end_time': end_time,
                'confidence': 0.7  # 估算置信度
            })
            
            current_time = end_time
            
            if current_time >= total_audio_duration:
                break
    
    return aligned_segments

def generate_srt_file(aligned_segments, output_file):
    """生成SRT字幕文件"""
    def format_timestamp(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(aligned_segments, 1):
            start_time = format_timestamp(segment['start_time'])
            end_time = format_timestamp(segment['end_time'])
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment['text']}\n\n")
    
    logger.info(f"SRT字幕文件已生成: {output_file}")
    return output_file

def align_mp3_with_txt(mp3_file, txt_file, output_srt_file):
    """
    主函数：将MP3音频与TXT文本对齐生成SRT字幕
    
    Args:
        mp3_file: MP3音频文件路径
        txt_file: TXT文本文件路径
        output_srt_file: 输出SRT字幕文件路径
    
    Returns:
        dict: 对齐结果报告
    """
    
    logger.info("🚀 开始音频文本对齐流程")
    
    # 1. 检查文件存在性
    if not os.path.exists(mp3_file):
        raise FileNotFoundError(f"音频文件不存在: {mp3_file}")
    
    if not os.path.exists(txt_file):
        raise FileNotFoundError(f"文本文件不存在: {txt_file}")
    
    # 2. 读取并分割文本
    logger.info("📖 读取文本文件...")
    with open(txt_file, 'r', encoding='utf-8') as f:
        txt_content = f.read().strip()
    
    if not txt_content:
        raise ValueError("文本文件为空")
    
    txt_segments = split_text_by_punctuation(txt_content)
    logger.info(f"文本分割为 {len(txt_segments)} 个段落")
    
    # 3. 转录音频
    logger.info("🎵 转录音频文件...")
    transcribed_segments, language = transcribe_audio_with_timestamps(mp3_file)
    logger.info(f"音频转录为 {len(transcribed_segments)} 个段落")
    
    # 4. 对齐文本和音频
    logger.info("🔄 对齐文本和音频...")
    aligned_segments = align_text_with_audio(txt_segments, transcribed_segments)
    
    # 5. 生成SRT文件
    logger.info("📝 生成SRT字幕文件...")
    srt_file = generate_srt_file(aligned_segments, output_srt_file)
    
    # 6. 计算统计信息
    total_confidence = sum(seg['confidence'] for seg in aligned_segments)
    avg_confidence = total_confidence / len(aligned_segments) if aligned_segments else 0
    
    total_duration = aligned_segments[-1]['end_time'] if aligned_segments else 0
    
    report = {
        'success': True,
        'mp3_file': mp3_file,
        'txt_file': txt_file,
        'srt_file': srt_file,
        'language': language,
        'total_segments': len(aligned_segments),
        'total_duration': total_duration,
        'average_confidence': avg_confidence,
        'segments_preview': aligned_segments[:3]  # 前3个段落预览
    }
    
    logger.info(f"✅ 对齐完成! 生成 {len(aligned_segments)} 个字幕段落")
    logger.info(f"📊 平均置信度: {avg_confidence:.2f}")
    logger.info(f"⏱️ 总时长: {total_duration:.2f} 秒")
    
    return report

# 使用示例
if __name__ == "__main__":
    # 示例用法
    mp3_file = "your_audio.mp3"      # 替换为你的MP3文件路径
    txt_file = "your_script.txt"     # 替换为你的TXT文件路径
    output_srt = "aligned_subtitle.srt"  # 输出的SRT文件路径
    
    try:
        result = align_mp3_with_txt(mp3_file, txt_file, output_srt)
        
        print("🎉 音频文本对齐成功!")
        print(f"📁 输出文件: {result['srt_file']}")
        print(f"🌍 检测语言: {result['language']}")
        print(f"📊 字幕段落: {result['total_segments']} 个")
        print(f"⏱️ 总时长: {result['total_duration']:.1f} 秒")
        print(f"🎯 平均置信度: {result['average_confidence']:.2f}")
        
        print("\n📋 前3个段落预览:")
        for i, segment in enumerate(result['segments_preview']):
            print(f"  {i+1}. [{segment['start_time']:.1f}s - {segment['end_time']:.1f}s] "
                  f"置信度: {segment['confidence']:.2f}")
            print(f"     {segment['text'][:60]}...")
        
    except Exception as e:
        print(f"❌ 对齐失败: {e}")
        import traceback
        traceback.print_exc()