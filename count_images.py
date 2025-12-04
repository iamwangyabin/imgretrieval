#!/usr/bin/env python3
"""
统计指定目录下各子文件夹的图片数量
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

# 支持的图片文件格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.ico'}


def count_images_in_directory(root_dir):
    """
    统计根目录下各子文件夹的图片数量
    
    Args:
        root_dir: 根目录路径
    
    Returns:
        dict: {文件夹名: 图片数量}
    """
    root_path = Path(root_dir)
    
    if not root_path.exists():
        print(f"错误：目录不存在：{root_dir}")
        sys.exit(1)
    
    if not root_path.is_dir():
        print(f"错误：不是目录：{root_dir}")
        sys.exit(1)
    
    image_counts = defaultdict(int)
    total_images = 0
    
    # 遍历根目录下的所有子目录
    try:
        subdirs = sorted([d for d in root_path.iterdir() if d.is_dir()])
    except PermissionError:
        print(f"错误：没有权限访问 {root_dir}")
        sys.exit(1)
    
    if not subdirs:
        print(f"警告：{root_dir} 中没有找到子文件夹")
        return image_counts
    
    print(f"正在扫描 {root_dir}...")
    print(f"共找到 {len(subdirs)} 个子文件夹\n")
    
    for subdir in subdirs:
        folder_name = subdir.name
        image_count = 0
        
        # 递归遍历子文件夹中的所有文件
        try:
            for file_path in subdir.rglob('*'):
                if file_path.is_file():
                    if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                        image_count += 1
        except PermissionError:
            print(f"  警告：没有权限访问 {subdir}")
            continue
        except Exception as e:
            print(f"  错误处理 {subdir}：{e}")
            continue
        
        image_counts[folder_name] = image_count
        total_images += image_count
    
    return image_counts, total_images


def print_statistics(image_counts, total_images):
    """
    打印统计结果
    
    Args:
        image_counts: {文件夹名: 图片数量}
        total_images: 总图片数量
    """
    print("="*70)
    print("图片统计结果")
    print("="*70)
    
    # 按数量降序排序
    sorted_counts = sorted(image_counts.items(), key=lambda x: x[1], reverse=True)
    
    max_name_length = max(len(name) for name, _ in sorted_counts) if sorted_counts else 0
    
    for folder_name, count in sorted_counts:
        percentage = (count / total_images * 100) if total_images > 0 else 0
        print(f"{folder_name:<{max_name_length}}  {count:>8,}  图片  ({percentage:>5.2f}%)")
    
    print("-"*70)
    print(f"{'总计':<{max_name_length}}  {total_images:>8,}  图片")
    print("="*70)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 count_images.py <根目录>")
        print()
        print("示例:")
        print("  python3 count_images.py /home/data/yabin/DFLIP3K/fake")
        sys.exit(1)
    
    root_dir = sys.argv[1]
    
    image_counts, total_images = count_images_in_directory(root_dir)
    
    if not image_counts:
        print("没有找到任何图片")
        sys.exit(0)
    
    print_statistics(image_counts, total_images)


if __name__ == '__main__':
    main()
