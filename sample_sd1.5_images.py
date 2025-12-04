#!/usr/bin/env python3
"""
采样脚本：限制任意 base_model 下的每个子文件夹最多只有指定数量的图片

脚本会：
1. 找到指定的 base_model 目录
2. 遍历其下的所有 specific_model（子文件夹）
3. 统计每个子文件夹的图片数量
4. 如果超过限制（默认 3000），随机删除多余的
5. 记录操作日志
"""

import os
import sys
import random
import argparse
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


def format_size(size_bytes):
    """
    格式化文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_folder_size(folder_path):
    """
    计算文件夹的总大小
    """
    total_size = 0
    try:
        for entry in Path(folder_path).rglob('*'):
            if entry.is_file():
                total_size += entry.stat().st_size
    except:
        pass
    return total_size


def sample_base_model_images(root_dir, base_model_name, max_images=3000, dry_run=False):
    """
    采样任意 base_model 下的所有子文件夹，限制图片数量
    
    Args:
        root_dir: 根目录路径
        base_model_name: base_model 名称（如 sd1.5, sdxl 等）
        max_images: 每个子文件夹的最大图片数（默认 3000）
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
    
    # 查找指定的 base_model 目录
    base_model_dir = root_path / base_model_name
    
    if not base_model_dir.exists():
        print(f"❌ 错误：找不到 base_model 目录：{base_model_dir}")
        print(f"\n可用的 base_model：")
        try:
            available = [d.name for d in root_path.iterdir() if d.is_dir()]
            if available:
                for model in sorted(available):
                    print(f"  - {model}")
            else:
                print("  （无）")
        except:
            pass
        sys.exit(1)
    
    # 统计信息
    stats = {
        'total_folders': 0,
        'folders_over_limit': 0,
        'images_deleted': 0,
        'total_images_before': 0,
        'total_images_after': 0,
        'space_freed': 0,
        'errors': []
    }
    
    print(f"{'='*80}")
    print(f"采样脚本：限制 '{base_model_name}' 下的每个子文件夹最多 {max_images} 张图片")
    print(f"{'='*80}\n")
    
    if dry_run:
        print("【干运行模式】 - 仅显示将要删除的文件，不实际删除\n")
    
    print(f"✓ 找到 base_model 目录: {base_model_dir}\n")
    
    # 列出该 base_model 下的所有子文件夹（specific_model）
    try:
        specific_models = sorted([d for d in base_model_dir.iterdir() if d.is_dir()])
    except PermissionError:
        print(f"❌ 错误：无权限访问 {base_model_dir}")
        sys.exit(1)
    
    if not specific_models:
        print(f"⚠️  警告：'{base_model_name}' 下没有子文件夹")
        return stats
    
    print(f"发现 {len(specific_models)} 个子文件夹（specific_model）\n")
    print(f"{'='*80}\n")
    
    # 处理每个子文件夹
    for specific_model_dir in specific_models:
        specific_model_name = specific_model_dir.name
        
        # 获取该文件夹中的所有图片
        image_files = get_image_files(specific_model_dir)
        num_images = len(image_files)
        
        stats['total_folders'] += 1
        stats['total_images_before'] += num_images
        
        # 如果图片数量超过限制
        if num_images > max_images:
            stats['folders_over_limit'] += 1
            num_to_delete = num_images - max_images
            
            print(f"[处理] {specific_model_name}")
            print(f"  当前图片数: {num_images:,} > {max_images:,}")
            print(f"  需要删除:   {num_to_delete:,} 张图片")
            
            # 随机选择要删除的图片
            random.seed(42)  # 固定随机种子以保证可重现
            files_to_delete = random.sample(image_files, num_to_delete)
            
            # 删除文件
            delete_count = 0
            freed_size = 0
            for file_to_delete in files_to_delete:
                try:
                    if not dry_run:
                        file_size = file_to_delete.stat().st_size
                        file_to_delete.unlink()
                        freed_size += file_size
                    else:
                        freed_size += file_to_delete.stat().st_size
                    delete_count += 1
                except Exception as e:
                    stats['errors'].append(f"删除失败: {file_to_delete} - {e}")
            
            stats['images_deleted'] += delete_count
            stats['total_images_after'] += (num_images - delete_count)
            stats['space_freed'] += freed_size
            
            print(f"  删除数量:   {num_images:,} → {max_images:,}")
            print(f"  释放空间:   {format_size(freed_size)}\n")
        else:
            stats['total_images_after'] += num_images
    
    return stats


def print_summary(stats, dry_run=False):
    """
    打印处理总结
    """
    print(f"{'='*80}")
    print("处理完成 - 统计摘要")
    print(f"{'='*80}")
    print(f"处理的子文件夹总数:   {stats['total_folders']}")
    print(f"超过限制的子文件夹:   {stats['folders_over_limit']}")
    print(f"删除的图片总数:       {stats['images_deleted']:,}")
    print(f"处理前总图片数:       {stats['total_images_before']:,}")
    print(f"处理后总图片数:       {stats['total_images_after']:,}")
    print(f"释放的存储空间:       {format_size(stats['space_freed'])}")
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
    parser = argparse.ArgumentParser(
        description='采样脚本：限制任意 base_model 下的每个子文件夹最多只有指定数量的图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 预览 sd1.5 将要删除的内容（干运行模式）
  python3 sample_sd1.5_images.py /path/to/data sd1.5 --dry-run

  # 实际执行采样（限制到 3000 张）
  python3 sample_sd1.5_images.py /path/to/data sd1.5

  # 处理 sdxl，限制到 5000 张
  python3 sample_sd1.5_images.py /path/to/data sdxl --max-images 5000 --dry-run

  # 处理其他 base_model，限制到 2000 张
  python3 sample_sd1.5_images.py /path/to/data my_model -m 2000

常见用法:
  python3 sample_sd1.5_images.py /home/data/yabin/DFLIP3K/fake sd1.5 --dry-run
  python3 sample_sd1.5_images.py /home/data/yabin/DFLIP3K/fake sd1.5 -m 3000
  python3 sample_sd1.5_images.py /home/data/yabin/DFLIP3K/fake sdxl -m 5000 --dry-run
        '''
    )
    
    parser.add_argument(
        'root_dir',
        help='包含各种 base_model 目录的根目录路径'
    )
    
    parser.add_argument(
        'base_model',
        help='要处理的 base_model 名称（如 sd1.5, sdxl 等）'
    )
    
    parser.add_argument(
        '--max-images', '-m',
        type=int,
        default=3000,
        help='每个子文件夹的最大图片数（默认: 3000）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将要删除的文件，不实际删除'
    )
    
    args = parser.parse_args()
    
    # 验证 max_images 参数
    if args.max_images <= 0:
        parser.error("错误：--max-images 必须是正整数")
    
    stats = sample_base_model_images(args.root_dir, args.base_model, max_images=args.max_images, dry_run=args.dry_run)
    print_summary(stats, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
