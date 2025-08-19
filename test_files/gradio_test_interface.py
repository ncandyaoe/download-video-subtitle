#!/usr/bin/env python3
"""
视频处理API Gradio测试界面
提供友好的Web界面来测试各种视频处理功能
"""

import gradio as gr
import requests
import json
import time
import os
import tempfile
from typing import Dict, Any, Optional, Tuple
import pandas as pd

class VideoProcessingTester:
    """视频处理测试器"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
    
    def check_api_health(self) -> Tuple[str, str]:
        """检查API健康状态"""
        try:
            response = self.session.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = "🟢 API服务正常运行"
                details = f"""
**系统状态**: {data.get('status', 'unknown')}
**活跃任务**: {data.get('total_active_tasks', 0)}
**资源状态**: {data.get('resource_status', {}).get('message', 'N/A')}
**CPU使用率**: {data.get('resource_status', {}).get('cpu_percent', 0):.1f}%
**内存使用率**: {data.get('resource_status', {}).get('memory_percent', 0):.1f}%
**磁盘使用率**: {data.get('resource_status', {}).get('disk_percent', 0):.1f}%
"""
                return status, details
            else:
                return "🔴 API服务异常", f"HTTP状态码: {response.status_code}"
        except Exception as e:
            return "🔴 API服务不可用", f"连接错误: {str(e)}"
    
    def test_video_transcription(self, video_url: str) -> Tuple[str, str]:
        """测试视频转录功能"""
        if not video_url.strip():
            return "❌ 错误", "请提供视频URL"
        
        try:
            # 启动转录任务
            response = self.session.post(
                f"{self.api_base_url}/generate_text_from_video",
                json={"video_url": video_url},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                
                result = f"✅ 转录任务已启动\n**任务ID**: {task_id}\n**状态**: {data.get('status')}\n**消息**: {data.get('message')}"
                
                # 提供状态查询信息
                status_info = f"\n\n**查询状态**: 使用任务ID `{task_id}` 在下方查询进度"
                
                return "成功", result + status_info
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return "❌ 失败", f"HTTP {response.status_code}: {error_data.get('detail', response.text)}"
                
        except Exception as e:
            return "❌ 异常", f"请求失败: {str(e)}"
    
    def test_video_download(self, video_url: str, quality: str, format_type: str) -> Tuple[str, str]:
        """测试视频下载功能"""
        if not video_url.strip():
            return "❌ 错误", "请提供视频URL"
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/download_video",
                json={
                    "video_url": video_url,
                    "quality": quality,
                    "format": format_type
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                
                result = f"✅ 下载任务已启动\n**任务ID**: {task_id}\n**质量**: {data.get('quality')}\n**格式**: {data.get('format')}"
                status_info = f"\n\n**查询状态**: 使用任务ID `{task_id}` 在下方查询进度"
                
                return "成功", result + status_info
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return "❌ 失败", f"HTTP {response.status_code}: {error_data.get('detail', response.text)}"
                
        except Exception as e:
            return "❌ 异常", f"请求失败: {str(e)}"
    
    def test_keyframe_extraction(self, video_url: str, method: str, interval: int, count: int) -> Tuple[str, str]:
        """测试关键帧提取功能"""
        if not video_url.strip():
            return "❌ 错误", "请提供视频URL"
        
        try:
            response = self.session.post(
                f"{self.api_base_url}/extract_keyframes",
                json={
                    "video_url": video_url,
                    "method": method,
                    "interval": interval,
                    "count": count,
                    "width": 1280,
                    "height": 720,
                    "format": "jpg",
                    "quality": 85
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                
                result = f"✅ 关键帧提取任务已启动\n**任务ID**: {task_id}\n**方法**: {method}\n**参数**: {interval if method == 'interval' else count}"
                status_info = f"\n\n**查询状态**: 使用任务ID `{task_id}` 在下方查询进度"
                
                return "成功", result + status_info
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return "❌ 失败", f"HTTP {response.status_code}: {error_data.get('detail', response.text)}"
                
        except Exception as e:
            return "❌ 异常", f"请求失败: {str(e)}"
    
    def test_video_composition(self, composition_type: str, video_urls: str, audio_url: str, subtitle_file) -> Tuple[str, str]:
        """测试视频合成功能"""
        if not video_urls.strip():
            return "❌ 错误", "请提供至少一个视频URL"
        
        # 解析视频URL列表
        urls = [url.strip() for url in video_urls.split('\n') if url.strip()]
        if not urls:
            return "❌ 错误", "请提供有效的视频URL"
        
        try:
            # 构建请求数据
            videos = [{"video_url": url} for url in urls]
            request_data = {
                "composition_type": composition_type,
                "videos": videos,
                "output_format": "mp4"
            }
            
            # 添加音频文件（如果提供）
            if audio_url and audio_url.strip():
                request_data["audio_file"] = audio_url.strip()
            
            # 添加字幕文件（如果上传）
            if subtitle_file is not None:
                # 保存上传的字幕文件到临时位置
                with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
                    f.write(subtitle_file.decode('utf-8') if isinstance(subtitle_file, bytes) else str(subtitle_file))
                    temp_subtitle_path = f.name
                request_data["subtitle_file"] = temp_subtitle_path
            
            response = self.session.post(
                f"{self.api_base_url}/compose_video",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                
                result = f"✅ 视频合成任务已启动\n**任务ID**: {task_id}\n**合成类型**: {composition_type}\n**视频数量**: {len(videos)}"
                status_info = f"\n\n**查询状态**: 使用任务ID `{task_id}` 在下方查询进度"
                
                return "成功", result + status_info
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return "❌ 失败", f"HTTP {response.status_code}: {error_data.get('detail', response.text)}"
                
        except Exception as e:
            return "❌ 异常", f"请求失败: {str(e)}"
    
    def query_task_status(self, task_id: str) -> Tuple[str, str]:
        """查询任务状态"""
        if not task_id.strip():
            return "❌ 错误", "请提供任务ID"
        
        task_id = task_id.strip()
        
        try:
            # 尝试不同的状态查询端点
            endpoints = [
                f"/composition_status/{task_id}",
                f"/transcription_status/{task_id}",
                f"/download_status/{task_id}",
                f"/keyframe_status/{task_id}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.api_base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        status = data.get('status', 'unknown')
                        progress = data.get('progress', 0)
                        message = data.get('message', '')
                        
                        result = f"**任务ID**: {task_id}\n**状态**: {status}\n**进度**: {progress}%\n**消息**: {message}"
                        
                        # 如果任务完成，显示结果信息
                        if status == 'completed' and 'result' in data:
                            result_data = data['result']
                            result += f"\n\n**结果信息**:\n"
                            for key, value in result_data.items():
                                result += f"- **{key}**: {value}\n"
                        
                        # 如果任务失败，显示错误信息
                        elif status == 'failed' and 'error' in data:
                            result += f"\n\n**错误信息**: {data['error']}"
                        
                        status_icon = {
                            'processing': '🔄',
                            'completed': '✅',
                            'failed': '❌',
                            'downloading': '⬇️',
                            'extracting': '🖼️'
                        }.get(status, '❓')
                        
                        return f"{status_icon} {status.title()}", result
                        
                except requests.exceptions.RequestException:
                    continue
            
            return "❓ 未找到", f"未找到任务ID: {task_id}"
            
        except Exception as e:
            return "❌ 异常", f"查询失败: {str(e)}"
    
    def get_system_status(self) -> Tuple[str, str]:
        """获取系统状态"""
        try:
            # 获取资源状态
            resource_response = self.session.get(f"{self.api_base_url}/system/resources", timeout=5)
            error_response = self.session.get(f"{self.api_base_url}/system/errors/stats", timeout=5)
            cleanup_response = self.session.get(f"{self.api_base_url}/system/cleanup/stats", timeout=5)
            
            result = "## 系统状态概览\n\n"
            
            # 资源状态
            if resource_response.status_code == 200:
                resource_data = resource_response.json()
                result += f"### 📊 资源使用情况\n"
                result += f"- **CPU使用率**: {resource_data.get('cpu_percent', 0):.1f}%\n"
                result += f"- **内存使用率**: {resource_data.get('memory_percent', 0):.1f}%\n"
                result += f"- **磁盘使用率**: {resource_data.get('disk_percent', 0):.1f}%\n"
                result += f"- **剩余磁盘空间**: {resource_data.get('free_disk_gb', 0):.2f}GB\n"
                result += f"- **活跃任务数**: {resource_data.get('active_tasks', 0)}/{resource_data.get('max_concurrent_tasks', 0)}\n\n"
            
            # 错误统计
            if error_response.status_code == 200:
                error_data = error_response.json()
                result += f"### ⚠️ 错误统计\n"
                result += f"- **总错误数**: {error_data.get('total_errors', 0)}\n"
                result += f"- **最近错误数**: {error_data.get('recent_errors_count', 0)}\n"
                
                most_common = error_data.get('most_common_errors', [])
                if most_common:
                    result += f"- **常见错误类型**:\n"
                    for error_type, count in most_common[:3]:
                        result += f"  - {error_type}: {count}次\n"
                result += "\n"
            
            # 清理统计
            if cleanup_response.status_code == 200:
                cleanup_data = cleanup_response.json()
                cleanup_stats = cleanup_data.get('cleanup_stats', {})
                result += f"### 🧹 清理统计\n"
                result += f"- **已清理过期任务**: {cleanup_stats.get('expired_tasks_cleaned', 0)}\n"
                result += f"- **已清理临时文件**: {cleanup_stats.get('temp_files_cleaned', 0)}\n"
                result += f"- **已终止进程**: {cleanup_stats.get('processes_terminated', 0)}\n"
                result += f"- **活跃进程数**: {cleanup_data.get('active_processes', 0)}\n"
                result += f"- **清理服务运行**: {'✅' if cleanup_data.get('cleanup_running', False) else '❌'}\n"
            
            return "📈 系统状态", result
            
        except Exception as e:
            return "❌ 获取失败", f"无法获取系统状态: {str(e)}"
    
    def get_all_tasks(self) -> str:
        """获取所有任务列表"""
        try:
            response = self.session.get(f"{self.api_base_url}/system/tasks", timeout=5)
            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', {})
                summary = data.get('summary', {})
                
                result = "## 📋 所有任务列表\n\n"
                result += f"**总任务数**: {summary.get('total_tasks', 0)}\n"
                result += f"**活跃任务数**: {summary.get('active_tasks', 0)}\n\n"
                
                # 显示各类任务
                task_types = [
                    ('composition_tasks', '🎬 合成任务'),
                    ('transcription_tasks', '📝 转录任务'),
                    ('download_tasks', '⬇️ 下载任务'),
                    ('keyframe_tasks', '🖼️ 关键帧任务')
                ]
                
                for task_type, title in task_types:
                    type_tasks = tasks.get(task_type, {})
                    if type_tasks:
                        result += f"### {title} ({len(type_tasks)}个)\n"
                        for task_id, task_info in list(type_tasks.items())[:5]:  # 只显示前5个
                            status = task_info.get('status', 'unknown')
                            progress = task_info.get('progress', 0)
                            result += f"- **{task_id[:8]}...**: {status} ({progress}%)\n"
                        
                        if len(type_tasks) > 5:
                            result += f"- ... 还有 {len(type_tasks) - 5} 个任务\n"
                        result += "\n"
                
                return result
            else:
                return f"❌ 获取任务列表失败: HTTP {response.status_code}"
                
        except Exception as e:
            return f"❌ 获取任务列表异常: {str(e)}"

# 创建测试器实例
tester = VideoProcessingTester()

# 创建Gradio界面
def create_interface():
    """创建Gradio测试界面"""
    
    with gr.Blocks(title="视频处理API测试界面", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🎬 视频处理API测试界面")
        gr.Markdown("这个界面可以帮助您快速测试视频处理API的各种功能")
        
        # API状态检查
        with gr.Tab("🏠 系统状态"):
            gr.Markdown("## API服务状态检查")
            
            with gr.Row():
                health_btn = gr.Button("🔍 检查API健康状态", variant="primary")
                system_btn = gr.Button("📊 获取系统状态", variant="secondary")
                tasks_btn = gr.Button("📋 查看所有任务", variant="secondary")
            
            health_status = gr.Textbox(label="API状态", interactive=False)
            health_details = gr.Markdown()
            
            health_btn.click(
                fn=tester.check_api_health,
                outputs=[health_status, health_details]
            )
            
            system_btn.click(
                fn=tester.get_system_status,
                outputs=[health_status, health_details]
            )
            
            tasks_btn.click(
                fn=tester.get_all_tasks,
                outputs=[health_details]
            )
        
        # 视频转录测试
        with gr.Tab("📝 视频转录"):
            gr.Markdown("## 视频转录功能测试")
            gr.Markdown("输入视频URL来测试转录功能")
            
            transcription_url = gr.Textbox(
                label="视频URL",
                placeholder="https://www.youtube.com/watch?v=...",
                lines=1
            )
            
            transcription_btn = gr.Button("🎤 开始转录", variant="primary")
            transcription_status = gr.Textbox(label="状态", interactive=False)
            transcription_result = gr.Markdown()
            
            transcription_btn.click(
                fn=tester.test_video_transcription,
                inputs=[transcription_url],
                outputs=[transcription_status, transcription_result]
            )
        
        # 视频下载测试
        with gr.Tab("⬇️ 视频下载"):
            gr.Markdown("## 视频下载功能测试")
            
            with gr.Row():
                download_url = gr.Textbox(
                    label="视频URL",
                    placeholder="https://www.youtube.com/watch?v=...",
                    scale=2
                )
                download_quality = gr.Dropdown(
                    choices=["best", "worst", "1080p", "720p", "480p"],
                    value="720p",
                    label="质量",
                    scale=1
                )
                download_format = gr.Dropdown(
                    choices=["mp4", "webm", "mkv"],
                    value="mp4",
                    label="格式",
                    scale=1
                )
            
            download_btn = gr.Button("📥 开始下载", variant="primary")
            download_status = gr.Textbox(label="状态", interactive=False)
            download_result = gr.Markdown()
            
            download_btn.click(
                fn=tester.test_video_download,
                inputs=[download_url, download_quality, download_format],
                outputs=[download_status, download_result]
            )
        
        # 关键帧提取测试
        with gr.Tab("🖼️ 关键帧提取"):
            gr.Markdown("## 关键帧提取功能测试")
            
            keyframe_url = gr.Textbox(
                label="视频URL",
                placeholder="https://www.youtube.com/watch?v=...",
                lines=1
            )
            
            with gr.Row():
                keyframe_method = gr.Dropdown(
                    choices=["interval", "count", "keyframes"],
                    value="interval",
                    label="提取方法"
                )
                keyframe_interval = gr.Number(
                    value=30,
                    label="间隔(秒)",
                    visible=True
                )
                keyframe_count = gr.Number(
                    value=10,
                    label="数量",
                    visible=False
                )
            
            def update_keyframe_inputs(method):
                if method == "interval":
                    return gr.update(visible=True), gr.update(visible=False)
                elif method == "count":
                    return gr.update(visible=False), gr.update(visible=True)
                else:
                    return gr.update(visible=False), gr.update(visible=False)
            
            keyframe_method.change(
                fn=update_keyframe_inputs,
                inputs=[keyframe_method],
                outputs=[keyframe_interval, keyframe_count]
            )
            
            keyframe_btn = gr.Button("🎞️ 提取关键帧", variant="primary")
            keyframe_status = gr.Textbox(label="状态", interactive=False)
            keyframe_result = gr.Markdown()
            
            keyframe_btn.click(
                fn=tester.test_keyframe_extraction,
                inputs=[keyframe_url, keyframe_method, keyframe_interval, keyframe_count],
                outputs=[keyframe_status, keyframe_result]
            )
        
        # 视频合成测试
        with gr.Tab("🎬 视频合成"):
            gr.Markdown("## 视频合成功能测试")
            
            composition_type = gr.Dropdown(
                choices=[
                    "concat",
                    "audio_video_subtitle", 
                    "pip",
                    "side_by_side",
                    "slideshow",
                    "multi_overlay",
                    "side_by_side_audio_mix"
                ],
                value="concat",
                label="合成类型"
            )
            
            composition_urls = gr.Textbox(
                label="视频URL列表 (每行一个)",
                placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
                lines=3
            )
            
            composition_audio = gr.Textbox(
                label="音频URL (可选)",
                placeholder="https://example.com/audio.mp3",
                lines=1
            )
            
            composition_subtitle = gr.File(
                label="字幕文件 (可选, .srt格式)",
                file_types=[".srt"]
            )
            
            composition_btn = gr.Button("🎭 开始合成", variant="primary")
            composition_status = gr.Textbox(label="状态", interactive=False)
            composition_result = gr.Markdown()
            
            composition_btn.click(
                fn=tester.test_video_composition,
                inputs=[composition_type, composition_urls, composition_audio, composition_subtitle],
                outputs=[composition_status, composition_result]
            )
        
        # 任务状态查询
        with gr.Tab("🔍 任务查询"):
            gr.Markdown("## 任务状态查询")
            gr.Markdown("输入任务ID来查询任务的执行状态和结果")
            
            with gr.Row():
                query_task_id = gr.Textbox(
                    label="任务ID",
                    placeholder="输入从其他标签页获得的任务ID",
                    lines=1,
                    scale=3
                )
                query_btn = gr.Button("🔎 查询状态", variant="primary", scale=1)
                refresh_btn = gr.Button("🔄 刷新", variant="secondary", scale=1)
            
            with gr.Row():
                query_status = gr.Textbox(label="任务状态", interactive=False, scale=1)
                query_progress = gr.Textbox(label="进度", interactive=False, scale=1)
            
            query_result = gr.Markdown(label="详细信息")
            
            # 自动刷新功能
            with gr.Row():
                auto_refresh = gr.Checkbox(label="启用自动刷新 (每10秒)", value=False)
                clear_btn = gr.Button("🗑️ 清空", variant="secondary")
            
            # 任务历史记录
            gr.Markdown("### 📋 最近查询的任务")
            task_history = gr.Dataframe(
                headers=["任务ID", "状态", "进度", "最后更新"],
                datatype=["str", "str", "str", "str"],
                row_count=5,
                col_count=4,
                interactive=False,
                label="任务历史"
            )
            
            # 存储任务历史的状态
            task_history_state = gr.State([])
            
            def query_with_history(task_id, history):
                if not task_id.strip():
                    return "", "", "请输入任务ID", history, history
                
                status_text, result_text = tester.query_task_status(task_id.strip())
                
                # 解析进度信息
                progress = "0%"
                if "进度:" in result_text:
                    try:
                        progress_line = [line for line in result_text.split('\n') if '进度:' in line][0]
                        progress = progress_line.split('进度:')[1].strip().split('\n')[0]
                    except:
                        progress = "未知"
                
                # 更新历史记录
                import time
                current_time = time.strftime("%H:%M:%S")
                new_entry = [task_id.strip()[:12] + "...", status_text, progress, current_time]
                
                # 添加到历史记录（最多保留10条）
                history = history or []
                history.insert(0, new_entry)
                if len(history) > 10:
                    history = history[:10]
                
                return status_text, progress, result_text, history, history
            
            def auto_refresh_status(task_id, should_refresh, history):
                if should_refresh and task_id.strip():
                    return query_with_history(task_id.strip(), history)
                return "", "", "", history, history
            
            def clear_all():
                return "", "", "", [], []
            
            # 绑定事件
            query_btn.click(
                fn=query_with_history,
                inputs=[query_task_id, task_history_state],
                outputs=[query_status, query_progress, query_result, task_history, task_history_state]
            )
            
            refresh_btn.click(
                fn=query_with_history,
                inputs=[query_task_id, task_history_state],
                outputs=[query_status, query_progress, query_result, task_history, task_history_state]
            )
            
            clear_btn.click(
                fn=clear_all,
                outputs=[query_task_id, query_status, query_progress, query_result, task_history_state]
            )
            
            # 设置定时器
            refresh_timer = gr.Timer(10)
            refresh_timer.tick(
                fn=auto_refresh_status,
                inputs=[query_task_id, auto_refresh, task_history_state],
                outputs=[query_status, query_progress, query_result, task_history, task_history_state]
            )
        
        # 使用说明
        with gr.Tab("📖 使用说明"):
            gr.Markdown("""
            # 📖 使用说明
            
            ## 🚀 快速开始
            
            1. **检查API状态**: 首先在"系统状态"标签页检查API服务是否正常运行
            2. **选择功能**: 根据需要选择相应的功能标签页
            3. **输入参数**: 填写必要的参数（如视频URL等）
            4. **启动任务**: 点击相应的按钮启动任务
            5. **查询状态**: 使用返回的任务ID在"任务查询"标签页查询进度
            
            ## 🎯 功能说明
            
            ### 📝 视频转录
            - 支持YouTube、Bilibili等主流视频网站
            - 自动识别语言并转录为文字
            - 支持SRT字幕格式输出
            
            ### ⬇️ 视频下载
            - 支持多种质量选项 (480p, 720p, 1080p, best, worst)
            - 支持多种格式 (mp4, webm, mkv)
            - 自动选择最佳下载源
            
            ### 🖼️ 关键帧提取
            - **间隔模式**: 按时间间隔提取关键帧
            - **数量模式**: 提取指定数量的关键帧
            - **关键帧模式**: 自动检测场景变化提取关键帧
            
            ### 🎬 视频合成
            - **concat**: 视频拼接 - 将多个视频按顺序连接
            - **audio_video_subtitle**: 音频视频字幕合成 - 为视频添加音频和字幕
            - **pip**: 画中画 - 将一个视频叠加到另一个视频上
            - **side_by_side**: 并排显示 - 多个视频并排显示
            - **slideshow**: 幻灯片 - 将图片制作成视频
            
            ## ⚠️ 注意事项
            
            - 确保API服务正在运行 (默认端口8000)
            - 视频URL必须是可访问的公开链接
            - 大文件处理可能需要较长时间
            - 建议在处理大任务前检查系统资源状态
            - 任务完成后可以通过API下载结果文件
            
            ## 🔧 故障排除
            
            1. **API不可用**: 检查API服务是否启动，端口是否正确
            2. **任务失败**: 查看错误信息，检查输入参数是否正确
            3. **处理缓慢**: 检查系统资源使用情况，必要时等待其他任务完成
            4. **文件无法访问**: 确保视频URL有效且可访问
            
            ## 📞 技术支持
            
            如果遇到问题，可以：
            - 查看"系统状态"页面的错误统计
            - 检查任务详细状态信息
            - 查看API服务日志
            """)
    
    return interface

if __name__ == "__main__":
    # 创建并启动界面
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )