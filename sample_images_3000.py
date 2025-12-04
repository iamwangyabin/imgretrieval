#!/usr/bin/env python3
"""
采样脚本：确保每个模型文件夹下最多只有 3000 张图片
如果某个文件夹的图片数量超过 3000，则随机删除多余的

脚本会：
1. 遍历每个 base_model 下的每个 specific_model 文件夹
2. 统计图片数量
3. 如果超过 3000，随机保留 3000 张，删除其余的
4. 记录操作日志
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime

# 支持的图片文件格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.ico'}


def get_image_files(directory):
    """
    获取目录中的所有图片文件（递归）
    
    Args:
        directory: 目录路径
    
    Returns:
        list: 图片文件路径列表
    """
    image_files = []
    dir_path = Path(directory)
    
    try:
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                image_files.append(file_path)
    except PermissionError:
        return []
    except Exception as e:
        return []
    
    return image_files


def process_model_folders(root_dir, max_images=3000, dry_run=False):
    """
    处理每个模型文件夹，删除超出限制的图片
    
    Args:
        root_dir: 根目录路径
        max_images: 每个文件夹的最大图片数
        dry_run: 如果为 True，只显示将要删除的文件，不实际删除
    
    Returns:
        dict: 处理统计信息
    """
    root_path = Path(root_dir)
    
    if not root_path.exists():
        print(f"错误：目录不存在：{root_dir}")
        sys.exit(1)
    
    if not root_path.is_dir():
        print(f"错误：不是目录：{root_dir}")
        sys.exit(1)
    
    # 统计信息
    stats = {
        'total_folders': 0,
        'folders_over_limit': 0,
        'images_deleted': 0,
        'total_images_before': 0,
        'total_images_after': 0,
        'errors': []
    }
    
    print(f"{'='*80}")
    print(f"开始处理图片文件夹 (最大限制: {max_images} 张)")
    print(f"根目录: {root_dir}")
    print(f"{'='*80}\n")
    
    if dry_run:
        print("【干运行模式】 - 仅显示将要删除的文件，不实际删除\n")
    
    # 第一层遍历：base_model
    try:
        base_models = sorted([d for d in root_path.iterdir() if d.is_dir()])
    except PermissionError:
        print(f"错误：没有权限访问 {root_dir}")
        sys.exit(1)
    
    if not base_models:
        print(f"警告：{root_dir} 中没有找到子文件夹")
        return stats
    
    print(f"发现 {len(base_models)} 个 base_model\n")
    
    # 第二层遍历：specific_model（处理目标）
    for base_model_dir in base_models:
        base_model_name = base_model_dir.name
        
        try:
            specific_models = sorted([d for d in base_model_dir.iterdir() if d.is_dir()])
        except PermissionError:
            stats['errors'].append(f"无权限访问: {base_model_dir}")
            continue
        
        for specific_model_dir in specific_models:
            specific_model_name = specific_model_dir.name
            folder_path = specific_model_dir
            
            # 获取该文件夹中的所有图片
            image_files = get_image_files(folder_path)
            num_images = len(image_files)
            
            stats['total_folders'] += 1
            stats['total_images_before'] += num_images
            
            # 如果图片数量超过限制
            if num_images > max_images:
                stats['folders_over_limit'] += 1
                num_to_delete = num_images - max_images
                
                print(f"[处理] {base_model_name}/{specific_model_name}")
                print(f"  当前图片数: {num_images} > {max_images}")
                print(f"  需要删除: {num_to_delete} 张图片")
                
                # 随机选择要删除的图片
                random.seed(42)  # 固定随机种子以保证可重现
                files_to_delete = random.sample(image_files, num_to_delete)
                
                # 删除文件
                delete_count = 0
                for file_to_delete in files_to_delete:
                    try:
                        if not dry_run:
                            file_to_delete.unlink()
                        delete_count += 1
                        print(f"    删除: {file_to_delete.name}")
                    except Exception as e:
                        stats['errors'].append(f"删除失败: {file_to_delete} - {e}")
                        print(f"    错误: 无法删除 {file_to_delete.name}")
                
                stats['images_deleted'] += delete_count
                stats['total_images_after'] += (num_images - delete_count)
                print(f"  实际删除: {delete_count} 张\n")
            else:
                stats['total_images_after'] += num_images
    
    return stats


def print_summary(stats, dry_run=False):
    """
    打印处理总结
    """
    print(f"\n{'='*80}")
    print("处理完成 - 统计摘要")
    print(f"{'='*80}")
    print(f"处理的文件夹总数:     {stats['total_folders']}")
    print(f"超过限制的文件夹数:   {stats['folders_over_limit']}")
    print(f"删除的图片总数:       {stats['images_deleted']}")
    print(f"处理前总图片数:       {stats['total_images_before']:,}")
    print(f"处理后总图片数:       {stats['total_images_after']:,}")
    print(f"{'='*80}")
    
    if stats['errors']:
        print(f"\n出现 {len(stats['errors'])} 个错误:")
        for error in stats['errors'][:10]:  # 显示前 10 个错误
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... 还有 {len(stats['errors']) - 10} 个错误")
    
    if dry_run:
        print("\n【干运行模式】 上述操作未被实际执行")
    else:
        print("\n✓ 操作已完成")
    
    print(f"{'='*80}\n")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 sample_images_3000.py <根目录> [--max-images N] [--dry-run]")
        print()
        print("参数说明:")
        print("  <根目录>: 图片文件夹的根目录路径")
        print("  --max-images N: 可选参数，指定每个文件夹的最大图片数（默认: 3000）")
        print("  --dry-run: 可选参数，仅显示将要删除的文件，不实际删除")
        print()
        print("示例:")
        print("  python3 sample_images_3000.py /home/data/yabin/DFLIP3K/fake")
        print("  python3 sample_images_3000.py /home/data/yabin/DFLIP3K/fake --max-images 5000")
        print("  python3 sample_images_3000.py /home/data/yabin/DFLIP3K/fake --max-images 2000 --dry-run")
        sys.exit(1)
    
    root_dir = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    max_images = 3000  # 默认值
    
    # 解析 --max-images 参数
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == '--max-images' and i + 1 < len(sys.argv):
            try:
                max_images = int(sys.argv[i + 1])
                if max_images <= 0:
                    print("错误：--max-images 必须是正整数")
                    sys.exit(1)
            except ValueError:
                print(f"错误：--max-images 的值必须是整数，获得：{sys.argv[i + 1]}")
                sys.exit(1)
    
    stats = process_model_folders(root_dir, max_images=max_images, dry_run=dry_run)
    print_summary(stats, dry_run=dry_run)


if __name__ == '__main__':
    main()
