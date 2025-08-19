#!/usr/bin/env python3
"""
本地视频支持补丁
修改现有API以支持本地视频文件
"""

import os
import re
import urllib.parse
from pathlib import Path
from fastapi import HTTPException
from loguru import logger

def validate_and_clean_url_with_local_support(url: str) -> str:
    """
    验证和清理视频URL，支持本地文件
    
    Args:
        url: 原始视频URL或本地文件路径
        
    Returns:
        清理后的有效URL或文件路径
        
    Raises:
        HTTPException: 如果URL或文件路径无效
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL或文件路径不能为空")
    
    url = url.strip()
    
    # 移除可能的引号或其他字符
    url = url.strip('\'"')
    
    # 检查是否为本地文件路径
    if url.startswith('file://') or (not url.startswith(('http://', 'https://')) and os.path.exists(url)):
        return validate_local_video_file(url)
    
    # 原有的在线URL验证逻辑
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise HTTPException(status_code=400, detail="URL格式无效")
    
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc.lower()
    
    logger.info(f"在线URL验证通过: {url} (域名: {domain})")
    return url

def validate_local_video_file(file_path: str) -> str:
    """
    验证本地视频文件
    
    Args:
        file_path: 本地文件路径（可能包含file://前缀）
        
    Returns:
        标准化的文件路径
        
    Raises:
        HTTPException: 如果文件无效
    """
    # 处理file://协议
    if file_path.startswith('file://'):
        file_path = file_path[7:]  # 移除file://前缀
    
    # 转换为绝对路径
    file_path = os.path.abspath(file_path)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"视频文件不存在: {file_path}")
    
    # 检查是否为文件（不是目录）
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"路径不是文件: {file_path}")
    
    # 检查文件扩展名
    valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp'}
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension not in valid_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的视频格式: {file_extension}。支持的格式: {', '.join(valid_extensions)}"
        )
    
    # 检查文件大小（限制为2GB）
    file_size = os.path.getsize(file_path)
    max_size = 2 * 1024 * 1024 * 1024  # 2GB
    
    if file_size > max_size:
        raise HTTPException(
            status_code=413, 
            detail=f"视频文件过大: {file_size / 1024 / 1024:.1f}MB，最大支持: {max_size / 1024 / 1024:.1f}MB"
        )
    
    # 检查文件权限
    if not os.access(file_path, os.R_OK):
        raise HTTPException(status_code=403, detail=f"无法读取视频文件: {file_path}")
    
    logger.info(f"本地视频文件验证通过: {file_path} (大小: {file_size / 1024 / 1024:.1f}MB)")
    return file_path

def is_local_file(url: str) -> bool:
    """判断是否为本地文件路径"""
    if not url:
        return False
    
    url = url.strip().strip('\'"')
    
    # 检查file://协议
    if url.startswith('file://'):
        return True
    
    # 检查是否为本地路径且文件存在
    if not url.startswith(('http://', 'https://')) and os.path.exists(url):
        return True
    
    return False

def get_local_file_path(url: str) -> str:
    """从URL获取本地文件路径"""
    if url.startswith('file://'):
        return url[7:]  # 移除file://前缀
    return url

# 使用示例和测试
def test_local_video_validation():
    """测试本地视频验证功能"""
    test_cases = [
        # 有效的本地文件路径
        "./test_videos/sample.mp4",
        "file:///Users/user/videos/test.mp4",
        "/absolute/path/to/video.avi",
        
        # 有效的在线URL
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://example.com/video.mp4",
        
        # 无效的路径
        "./nonexistent.mp4",
        "file:///nonexistent/path.mp4",
        "invalid-url",
        "",
    ]
    
    print("🧪 测试本地视频验证功能")
    print("=" * 50)
    
    for test_url in test_cases:
        try:
            result = validate_and_clean_url_with_local_support(test_url)
            is_local = is_local_file(test_url)
            print(f"✅ {test_url}")
            print(f"   结果: {result}")
            print(f"   类型: {'本地文件' if is_local else '在线URL'}")
        except HTTPException as e:
            print(f"❌ {test_url}")
            print(f"   错误: {e.detail}")
        except Exception as e:
            print(f"💥 {test_url}")
            print(f"   异常: {str(e)}")
        print()

if __name__ == "__main__":
    test_local_video_validation()