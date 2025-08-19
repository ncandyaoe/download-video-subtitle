#!/bin/bash

# 视频下载功能演示脚本

if [ $# -eq 0 ]; then
    echo "用法: $0 <video_url> [quality] [format]"
    echo "示例: $0 'https://www.youtube.com/watch?v=VIDEO_ID' 720p mp4"
    echo "质量选项: best, worst, 1080p, 720p, 480p"
    echo "格式选项: mp4, webm, mkv"
    exit 1
fi

VIDEO_URL="$1"
QUALITY="${2:-best}"
FORMAT="${3:-mp4}"
API_BASE="http://localhost:7878"

echo "=== 视频下载功能演示 ==="
echo "视频URL: $VIDEO_URL"
echo "质量: $QUALITY"
echo "格式: $FORMAT"
echo

# 1. 启动下载任务
echo "1. 启动下载任务..."
RESPONSE=$(curl -s -X POST "$API_BASE/download_video" \
    -H "Content-Type: application/json" \
    -d "{\"video_url\": \"$VIDEO_URL\", \"quality\": \"$QUALITY\", \"format\": \"$FORMAT\"}")

echo "响应: $RESPONSE"

# 提取task_id
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

if [ "$TASK_ID" = "null" ] || [ -z "$TASK_ID" ]; then
    echo "错误: 无法获取task_id"
    exit 1
fi

echo "任务ID: $TASK_ID"
echo

# 2. 轮询任务状态
echo "2. 监控下载进度..."
echo "时间戳 | 状态 | 进度 | 文件大小 | 消息"
echo "-------|------|------|----------|------"

while true; do
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/download_status/$TASK_ID")
    
    if [ $? -ne 0 ]; then
        echo "错误: 无法获取任务状态"
        break
    fi
    
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
    MESSAGE=$(echo $STATUS_RESPONSE | jq -r '.message')
    FILE_SIZE=$(echo $STATUS_RESPONSE | jq -r '.file_size')
    DOWNLOADED_SIZE=$(echo $STATUS_RESPONSE | jq -r '.downloaded_size')
    
    TIMESTAMP=$(date '+%H:%M:%S')
    
    if [ "$FILE_SIZE" != "null" ] && [ "$FILE_SIZE" != "0" ]; then
        FILE_SIZE_MB=$(echo "scale=1; $FILE_SIZE / 1024 / 1024" | bc)
        if [ "$DOWNLOADED_SIZE" != "null" ] && [ "$DOWNLOADED_SIZE" != "0" ]; then
            DOWNLOADED_MB=$(echo "scale=1; $DOWNLOADED_SIZE / 1024 / 1024" | bc)
            SIZE_INFO="${DOWNLOADED_MB}MB/${FILE_SIZE_MB}MB"
        else
            SIZE_INFO="${FILE_SIZE_MB}MB"
        fi
    else
        SIZE_INFO="计算中..."
    fi
    
    echo "$TIMESTAMP | $STATUS | $PROGRESS% | $SIZE_INFO | $MESSAGE"
    
    if [ "$STATUS" = "completed" ]; then
        echo
        echo "✅ 下载完成！"
        
        # 获取完整结果
        RESULT_RESPONSE=$(curl -s -X GET "$API_BASE/download_result/$TASK_ID")
        
        if [ $? -eq 0 ]; then
            TITLE=$(echo $RESULT_RESPONSE | jq -r '.result.title')
            DURATION=$(echo $RESULT_RESPONSE | jq -r '.result.duration')
            FILE_PATH=$(echo $RESULT_RESPONSE | jq -r '.result.file_path')
            ACTUAL_SIZE=$(echo $RESULT_RESPONSE | jq -r '.result.file_size')
            
            REQUESTED_QUALITY=$(echo $RESULT_RESPONSE | jq -r '.result.requested_quality')
            ACTUAL_RESOLUTION=$(echo $RESULT_RESPONSE | jq -r '.result.actual_resolution')
            REQUESTED_FORMAT=$(echo $RESULT_RESPONSE | jq -r '.result.requested_format')
            ACTUAL_FORMAT=$(echo $RESULT_RESPONSE | jq -r '.result.actual_format')
            FORMAT_ID=$(echo $RESULT_RESPONSE | jq -r '.result.format_id')
            AVAILABLE_FORMATS=$(echo $RESULT_RESPONSE | jq -r '.result.available_formats_count')
            
            echo "标题: $TITLE"
            echo "时长: ${DURATION}秒"
            echo "文件路径: $FILE_PATH"
            echo "文件大小: $(echo "scale=1; $ACTUAL_SIZE / 1024 / 1024" | bc)MB"
            echo "请求质量: $REQUESTED_QUALITY -> 实际分辨率: $ACTUAL_RESOLUTION"
            echo "请求格式: $REQUESTED_FORMAT -> 实际格式: $ACTUAL_FORMAT"
            echo "格式ID: $FORMAT_ID"
            echo "可用格式数: $AVAILABLE_FORMATS"
            
            # 验证文件是否存在
            if [ -f "$FILE_PATH" ]; then
                echo "✅ 文件验证成功"
                echo "文件信息:"
                ls -lh "$FILE_PATH"
            else
                echo "❌ 文件验证失败: 文件不存在"
            fi
        else
            echo "❌ 获取下载结果失败"
        fi
        break
        
    elif [ "$STATUS" = "failed" ]; then
        echo
        echo "❌ 下载失败！"
        ERROR=$(echo $STATUS_RESPONSE | jq -r '.error')
        echo "错误: $ERROR"
        break
        
    elif [ "$STATUS" = "null" ]; then
        echo "错误: 任务不存在或已过期"
        break
    fi
    
    # 等待5秒后继续检查
    sleep 5
done

echo
echo "=== 演示结束 ==="