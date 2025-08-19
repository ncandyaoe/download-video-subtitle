#!/bin/bash

# 视频字幕服务监控脚本

echo "=== 视频字幕服务监控 ==="
echo "时间: $(date)"
echo

# 检查容器状态
echo "1. 容器状态:"
docker ps -a | grep subtitle-service
echo

# 检查容器资源使用情况
echo "2. 资源使用情况:"
docker stats --no-stream subtitle-service 2>/dev/null || echo "容器未运行"
echo

# 检查最近的日志
echo "3. 最近日志 (最后20行):"
docker logs subtitle-service --tail 20 2>/dev/null || echo "无法获取日志"
echo

# 检查服务健康状态
echo "4. 服务健康检查:"
curl -s -X GET "http://localhost:7878/" | jq . 2>/dev/null || echo "服务不可访问"
echo

# 检查磁盘空间
echo "5. 磁盘空间:"
df -h | grep -E "(Filesystem|/dev/)"
echo

# 检查Docker系统资源
echo "6. Docker系统资源:"
docker system df
echo

echo "=== 监控完成 ==="