#!/bin/bash

# 测试运行脚本

echo "=== 视频下载功能测试套件 ==="
echo

# 检查服务是否运行
echo "1. 检查服务状态..."
if curl -s -f "http://localhost:7878/health" > /dev/null; then
    echo "✅ 服务正在运行"
else
    echo "❌ 服务未运行，请先启动服务"
    echo "启动命令: python run.py 或 docker-compose up -d"
    exit 1
fi

echo

# 安装测试依赖
echo "2. 检查测试依赖..."
if ! python -c "import pytest" 2>/dev/null; then
    echo "安装pytest..."
    pip install pytest
fi

if ! python -c "import requests" 2>/dev/null; then
    echo "安装requests..."
    pip install requests
fi

echo "✅ 测试依赖已就绪"
echo

# 运行单元测试
echo "3. 运行单元测试..."
echo "================================"
python -m pytest test_download_unit.py -v
UNIT_TEST_RESULT=$?
echo

# 运行集成测试（可选，需要真实网络连接）
echo "4. 运行集成测试..."
echo "================================"
echo "注意: 集成测试需要网络连接和较长时间"
read -p "是否运行集成测试? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python -m pytest test_video_download.py::TestVideoDownload::test_download_video_success -v -s
    INTEGRATION_TEST_RESULT=$?
else
    echo "跳过集成测试"
    INTEGRATION_TEST_RESULT=0
fi

echo

# 运行API测试
echo "5. 运行API基础测试..."
echo "================================"
python -m pytest test_video_download.py::TestVideoDownload::test_health_check -v
python -m pytest test_video_download.py::TestVideoDownload::test_download_video_invalid_url -v
python -m pytest test_video_download.py::TestVideoDownload::test_download_video_invalid_quality -v
python -m pytest test_video_download.py::TestVideoDownload::test_download_video_invalid_format -v
API_TEST_RESULT=$?

echo

# 测试结果总结
echo "=== 测试结果总结 ==="
if [ $UNIT_TEST_RESULT -eq 0 ]; then
    echo "✅ 单元测试: 通过"
else
    echo "❌ 单元测试: 失败"
fi

if [ $INTEGRATION_TEST_RESULT -eq 0 ]; then
    echo "✅ 集成测试: 通过"
else
    echo "❌ 集成测试: 失败"
fi

if [ $API_TEST_RESULT -eq 0 ]; then
    echo "✅ API测试: 通过"
else
    echo "❌ API测试: 失败"
fi

echo

# 提供手动测试选项
echo "6. 手动测试选项..."
echo "运行手动测试: python test_video_download.py"
echo "运行下载演示: ./demo_download.sh 'https://www.youtube.com/watch?v=jNQXAC9IVRw'"
echo "关键帧提取测试: python test_keyframes_quick.py"
echo "多网站支持测试: python test_keyframes_multisite.py"
echo "检查特定网站: python check_site_support.py 'VIDEO_URL'"

# 总体结果
TOTAL_RESULT=$((UNIT_TEST_RESULT + INTEGRATION_TEST_RESULT + API_TEST_RESULT))
if [ $TOTAL_RESULT -eq 0 ]; then
    echo
    echo "🎉 所有测试通过！"
    exit 0
else
    echo
    echo "⚠️  部分测试失败，请检查日志"
    exit 1
fi