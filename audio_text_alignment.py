#!/usr/bin/env python3
"""
音频文本对齐工具
基于现有MP3音频和TXT文本，生成完美对齐的字幕
"""

import os
import re
import json
from moviepy.editor import AudioFileClip
from faster_whisper import WhisperModel
from loguru import logger

class AudioTextAligner:
    """音频文本对齐器"""
    
    def __init__(self, model_size="large-v3"):
        self.model_size = model_size
        self.model = None
        
    def load_whisper_model(self):
        """加载Whisper模型"""
        if not self.model:
            logger.info(f"加载Whisper模型: {self.model_size}")
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self.model
    
    def split_text_by_punctuation(self, text):
        """按标点符号分割文本"""
        # 分割标点符号，保留标点
        segments = re.split(r'([，。！？；:,.!?;:])', text)
        
        result = []
        current = ""
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
                
            if segment in "，。！？；:,.!?;:":
                # 标点符号，添加到当前段落
                current += segment
                if current.strip():
                    result.append(current.strip())
                current = ""
            else:
                # 文本内容
                current += segment
        
        # 处理最后一段
        if current.strip():
            result.append(current.strip())
        
        return [s for s in result if s.strip()]
    
    def transcribe_with_word_timestamps(self, audio_file):
        """转录音频并获取词级时间戳"""
        model = self.load_whisper_model()
        
        logger.info(f"开始转录音频: {audio_file}")
        segments, info = model.transcribe(
            audio_file,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),
        )
        
        logger.info(f"检测语言: {info.language}, 置信度: {info.language_probability:.2f}")
        
        # 提取所有词和时间戳
        words_with_timestamps = []
        for segment in segments:
            if segment.words:
                for word in segment.words:
                    words_with_timestamps.append({
                        'word': word.word.strip(),
                        'start': word.start,
                        'end': word.end
                    })
        
        return words_with_timestamps, info.language
    
    def calculate_similarity(self, text1, text2):
        """计算两个文本的相似度"""
        # 简单的字符级相似度计算
        text1 = re.sub(r'[^\w\s]', '', text1.lower())
        text2 = re.sub(r'[^\w\s]', '', text2.lower())
        
        if not text1 or not text2:
            return 0.0
        
        # 使用最长公共子序列
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(text1, text2)
        max_len = max(len(text1), len(text2))
        
        return lcs_len / max_len if max_len > 0 else 0.0
    
    def align_text_segments(self, txt_segments, transcribed_words):
        """将文本段落与转录词对齐"""
        logger.info(f"开始对齐 {len(txt_segments)} 个文本段落和 {len(transcribed_words)} 个转录词")
        
        aligned_segments = []
        word_index = 0
        
        for i, txt_segment in enumerate(txt_segments):
            logger.debug(f"处理文本段落 {i+1}: {txt_segment[:50]}...")
            
            # 清理文本用于匹配
            clean_txt = re.sub(r'[^\w\s]', '', txt_segment.lower())
            txt_words = clean_txt.split()
            
            if not txt_words:
                continue
            
            # 寻找最佳匹配的起始位置
            best_start_index = word_index
            best_similarity = 0.0
            
            # 在当前位置附近搜索最佳匹配
            search_range = min(50, len(transcribed_words) - word_index)
            
            for offset in range(search_range):
                test_index = word_index + offset
                if test_index >= len(transcribed_words):
                    break
                
                # 构建测试文本
                test_words = []
                for j in range(test_index, min(test_index + len(txt_words) * 2, len(transcribed_words))):
                    test_words.append(re.sub(r'[^\w\s]', '', transcribed_words[j]['word'].lower()))
                
                test_text = ' '.join(test_words)
                similarity = self.calculate_similarity(clean_txt, test_text)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_start_index = test_index
            
            # 确定段落的时间范围
            if best_start_index < len(transcribed_words):
                start_time = transcribed_words[best_start_index]['start']
                
                # 估算结束时间
                estimated_word_count = len(txt_words)
                end_index = min(best_start_index + estimated_word_count, len(transcribed_words) - 1)
                
                # 微调结束位置
                for j in range(best_start_index + 1, min(best_start_index + estimated_word_count * 2, len(transcribed_words))):
                    current_text = ' '.join([re.sub(r'[^\w\s]', '', transcribed_words[k]['word'].lower()) 
                                           for k in range(best_start_index, j + 1)])
                    
                    if self.calculate_similarity(clean_txt, current_text) > 0.7:
                        end_index = j
                    else:
                        break
                
                end_time = transcribed_words[end_index]['end']
                
                # 确保最小时长
                if end_time - start_time < 1.0:
                    end_time = start_time + max(1.0, len(txt_segment) * 0.1)
                
                aligned_segments.append({
                    'text': txt_segment,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': best_similarity
                })
                
                word_index = end_index + 1
                logger.debug(f"对齐成功: {start_time:.2f}s - {end_time:.2f}s, 置信度: {best_similarity:.2f}")
            else:
                # 如果无法找到匹配，使用估算时间
                if aligned_segments:
                    last_end = aligned_segments[-1]['end_time']
                    estimated_duration = len(txt_segment) * 0.15
                    aligned_segments.append({
                        'text': txt_segment,
                        'start_time': last_end,
                        'end_time': last_end + estimated_duration,
                        'confidence': 0.0
                    })
                else:
                    estimated_duration = len(txt_segment) * 0.15
                    aligned_segments.append({
                        'text': txt_segment,
                        'start_time': 0.0,
                        'end_time': estimated_duration,
                        'confidence': 0.0
                    })
                
                logger.warning(f"无法对齐段落，使用估算时间: {txt_segment[:30]}...")
        
        return aligned_segments
    
    def generate_srt(self, aligned_segments, output_file):
        """生成SRT字幕文件"""
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            milliseconds = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(aligned_segments, 1):
                start_time = format_time(segment['start_time'])
                end_time = format_time(segment['end_time'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        
        logger.info(f"SRT字幕文件已生成: {output_file}")
        return output_file
    
    def align_audio_text(self, audio_file, txt_file, output_srt_file):
        """主要对齐函数"""
        logger.info("开始音频文本对齐流程")
        
        # 1. 读取文本文件
        with open(txt_file, 'r', encoding='utf-8') as f:
            txt_content = f.read().strip()
        
        if not txt_content:
            raise ValueError("文本文件为空")
        
        logger.info(f"文本内容长度: {len(txt_content)} 字符")
        
        # 2. 分割文本
        txt_segments = self.split_text_by_punctuation(txt_content)
        logger.info(f"文本分割为 {len(txt_segments)} 个段落")
        
        # 3. 转录音频获取时间戳
        transcribed_words, language = self.transcribe_with_word_timestamps(audio_file)
        logger.info(f"转录获得 {len(transcribed_words)} 个词的时间戳")
        
        # 4. 对齐文本和音频
        aligned_segments = self.align_text_segments(txt_segments, transcribed_words)
        
        # 5. 生成SRT文件
        srt_file = self.generate_srt(aligned_segments, output_srt_file)
        
        # 6. 生成对齐报告
        total_confidence = sum(seg['confidence'] for seg in aligned_segments)
        avg_confidence = total_confidence / len(aligned_segments) if aligned_segments else 0
        
        report = {
            'audio_file': audio_file,
            'txt_file': txt_file,
            'srt_file': srt_file,
            'language': language,
            'total_segments': len(aligned_segments),
            'average_confidence': avg_confidence,
            'segments': aligned_segments
        }
        
        logger.info(f"对齐完成! 平均置信度: {avg_confidence:.2f}")
        return report

def main():
    """主函数示例"""
    # 使用示例
    aligner = AudioTextAligner()
    
    # 输入文件
    audio_file = "your_audio.mp3"  # 你的音频文件
    txt_file = "your_script.txt"   # 你的文本文件
    output_srt = "aligned_subtitle.srt"  # 输出字幕文件
    
    try:
        # 执行对齐
        report = aligner.align_audio_text(audio_file, txt_file, output_srt)
        
        print("🎉 对齐完成!")
        print(f"📁 字幕文件: {report['srt_file']}")
        print(f"🌍 检测语言: {report['language']}")
        print(f"📊 段落数量: {report['total_segments']}")
        print(f"🎯 平均置信度: {report['average_confidence']:.2f}")
        
        # 显示前几个段落的对齐结果
        print("\n📋 对齐结果预览:")
        for i, segment in enumerate(report['segments'][:3]):
            print(f"  {i+1}. [{segment['start_time']:.2f}s - {segment['end_time']:.2f}s] "
                  f"置信度: {segment['confidence']:.2f}")
            print(f"     {segment['text'][:50]}...")
        
    except Exception as e:
        print(f"❌ 对齐失败: {e}")

if __name__ == "__main__":
    main()