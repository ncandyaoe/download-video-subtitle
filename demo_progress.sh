#!/bin/bash

# 演示进度查询的脚本

if [ $# -eq 0 ]; then
    echo "用法: $0 <video_url>"
    echo "示例: $0 'https://www.youtube.com/watch?v=VIDEO_ID'"
    exit 1
fi

VIDEO_URL="$1"
API_BASE="http://localhost:7878"

echo "=== 视频字幕转录进度演示 ==="
echo "视频URL: $VIDEO_URL"
echo

# 1. 启动转录任务
echo "1. 启动转录任务..."
RESPONSE=$(curl -s -X POST "$API_BASE/generate_text_from_video" \
    -H "Content-Type: application/json" \
    -d "{\"video_url\": \"$VIDEO_URL\"}")

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
echo "2. 监控任务进度..."
echo "时间戳 | 状态 | 进度 | 消息"
echo "-------|------|------|------"

while true; do
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/task_status/$TASK_ID")
    
    if [ $? -ne 0 ]; then
        echo "错误: 无法获取任务状态"
        break
    fi
    
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
    MESSAGE=$(echo $STATUS_RESPONSE | jq -r '.message')
    
    TIMESTAMP=$(date '+%H:%M:%S')
    echo "$TIMESTAMP | $STATUS | $PROGRESS% | $MESSAGE"
    
    if [ "$STATUS" = "completed" ]; then
        echo
        echo "✅ 转录完成！"
        
        # 显示结果摘要
        TITLE=$(echo $STATUS_RESPONSE | jq -r '.result.title')
        DURATION=$(echo $STATUS_RESPONSE | jq -r '.result.duration')
        LANGUAGE=$(echo $STATUS_RESPONSE | jq -r '.result.language')
        
        echo "标题: $TITLE"
        echo "时长: ${DURATION}秒"
        echo "语言: $LANGUAGE"
        
        # 保存结果到文件
        echo $STATUS_RESPONSE | jq '.result' > "result_${TASK_ID}.json"
        echo "完整结果已保存到: result_${TASK_ID}.json"
        break
        
    elif [ "$STATUS" = "failed" ]; then
        echo
        echo "❌ 转录失败！"
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