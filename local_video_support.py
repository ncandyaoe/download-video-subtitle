#!/usr/bin/env python3
"""
本地视频支持扩展
为API添加本地视频文件上传和处理功能
"""

import os
import shutil
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List

# 本地视频存储目录
LOCAL_VIDEO_DIR = Path("local_videos")
LOCAL_VIDEO_DIR.mkdir(exist_ok=True)

def save_uploaded_video(file: UploadFile) -> str:
    """保存上传的视频文件"""
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else '.mp4'
    local_filename = f"{file_id}{file_extension}"
    local_path = LOCAL_VIDEO_DIR / local_filename
    
    # 保存文件
    with open(local_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return str(local_path)

def validate_video_file(file_path: str) -> bool:
    """验证视频文件是否有效"""
    if not os.path.exists(file_path):
        return False
    
    # 检查文件大小（限制为500MB）
    file_size = os.path.getsize(file_path)
    if file_size > 500 * 1024 * 1024:  # 500MB
        return False
    
    # 检查文件扩展名
    valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    file_extension = Path(file_path).suffix.lower()
    
    return file_extension in valid_extensions

# 添加到主API应用的端点
def add_local_video_endpoints(app: FastAPI):
    """添加本地视频支持的端点"""
    
    @app.post("/upload_video")
    async def upload_video(file: UploadFile = File(...)):
        """
        上传本地视频文件
        
        Returns:
            video_id: 上传后的视频ID，可用于后续合成
        """
        try:
            # 验证文件类型
            if not file.content_type or not file.content_type.startswith('video/'):
                raise HTTPException(status_code=400, detail="只支持视频文件")
            
            # 保存文件
            local_path = save_uploaded_video(file)
            
            # 验证文件
            if not validate_video_file(local_path):
                os.remove(local_path)  # 删除无效文件
                raise HTTPException(status_code=400, detail="视频文件无效或过大")
            
            # 生成视频ID
            video_id = Path(local_path).stem
            
            return {
                "video_id": video_id,
                "filename": file.filename,
                "size": os.path.getsize(local_path),
                "local_path": local_path,
                "message": "视频上传成功"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    
    @app.post("/upload_multiple_videos")
    async def upload_multiple_videos(files: List[UploadFile] = File(...)):
        """
        批量上传多个视频文件
        
        Returns:
            uploaded_videos: 上传成功的视频列表
        """
        if len(files) > 10:  # 限制最多10个文件
            raise HTTPException(status_code=400, detail="最多只能同时上传10个视频文件")
        
        uploaded_videos = []
        failed_uploads = []
        
        for file in files:
            try:
                # 验证文件类型
                if not file.content_type or not file.content_type.startswith('video/'):
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "不是视频文件"
                    })
                    continue
                
                # 保存文件
                local_path = save_uploaded_video(file)
                
                # 验证文件
                if not validate_video_file(local_path):
                    os.remove(local_path)
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "视频文件无效或过大"
                    })
                    continue
                
                # 成功上传
                video_id = Path(local_path).stem
                uploaded_videos.append({
                    "video_id": video_id,
                    "filename": file.filename,
                    "size": os.path.getsize(local_path),
                    "local_path": local_path
                })
                
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return {
            "uploaded_videos": uploaded_videos,
            "failed_uploads": failed_uploads,
            "total_uploaded": len(uploaded_videos),
            "total_failed": len(failed_uploads)
        }
    
    @app.post("/compose_local_videos")
    async def compose_local_videos(request: dict):
        """
        合成本地视频文件
        
        Request format:
        {
            "composition_type": "concat",
            "video_ids": ["video_id_1", "video_id_2"],
            "output_format": "mp4"
        }
        """
        try:
            composition_type = request.get('composition_type', 'concat')
            video_ids = request.get('video_ids', [])
            output_format = request.get('output_format', 'mp4')
            
            if not video_ids:
                raise HTTPException(status_code=400, detail="必须提供video_ids")
            
            # 验证所有视频文件存在
            video_paths = []
            for video_id in video_ids:
                # 查找对应的视频文件
                video_files = list(LOCAL_VIDEO_DIR.glob(f"{video_id}.*"))
                if not video_files:
                    raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_id}")
                
                video_path = str(video_files[0])
                if not validate_video_file(video_path):
                    raise HTTPException(status_code=400, detail=f"视频文件无效: {video_id}")
                
                video_paths.append(video_path)
            
            # 构建合成请求（转换为标准的compose_video格式）
            compose_request = {
                "composition_type": composition_type,
                "videos": [{"video_url": f"file://{path}"} for path in video_paths],
                "output_format": output_format
            }
            
            # 这里需要调用原有的compose_video逻辑
            # 但需要修改URL验证逻辑以支持file://协议
            
            return {
                "message": "本地视频合成功能需要修改主API的URL验证逻辑",
                "video_paths": video_paths,
                "compose_request": compose_request
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"合成失败: {str(e)}")
    
    @app.get("/local_videos")
    async def list_local_videos():
        """列出所有已上传的本地视频"""
        videos = []
        
        for video_file in LOCAL_VIDEO_DIR.glob("*"):
            if video_file.is_file() and validate_video_file(str(video_file)):
                videos.append({
                    "video_id": video_file.stem,
                    "filename": video_file.name,
                    "size": video_file.stat().st_size,
                    "created_time": video_file.stat().st_ctime
                })
        
        return {
            "local_videos": videos,
            "total_count": len(videos)
        }
    
    @app.delete("/local_videos/{video_id}")
    async def delete_local_video(video_id: str):
        """删除本地视频文件"""
        video_files = list(LOCAL_VIDEO_DIR.glob(f"{video_id}.*"))
        
        if not video_files:
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        try:
            for video_file in video_files:
                video_file.unlink()
            
            return {"message": f"视频文件已删除: {video_id}"}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

# 使用示例
if __name__ == "__main__":
    from fastapi import FastAPI
    
    app = FastAPI()
    add_local_video_endpoints(app)
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)