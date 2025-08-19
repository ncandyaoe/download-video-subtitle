# 测试文件目录

本目录包含所有与测试相关的文件，包括单元测试、集成测试、调试工具和测试脚本。

## 📁 文件分类

### 🧪 核心测试文件

#### 单元和集成测试
- `test_unit_tests.py` - 单元测试套件
- `test_integration_tests.py` - 集成测试套件
- `test_comprehensive_integration.py` - 综合集成测试

#### 功能模块测试
- `test_video_download.py` - 视频下载功能测试
- `test_download_unit.py` - 下载单元测试
- `test_composition.py` - 视频合成测试
- `test_keyframe_extraction.py` - 关键帧提取测试

#### 字幕相关测试
- `test_chinese_subtitle_display.py` - 中文字幕显示测试
- `test_subtitle_fixes.py` - 字幕修复测试
- `test_txt_subtitle_support.py` - TXT字幕支持测试
- `test_subtitle_validation.py` - 字幕验证测试
- `test_audio_text_alignment.py` - 音频文本对齐测试

#### 系统性能测试
- `test_performance_optimizer.py` - 性能优化器测试
- `test_resource_monitoring.py` - 资源监控测试
- `test_performance_benchmarks.py` - 性能基准测试
- `test_performance_integration.py` - 性能集成测试

#### 错误处理测试
- `test_error_handling.py` - 错误处理测试

#### 特定功能测试
- `test_local_video_composition.py` - 本地视频合成测试
- `test_final_fixes.py` - 最终修复验证测试
- `test_tasks_8_9.py` - 历史任务测试

### 🔧 调试和工具文件

#### 调试工具
- `debug_audio_offset.py` - 音频偏移调试工具
- `debug_aspect_ratio.py` - 宽高比调试工具
- `debug_ffmpeg_command.py` - FFmpeg命令调试工具
- `debug_formats.py` - 格式调试工具
- `debug_pip_command.py` - 画中画命令调试工具
- `debug_side_by_side.py` - 并排显示调试工具

#### 检查工具
- `font_path_checker.py` - 字体路径检查工具

#### 快速测试工具
- `quick_test.py` - 快速测试脚本
- `quick_test_tool.py` - 快速测试工具
- `quick_aspect_test.py` - 快速宽高比测试

#### 测试界面
- `gradio_test_interface.py` - Gradio测试界面

### 🚀 测试运行器

#### Python运行器
- `run_all_tests.py` - 运行所有测试
- `run_integration_tests.py` - 运行集成测试

#### Shell脚本
- `run_tests.sh` - 测试套件运行脚本

### ⚙️ 配置文件

- `pytest.ini` - pytest配置文件

## 🚀 使用方法

### 运行所有测试
```bash
cd test_files
python run_all_tests.py
```

### 运行特定测试
```bash
cd test_files
python -m pytest test_unit_tests.py -v
```

### 运行集成测试
```bash
cd test_files
python run_integration_tests.py
```

### 使用调试工具
```bash
cd test_files
python debug_audio_offset.py
python font_path_checker.py
```

## 📋 注意事项

1. **依赖关系**: 大部分测试文件依赖于根目录的 `api.py` 和其他核心模块
2. **测试数据**: 某些测试需要 `test_videos/`, `test_audio/`, `test_images/` 目录中的测试数据
3. **API服务**: 集成测试需要API服务运行在 `http://localhost:8000` 或 `http://localhost:7878`
4. **权限**: 某些测试可能需要文件系统写权限

## 🔄 维护

- 定期运行测试确保功能正常
- 更新测试用例以覆盖新功能
- 清理过时的测试文件
- 保持测试文档的更新