#!/bin/bash

echo "=== API 性能测试 ==="

# 测试基础健康检查
echo "1. 健康检查性能测试："
for i in {1..5}; do
    echo -n "  测试 $i: "
    time curl -s -X GET "http://localhost:7878/health" > /dev/null
done
echo

# 创建测试任务
echo "2. 创建测试任务："
RESPONSE=$(curl -s -X POST "http://localhost:7878/generate_text_from_video" \
    -H "Content-Type: application/json" \
    -d '{"video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}')

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "任务ID: $TASK_ID"
echo

# 等待任务完成
echo "3. 等待任务完成..."
sleep 10

# 测试状态查询性能
echo "4. 状态查询性能测试："
for i in {1..5}; do
    echo -n "  测试 $i: "
    time curl -s -X GET "http://localhost:7878/task_status/$TASK_ID" > /dev/null
done
echo

# 测试结果获取性能
echo "5. 结果获取性能测试："
for i in {1..3}; do
    echo -n "  测试 $i: "
    time curl -s -X GET "http://localhost:7878/task_result/$TASK_ID" > /dev/null 2>/dev/null || echo "任务已清理"
done

echo "=== 测试完成 ==="