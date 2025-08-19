#!/usr/bin/env python3
"""
视频格式调试工具 - 帮助分析为什么不同质量下载相同大小的文件
"""

import subprocess
import json
import sys

def get_video_formats(video_url):
    """获取视频的所有可用格式"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            formats = metadata.get('formats', [])
            
            print(f"视频标题: {metadata.get('title', 'Unknown')}")
            print(f"视频ID: {metadata.get('id', 'Unknown')}")
            print(f"时长: {metadata.get('duration', 0)}秒")
            print(f"总格式数: {len(formats)}")
            print("\n" + "="*80)
            
            # 过滤并显示视频格式
            video_formats = []
            for fmt in formats:
                if fmt.get('vcodec') != 'none':  # 只要视频格式
                    video_formats.append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'height': fmt.get('height'),
                        'width': fmt.get('width'),
                        'filesize': fmt.get('filesize'),
                        'tbr': fmt.get('tbr'),  # 总比特率
                        'vbr': fmt.get('vbr'),  # 视频比特率
                        'abr': fmt.get('abr'),  # 音频比特率
                        'format_note': fmt.get('format_note', ''),
                        'quality': fmt.get('quality', 0),
                        'fps': fmt.get('fps'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec')
                    })
            
            # 按分辨率排序
            video_formats.sort(key=lambda x: (x.get('height', 0), x.get('tbr', 0)), reverse=True)
            
            print("可用的视频格式:")
            print(f"{'ID':<10} {'格式':<6} {'分辨率':<10} {'文件大小':<12} {'比特率':<10} {'帧率':<6} {'编码':<15} {'说明'}")
            print("-" * 90)
            
            for fmt in video_formats:
                format_id = fmt.get('format_id', 'N/A')
                ext = fmt.get('ext', 'N/A')
                
                height = fmt.get('height')
                width = fmt.get('width')
                resolution = f"{width}x{height}" if width and height else "N/A"
                
                filesize = fmt.get('filesize')
                if filesize:
                    size_mb = filesize / 1024 / 1024
                    size_str = f"{size_mb:.1f}MB"
                else:
                    size_str = "未知"
                
                tbr = fmt.get('tbr')
                bitrate_str = f"{tbr:.0f}k" if tbr else "N/A"
                
                fps = fmt.get('fps')
                fps_str = f"{fps:.0f}" if fps else "N/A"
                
                vcodec = fmt.get('vcodec', 'N/A')[:12]
                
                format_note = fmt.get('format_note', '')[:20]
                
                print(f"{format_id:<10} {ext:<6} {resolution:<10} {size_str:<12} {bitrate_str:<10} {fps_str:<6} {vcodec:<15} {format_note}")
            
            # 分析常见质量的最佳选择
            print("\n" + "="*80)
            print("质量分析:")
            
            qualities = ["480p", "720p", "1080p"]
            quality_heights = {"480p": 480, "720p": 720, "1080p": 1080}
            
            for quality in qualities:
                target_height = quality_heights[quality]
                
                # 找到精确匹配
                exact_matches = [f for f in video_formats if f.get('height') == target_height]
                
                if exact_matches:
                    best_match = max(exact_matches, key=lambda x: x.get('tbr', 0))
                    filesize = best_match.get('filesize')
                    size_str = f"{filesize / 1024 / 1024:.1f}MB" if filesize else "未知"
                    
                    print(f"{quality}: 格式ID {best_match.get('format_id')}, "
                          f"分辨率 {best_match.get('width')}x{best_match.get('height')}, "
                          f"大小 {size_str}, "
                          f"比特率 {best_match.get('tbr', 0):.0f}k")
                else:
                    # 找到最接近的格式
                    suitable = [f for f in video_formats if f.get('height', 0) <= target_height and f.get('height', 0) > 0]
                    if suitable:
                        closest = max(suitable, key=lambda x: (x.get('height', 0), x.get('tbr', 0)))
                        filesize = closest.get('filesize')
                        size_str = f"{filesize / 1024 / 1024:.1f}MB" if filesize else "未知"
                        
                        print(f"{quality}: 无精确匹配，最接近格式ID {closest.get('format_id')}, "
                              f"分辨率 {closest.get('width')}x{closest.get('height')}, "
                              f"大小 {size_str}, "
                              f"比特率 {closest.get('tbr', 0):.0f}k")
                    else:
                        print(f"{quality}: 无合适格式")
            
            # 检查是否有相同大小的格式
            print("\n" + "="*80)
            print("文件大小分析:")
            
            size_groups = {}
            for fmt in video_formats:
                filesize = fmt.get('filesize')
                if filesize:
                    size_mb = round(filesize / 1024 / 1024, 1)
                    if size_mb not in size_groups:
                        size_groups[size_mb] = []
                    size_groups[size_mb].append(fmt)
            
            for size_mb, formats_with_same_size in size_groups.items():
                if len(formats_with_same_size) > 1:
                    print(f"\n相同大小 {size_mb}MB 的格式:")
                    for fmt in formats_with_same_size:
                        print(f"  - 格式ID {fmt.get('format_id')}: {fmt.get('width')}x{fmt.get('height')}, {fmt.get('tbr', 0):.0f}k, {fmt.get('format_note', '')}")
            
            return video_formats
            
        else:
            print(f"错误: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"异常: {e}")
        return []

def main():
    if len(sys.argv) != 2:
        print("用法: python debug_formats.py <video_url>")
        print("示例: python debug_formats.py 'https://www.youtube.com/watch?v=VIDEO_ID'")
        sys.exit(1)
    
    video_url = sys.argv[1]
    print(f"分析视频: {video_url}")
    print("="*80)
    
    formats = get_video_formats(video_url)
    
    if not formats:
        print("无法获取视频格式信息")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("建议:")
    print("1. 如果1080p和720p显示相同大小，可能是视频源本身没有真正的1080p版本")
    print("2. 某些视频平台会对不同质量使用相同的编码，导致文件大小相同")
    print("3. 可以尝试选择不同的格式ID来获得真正不同的质量")
    print("4. 检查比特率差异，即使文件大小相同，质量可能仍有差异")

if __name__ == "__main__":
    main()