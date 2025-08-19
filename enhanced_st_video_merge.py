import streamlit as st
import os
from tempfile import TemporaryDirectory
from srt_generate import auto_fix_video, get_target_size, process_video_with_ffmpeg
import subprocess
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from simple_audio_text_aligner import align_mp3_with_txt

def add_srt_to_video(video_path, srt_path, output_path):
    """
    用 ffmpeg 将 srt 字幕文件叠加到视频上，支持中文字体
    """
    import platform
    
    # 根据系统选择合适的中文字体
    system = platform.system()
    if system == 'Darwin':  # macOS
        font_name = 'PingFang SC'
    elif system == 'Linux':
        font_name = 'Noto Sans CJK SC'
    else:  # Windows
        font_name = 'Microsoft YaHei'
    
    # 构建字幕滤镜，确保中文显示
    subtitle_filter = f"subtitles={srt_path}:force_style='FontName={font_name},FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=1'"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", subtitle_filter,
        "-c:a", "copy",
        "-c:v", "libx264",  # 确保视频编码兼容性
        output_path
    ]
    
    print(f"🎨 使用字体: {font_name}")
    print(f"📝 字幕滤镜: {subtitle_filter}")
    
    subprocess.run(cmd, check=True)

st.set_page_config(page_title="智能音频文本对齐视频合成工具", layout="centered")

st.title("🎯 智能音频文本对齐视频合成工具")
st.markdown("""
### ✨ 核心功能：
- 🎵 **智能对齐**：将现有MP3音频与TXT文本完美对齐
- 📝 **精准字幕**：基于音频实际时间轴生成准确字幕
- 🎬 **视频合成**：支持多视频片段循环拼接
- 🔤 **中文优化**：完美支持中文字幕显示

### 📋 使用说明：
1. 上传你的MP3音频文件（必需）
2. 上传对应的TXT脚本文件（必需）
3. 可选上传视频片段进行合成
4. 系统会自动对齐音频和文本，生成同步字幕
""")

# 文件上传区域
st.subheader("📁 文件上传")

col1, col2 = st.columns(2)

with col1:
    uploaded_audio = st.file_uploader(
        "🎵 上传MP3音频文件", 
        type=["mp3"],
        help="上传你已有的MP3音频文件"
    )

with col2:
    uploaded_text = st.file_uploader(
        "📝 上传TXT脚本文件", 
        type=["txt"],
        help="上传与音频对应的文本脚本"
    )

# 可选视频上传
uploaded_videos = st.file_uploader(
    "🎬 可选：上传视频片段（可多选）", 
    type=["mp4"], 
    accept_multiple_files=True,
    help="如果不上传视频，系统会自动生成纯色背景"
)

# 设置选项
st.subheader("⚙️ 设置选项")

col1, col2 = st.columns(2)

with col1:
    aspect_ratio = st.selectbox(
        "📐 选择输出视频宽高比", 
        ["16:9", "9:16", "4:3", "3:4", "1:1"], 
        index=0
    )

with col2:
    whisper_model = st.selectbox(
        "🤖 Whisper模型大小",
        ["large-v3", "medium", "small", "base"],
        index=0,
        help="large-v3最准确但较慢，base最快但准确度较低"
    )

# 预览上传的文件
if uploaded_text:
    with st.expander("📖 查看文本内容"):
        text_content = uploaded_text.read().decode('utf-8')
        st.text_area("文本预览", text_content[:500] + "..." if len(text_content) > 500 else text_content, height=150)
        uploaded_text.seek(0)  # 重置文件指针

if uploaded_audio:
    st.audio(uploaded_audio, format='audio/mp3')

# 主要处理按钮
if st.button("🚀 开始智能对齐和合成", type="primary"):
    if not uploaded_audio or not uploaded_text:
        st.error("❌ 请先上传MP3音频文件和TXT脚本文件！")
    else:
        with st.spinner("🔄 正在进行智能对齐和视频合成，请稍候..."):
            with TemporaryDirectory() as tmpdir:
                try:
                    # 保存上传的文件
                    audio_path = os.path.join(tmpdir, "input_audio.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_audio.read())
                    
                    script_path = os.path.join(tmpdir, "input_script.txt")
                    with open(script_path, "wb") as f:
                        f.write(uploaded_text.read())
                    
                    st.info("📁 文件保存完成")
                    
                    # 执行智能对齐
                    st.info("🎯 正在进行音频文本智能对齐...")
                    
                    subtitle_path = os.path.join(tmpdir, "aligned_subtitle.srt")
                    
                    # 使用我们的智能对齐工具
                    alignment_result = align_mp3_with_txt(audio_path, script_path, subtitle_path)
                    
                    if alignment_result['success']:
                        st.success(f"✅ 对齐成功！生成 {alignment_result['total_segments']} 个字幕段落")
                        st.info(f"🌍 检测语言: {alignment_result['language']}")
                        st.info(f"⏱️ 总时长: {alignment_result['total_duration']:.1f} 秒")
                        st.info(f"🎯 平均置信度: {alignment_result['average_confidence']:.2f}")
                        
                        # 显示字幕预览
                        with st.expander("📝 查看生成的字幕"):
                            with open(subtitle_path, 'r', encoding='utf-8') as f:
                                srt_content = f.read()
                            st.text_area("SRT字幕预览", srt_content[:800] + "..." if len(srt_content) > 800 else srt_content, height=200)
                    else:
                        st.error("❌ 音频文本对齐失败")
                        st.stop()
                    
                    # 处理视频文件
                    video_paths = []
                    if uploaded_videos:
                        st.info("🎬 处理上传的视频文件...")
                        for i, v in enumerate(uploaded_videos):
                            v_path = os.path.join(tmpdir, f"input_video_{i}.mp4")
                            with open(v_path, "wb") as f:
                                f.write(v.read())
                            video_paths.append(v_path)
                    else:
                        # 创建纯色背景视频
                        st.info("🎨 创建纯色背景视频...")
                        from moviepy.editor import ColorClip
                        
                        audio_clip = AudioFileClip(audio_path)
                        color_clip = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=audio_clip.duration)
                        bg_video_path = os.path.join(tmpdir, "bg_video.mp4")
                        color_clip.write_videofile(bg_video_path, fps=25, codec="libx264", audio=False)
                        video_paths = [bg_video_path]
                        audio_clip.close()
                    
                    # 视频处理和标准化
                    st.info("🔧 处理和标准化视频...")
                    target_size = get_target_size(aspect_ratio)
                    fixed_video_paths = []
                    
                    for i, v_path in enumerate(video_paths):
                        try:
                            # 修复视频格式
                            fixed_path = auto_fix_video(v_path)
                            # 统一分辨率
                            resized_path = os.path.join(tmpdir, f"resized_{i}.mp4")
                            process_video_with_ffmpeg(fixed_path, resized_path, target_size)
                            fixed_video_paths.append(resized_path)
                            st.success(f"✅ 视频 {i+1} 处理完成")
                        except Exception as e:
                            st.warning(f"⚠️ 视频 {i+1} 处理失败: {e}")
                    
                    if not fixed_video_paths:
                        st.error("❌ 没有可用的视频文件")
                        st.stop()
                    
                    # 视频合成
                    st.info("🎬 正在合成最终视频...")
                    
                    # 加载视频片段
                    clips = [VideoFileClip(p) for p in fixed_video_paths]
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    
                    # 循环拼接视频片段直到匹配音频长度
                    final_clips = []
                    current_duration = 0
                    i = 0
                    while current_duration < audio_duration:
                        clip = clips[i % len(clips)]
                        final_clips.append(clip)
                        current_duration += clip.duration
                        i += 1
                    
                    # 拼接并截断到音频长度
                    video = concatenate_videoclips(final_clips).subclip(0, audio_duration)
                    video = video.set_audio(audio_clip)
                    
                    # 保存无字幕版本
                    output_path = os.path.join(tmpdir, "output_video.mp4")
                    video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=video.fps)
                    
                    st.success("✅ 视频合成完成")
                    
                    # 添加对齐的字幕
                    st.info("📝 正在添加智能对齐的字幕...")
                    final_video_with_sub = os.path.join(tmpdir, "final_with_aligned_subtitle.mp4")
                    add_srt_to_video(output_path, subtitle_path, final_video_with_sub)
                    
                    st.success("🎉 智能对齐视频合成完成！")
                    
                    # 显示结果
                    st.subheader("📺 最终结果")
                    st.video(final_video_with_sub)
                    
                    # 提供下载
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        with open(final_video_with_sub, "rb") as f:
                            st.download_button(
                                "📥 下载带字幕视频",
                                f,
                                file_name="aligned_video_with_subtitle.mp4",
                                mime="video/mp4"
                            )
                    
                    with col2:
                        with open(subtitle_path, "rb") as f:
                            st.download_button(
                                "📥 下载SRT字幕文件",
                                f,
                                file_name="aligned_subtitle.srt",
                                mime="text/plain"
                            )
                    
                    # 显示对齐统计
                    st.subheader("📊 对齐统计信息")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("字幕段落数", alignment_result['total_segments'])
                    
                    with col2:
                        st.metric("视频总时长", f"{alignment_result['total_duration']:.1f}秒")
                    
                    with col3:
                        st.metric("对齐置信度", f"{alignment_result['average_confidence']:.2f}")
                    
                    # 显示前几个段落的对齐结果
                    if alignment_result.get('segments_preview'):
                        st.subheader("🔍 对齐结果预览")
                        for i, segment in enumerate(alignment_result['segments_preview']):
                            with st.expander(f"段落 {i+1}: {segment['start_time']:.1f}s - {segment['end_time']:.1f}s"):
                                st.write(f"**置信度**: {segment['confidence']:.2f}")
                                st.write(f"**内容**: {segment['text']}")
                    
                except Exception as e:
                    st.error(f"❌ 处理过程中出现错误: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

# 侧边栏信息
with st.sidebar:
    st.header("ℹ️ 使用说明")
    
    st.markdown("""
    ### 🎯 智能对齐原理：
    1. **音频转录**：使用Whisper将MP3转录为带时间戳的文本
    2. **文本分割**：智能分割TXT脚本为合理的句子段落
    3. **智能匹配**：通过相似度算法将脚本与转录对齐
    4. **时间映射**：将脚本文本映射到音频的准确时间轴
    
    ### 📋 最佳实践：
    - TXT脚本应与音频内容高度一致
    - 音频质量越好，对齐效果越佳
    - 建议使用清晰的语音录音
    - 脚本中保留适当的标点符号
    
    ### 🔧 技术特点：
    - 支持中文和英文
    - 自动检测语言
    - 智能句子分割
    - 相似度匹配算法
    - 中文字体优化
    """)
    
    st.header("📞 技术支持")
    st.info("如遇问题，请检查：\n1. 音频文件是否完整\n2. 文本编码是否为UTF-8\n3. 脚本内容是否与音频匹配")