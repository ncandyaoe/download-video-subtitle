# n8n 使用指南 - 异步视频字幕服务

## 概述

新的异步API设计解决了长视频处理时的连接超时问题。现在API分为两个步骤：
1. 启动转录任务（立即返回task_id）
2. 轮询任务状态直到完成

## n8n 工作流配置

### 方法1：简单轮询（推荐用于短视频）

#### 步骤1：启动转录任务
- **节点类型**: HTTP Request
- **方法**: POST
- **URL**: `http://host.docker.internal:7878/generate_text_from_video`
- **Headers**: 
  - `Content-Type: application/json`
- **Body**: 
  ```json
  {
    "video_url": "{{$json.video_url}}"
  }
  ```

#### 步骤2：等待处理
- **节点类型**: Wait
- **等待时间**: 30秒（根据视频长度调整）

#### 步骤3：检查任务状态
- **节点类型**: HTTP Request
- **方法**: GET
- **URL**: `http://host.docker.internal:7878/task_status/{{$json.task_id}}`
- **超时设置**: 30秒（重要！）

#### 步骤4：条件判断
- **节点类型**: If
- **条件**: `{{$json.status}} === "completed"`
- **True**: 获取完整结果
- **False**: 返回步骤2继续等待

#### 步骤5：获取完整结果
- **节点类型**: HTTP Request
- **方法**: GET
- **URL**: `http://host.docker.internal:7878/task_result/{{$json.task_id}}`

### 方法2：智能轮询（推荐用于长视频）

#### 步骤1：启动转录任务
同上

#### 步骤2：循环检查状态
- **节点类型**: Code (JavaScript)
- **代码**:
```javascript
// 轮询任务状态直到完成
const taskId = $input.first().json.task_id;
const maxAttempts = 120; // 最多检查2小时
const checkInterval = 30000; // 30秒检查一次

for (let attempt = 0; attempt < maxAttempts; attempt++) {
  const response = await $http.request({
    method: 'GET',
    url: `http://localhost:7878/task_status/${taskId}`,
  });
  
  const status = response.data;
  
  if (status.status === 'completed') {
    return [{ json: status.result }];
  } else if (status.status === 'failed') {
    throw new Error(`转录失败: ${status.error}`);
  }
  
  // 等待后继续检查
  await new Promise(resolve => setTimeout(resolve, checkInterval));
}

throw new Error('转录超时');
```

### 方法3：Webhook回调（高级用法）

如果您需要处理非常长的视频，可以考虑实现webhook回调机制。

## API 端点详情

### 1. 启动转录任务
- **URL**: `POST /generate_text_from_video`
- **请求体**:
  ```json
  {
    "video_url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }
  ```
- **响应**:
  ```json
  {
    "task_id": "uuid-string",
    "status": "started",
    "message": "转录任务已启动，请使用task_id查询进度"
  }
  ```

### 2. 查询任务状态
- **URL**: `GET /task_status/{task_id}`
- **响应（进行中）**:
  ```json
  {
    "task_id": "uuid-string",
    "status": "processing",
    "progress": 50,
    "message": "开始转录..."
  }
  ```
- **响应（完成）**:
  ```json
  {
    "task_id": "uuid-string",
    "status": "completed",
    "progress": 100,
    "message": "转录完成",
    "result": {
      "title": "视频标题",
      "text": "转录文本",
      "srt": "SRT格式字幕",
      // ... 其他字段
    }
  }
  ```

## 错误处理

### 常见错误和解决方案

1. **视频时长超限**:
   - 错误码: 413
   - 解决方案: 当前限制为2小时，可以分段处理

2. **任务不存在**:
   - 错误码: 404
   - 解决方案: 检查task_id是否正确

3. **服务不可用**:
   - 错误码: 503
   - 解决方案: 检查服务是否正常运行

## 性能优化建议

1. **根据视频长度调整轮询间隔**:
   - 短视频（<5分钟）: 10秒间隔
   - 中等视频（5-30分钟）: 30秒间隔
   - 长视频（>30分钟）: 60秒间隔

2. **设置合理的超时时间**:
   - 短视频: 5分钟
   - 中等视频: 15分钟
   - 长视频: 60分钟

3. **错误重试机制**:
   - 网络错误: 重试3次
   - 服务错误: 重试1次
   - 超时错误: 不重试

## 监控和调试

使用提供的监控脚本检查服务状态：
```bash
./monitor.sh
```

查看详细日志：
```bash
docker logs subtitle-service -f
```

## 示例n8n工作流JSON

```json
{
  "nodes": [
    {
      "parameters": {
        "url": "http://localhost:7878/generate_text_from_video",
        "options": {
          "bodyContentType": "json",
          "jsonBody": "{\n  \"video_url\": \"{{$json.video_url}}\"\n}"
        }
      },
      "name": "Start Transcription",
      "type": "n8n-nodes-base.httpRequest",
      "position": [240, 300]
    },
    {
      "parameters": {
        "amount": 30,
        "unit": "seconds"
      },
      "name": "Wait",
      "type": "n8n-nodes-base.wait",
      "position": [460, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:7878/task_status/{{$json.task_id}}"
      },
      "name": "Check Status",
      "type": "n8n-nodes-base.httpRequest",
      "position": [680, 300]
    }
  ]
}
```

这个新的异步设计应该能够解决您遇到的连接中断问题。