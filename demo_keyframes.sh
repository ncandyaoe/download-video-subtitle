#!/bin/bash

# 关键帧提取功能演示脚本

if [ $# -eq 0 ]; then
    echo "用法: $0 <video_url> [method] [parameter]"
    echo ""
    echo "支持所有yt-dlp支持的视频网站，包括："
    echo "  YouTube, Bilibili, Vimeo, Dailymotion, Twitch, Facebook等"
    echo ""
    echo "示例:"
    echo "  # YouTube"
    echo "  $0 'https://www.youtube.com/watch?v=VIDEO_ID' interval 30"
    echo "  $0 'https://youtu.be/VIDEO_ID' count 10"
    echo ""
    echo "  # Bilibili"
    echo "  $0 'https://www.bilibili.com/video/BV1xx411c7mu' count 5"
    echo ""
    echo "  # Vimeo"
    echo "  $0 'https://vimeo.com/148751763' timestamps '15,45,75'"
    echo ""
    echo "  # 其他网站"
    echo "  $0 'https://www.dailymotion.com/video/x2hwqn9' keyframes"
    echo ""
    echo "方法说明:"
    echo "  interval N  - 每N秒截取一帧"
    echo "  count N     - 平均分布截取N帧"
    echo "  timestamps  - 在指定时间点截取（逗号分隔）"
    echo "  keyframes   - 自动检测关键帧"
    echo ""
    echo "完整支持网站列表: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md"
    exit 1
fi

VIDEO_URL="$1"
METHOD="${2:-interval}"
PARAMETER="${3:-30}"
API_BASE="http://localhost:7878"

echo "=== 视频关键帧提取演示 ==="
echo "视频URL: $VIDEO_URL"
echo "提取方法: $METHOD"
echo "参数: $PARAMETER"
echo

# 构建请求JSON
case $METHOD in
    "interval")
        REQUEST_JSON="{\"video_url\": \"$VIDEO_URL\", \"method\": \"interval\", \"interval\": $PARAMETER, \"width\": 1280, \"height\": 720, \"format\": \"jpg\", \"quality\": 85}"
        ;;
    "count")
        REQUEST_JSON="{\"video_url\": \"$VIDEO_URL\", \"method\": \"count\", \"count\": $PARAMETER, \"width\": 1280, \"height\": 720, \"format\": \"jpg\", \"quality\": 85}"
        ;;
    "timestamps")
        # 将逗号分隔的字符串转换为JSON数组
        IFS=',' read -ra TIMESTAMPS <<< "$PARAMETER"
        TIMESTAMP_ARRAY="["
        for i in "${!TIMESTAMPS[@]}"; do
            if [ $i -gt 0 ]; then
                TIMESTAMP_ARRAY+=","
            fi
            TIMESTAMP_ARRAY+="${TIMESTAMPS[$i]}"
        done
        TIMESTAMP_ARRAY+="]"
        REQUEST_JSON="{\"video_url\": \"$VIDEO_URL\", \"method\": \"timestamps\", \"timestamps\": $TIMESTAMP_ARRAY, \"width\": 1280, \"height\": 720, \"format\": \"jpg\", \"quality\": 85}"
        ;;
    "keyframes")
        REQUEST_JSON="{\"video_url\": \"$VIDEO_URL\", \"method\": \"keyframes\", \"width\": 1280, \"height\": 720, \"format\": \"jpg\", \"quality\": 85}"
        ;;
    *)
        echo "错误: 不支持的方法 '$METHOD'"
        exit 1
        ;;
esac

# 1. 启动关键帧提取任务
echo "1. 启动关键帧提取任务..."
RESPONSE=$(curl -s -X POST "$API_BASE/extract_keyframes" \
    -H "Content-Type: application/json" \
    -d "$REQUEST_JSON")

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
echo "2. 监控关键帧提取进度..."
echo "时间戳 | 状态 | 进度 | 已提取帧数 | 消息"
echo "-------|------|------|-----------|------"

while true; do
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/keyframe_status/$TASK_ID")
    
    if [ $? -ne 0 ]; then
        echo "错误: 无法获取任务状态"
        break
    fi
    
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
    MESSAGE=$(echo $STATUS_RESPONSE | jq -r '.message')
    TOTAL_FRAMES=$(echo $STATUS_RESPONSE | jq -r '.total_frames')
    EXTRACTED_FRAMES=$(echo $STATUS_RESPONSE | jq -r '.extracted_frames')
    
    TIMESTAMP=$(date '+%H:%M:%S')
    
    if [ "$TOTAL_FRAMES" != "null" ] && [ "$TOTAL_FRAMES" != "0" ]; then
        FRAME_INFO="${EXTRACTED_FRAMES}/${TOTAL_FRAMES}"
    else
        FRAME_INFO="计算中..."
    fi
    
    echo "$TIMESTAMP | $STATUS | $PROGRESS% | $FRAME_INFO | $MESSAGE"
    
    if [ "$STATUS" = "completed" ]; then
        echo
        echo "✅ 关键帧提取完成！"
        
        # 获取完整结果
        RESULT_RESPONSE=$(curl -s -X GET "$API_BASE/keyframe_result/$TASK_ID")
        
        if [ $? -eq 0 ]; then
            TITLE=$(echo $RESULT_RESPONSE | jq -r '.result.title')
            DURATION=$(echo $RESULT_RESPONSE | jq -r '.result.duration')
            TOTAL_FRAMES=$(echo $RESULT_RESPONSE | jq -r '.result.total_frames')
            METHOD_USED=$(echo $RESULT_RESPONSE | jq -r '.result.method')
            TASK_DIR=$(echo $RESULT_RESPONSE | jq -r '.result.task_dir')
            
            echo "标题: $TITLE"
            echo "时长: ${DURATION}秒"
            echo "提取方法: $METHOD_USED"
            echo "总帧数: $TOTAL_FRAMES"
            echo "文件目录: $TASK_DIR"
            
            # 显示帧信息
            echo
            echo "关键帧详情:"
            echo "索引 | 时间戳 | 文件名 | 大小"
            echo "-----|--------|--------|------"
            
            for i in $(seq 0 $((TOTAL_FRAMES - 1))); do
                FRAME_INFO=$(echo $RESULT_RESPONSE | jq -r ".result.frames[$i]")
                FRAME_TIMESTAMP=$(echo $FRAME_INFO | jq -r '.timestamp')
                FRAME_FILENAME=$(echo $FRAME_INFO | jq -r '.filename')
                FRAME_SIZE=$(echo $FRAME_INFO | jq -r '.size')
                
                if [ "$FRAME_SIZE" != "null" ]; then
                    FRAME_SIZE_KB=$(echo "scale=1; $FRAME_SIZE / 1024" | bc)
                    echo "$i | ${FRAME_TIMESTAMP}s | $FRAME_FILENAME | ${FRAME_SIZE_KB}KB"
                fi
            done
            
            # 测试下载第一帧
            if [ "$TOTAL_FRAMES" -gt 0 ]; then
                echo
                echo "测试下载第一帧..."
                curl -s -X GET "$API_BASE/keyframe_image/$TASK_ID/0" -o "test_frame_0.jpg"
                if [ -f "test_frame_0.jpg" ]; then
                    echo "✅ 第一帧下载成功: test_frame_0.jpg"
                    ls -lh test_frame_0.jpg
                else
                    echo "❌ 第一帧下载失败"
                fi
                
                # 测试下载缩略图
                echo
                echo "测试下载缩略图网格..."
                curl -s -X GET "$API_BASE/keyframe_thumbnail/$TASK_ID" -o "test_thumbnail.jpg"
                if [ -f "test_thumbnail.jpg" ]; then
                    echo "✅ 缩略图下载成功: test_thumbnail.jpg"
                    ls -lh test_thumbnail.jpg
                else
                    echo "❌ 缩略图下载失败"
                fi
            fi
            
        else
            echo "❌ 获取关键帧提取结果失败"
        fi
        break
        
    elif [ "$STATUS" = "failed" ]; then
        echo
        echo "❌ 关键帧提取失败！"
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

# 提供使用建议
echo
echo "💡 使用建议:"
echo "1. 对于长视频，建议使用 interval 方法，间隔30-60秒"
echo "2. 对于短视频预览，建议使用 count 方法，提取5-10帧"
echo "3. 对于特定场景，使用 timestamps 方法指定关键时间点"
echo "4. 对于自动分析，使用 keyframes 方法检测真正的关键帧"
echo
echo "📁 文件位置:"
echo "- 关键帧图片: ./keyframes/$TASK_ID/"
echo "- 可通过API下载: GET /keyframe_image/$TASK_ID/{frame_index}"
echo "- 缩略图网格: GET /keyframe_thumbnail/$TASK_ID"