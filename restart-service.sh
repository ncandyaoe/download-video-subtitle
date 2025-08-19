#!/bin/bash

# 视频字幕服务重启脚本

echo "=== 重启视频字幕服务 ==="
echo "时间: $(date)"

# 停止并移除现有容器
echo "1. 停止现有服务..."
docker-compose down

# 清理Docker资源
echo "2. 清理Docker资源..."
docker system prune -f

# 重新构建并启动服务
echo "3. 重新构建并启动服务..."
docker-compose up -d --build

# 等待服务启动
echo "4. 等待服务启动..."
sleep 30

# 检查服务状态
echo "5. 检查服务状态..."
docker ps | grep subtitle-service

# 测试服务
echo "6. 测试服务..."
curl -s -X GET "http://localhost:7878/" || echo "服务测试失败"

echo "=== 重启完成 ==="