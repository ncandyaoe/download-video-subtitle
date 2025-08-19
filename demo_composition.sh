#!/bin/bash

# 视频合成功能演示脚本
# 演示音频视频字幕三合一合成功能

API_BASE="http://localhost:7878"

echo "🎬 视频合成功能演示"
echo "===================="

# 检查服务器状态
echo "📡 检查API服务器状态..."
if ! curl -s "$API_BASE/health" > /dev/null; then
    echo "❌ API服务器未运行，请先启动服务器:"
    echo "   python api.py"
    exit 1
fi

echo "✅ API服务器运行正常"

# 演示参数（请根据实际情况修改文件路径）
VIDEO_FILE="/path/to/your/video.mp4"
AUDIO_FILE="/path/to/your/audio.mp3"
SUBTITLE_FILE="/path/to/your/subtitle.srt"

echo ""
echo "📝 演示参数:"
echo "   视频文件: $VIDEO_FILE"
echo "   音频文件: $AUDIO_FILE"
echo "   字幕文件: $SUBTITLE_FILE"
echo ""

# 检查文件是否存在
if [ ! -f "$VIDEO_FILE" ]; then
    echo "❌ 视频文件不存在: $VIDEO_FILE"
    echo "请修改脚本中的文件路径"
    exit 1
fi

if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ 音频文件不存在: $AUDIO_FILE"
    echo "请修改脚本中的文件路径"
    exit 1
fi

# 字幕文件是可选的
SUBTITLE_PARAM=""
if [ -f "$SUBTITLE_FILE" ]; then
    SUBTITLE_PARAM='"subtitle_file": "'$SUBTITLE_FILE'",'
    echo "✅ 将包含字幕文件"
else
    echo "⚠️  字幕文件不存在，将跳过字幕"
fi

echo ""
echo "🚀 启动音频视频字幕合成任务..."

# 构建JSON请求
JSON_DATA='{
  "composition_type": "audio_video_subtitle",
  "videos": [
    {
      "video_url": "'$VIDEO_FILE'"
    }
  ],
  "audio_file": "'$AUDIO_FILE'",
  '$SUBTITLE_PARAM'
  "output_format": "mp4",
  "output_quality": "720p"
}'

# 启动任务
RESPONSE=$(curl -s -X POST "$API_BASE/compose_video" \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA")

# 检查响应
if [ $? -ne 0 ]; then
    echo "❌ 请求失败"
    exit 1
fi

# 提取任务ID
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
    echo "❌ 启动任务失败:"
    echo "$RESPONSE"
    exit 1
fi

echo "✅ 任务启动成功，任务ID: $TASK_ID"

# 监控进度
echo ""
echo "📊 监控任务进度..."
while true; do
    STATUS_RESPONSE=$(curl -s "$API_BASE/composition_status/$TASK_ID")
    
    if [ $? -ne 0 ]; then
        echo "❌ 查询状态失败"
        exit 1
    fi
    
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['status'])" 2>/dev/null)
    PROGRESS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['progress'])" 2>/dev/null)
    MESSAGE=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['message'])" 2>/dev/null)
    
    echo "📈 进度: ${PROGRESS}% - $MESSAGE"
    
    if [ "$STATUS" = "completed" ]; then
        echo "🎉 任务完成！"
        break
    elif [ "$STATUS" = "failed" ]; then
        ERROR=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', '未知错误'))" 2>/dev/null)
        echo "❌ 任务失败: $ERROR"
        exit 1
    fi
    
    sleep 2
done

# 获取结果
echo ""
echo "📋 获取合成结果..."
RESULT_RESPONSE=$(curl -s "$API_BASE/composition_result/$TASK_ID")

if [ $? -ne 0 ]; then
    echo "❌ 获取结果失败"
    exit 1
fi

# 解析结果
OUTPUT_FILE=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['output_file_path'])" 2>/dev/null)
FILE_SIZE=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['result']['file_size'] / 1024 / 1024:.1f}\")" 2>/dev/null)
DURATION=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['result']['duration']:.1f}\")" 2>/dev/null)
RESOLUTION=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['resolution'])" 2>/dev/null)
PROCESSING_TIME=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['result']['processing_time']:.1f}\")" 2>/dev/null)

echo "✅ 合成结果:"
echo "   输出文件: $OUTPUT_FILE"
echo "   文件大小: ${FILE_SIZE} MB"
echo "   视频时长: ${DURATION} 秒"
echo "   分辨率: $RESOLUTION"
echo "   处理时间: ${PROCESSING_TIME} 秒"

# 询问是否下载
echo ""
read -p "💾 是否下载合成的视频文件？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📥 开始下载..."
    OUTPUT_FILENAME="composed_video_${TASK_ID}.mp4"
    
    curl -s "$API_BASE/composition_file/$TASK_ID" -o "$OUTPUT_FILENAME"
    
    if [ $? -eq 0 ]; then
        echo "✅ 文件下载完成: $OUTPUT_FILENAME"
    else
        echo "❌ 下载失败"
    fi
fi

echo ""
echo "🎉 演示完成！"