#!/usr/bin/env python3
"""
删除脚本：删除指定的 base_model 及其下的所有模型文件夹和图片

脚本会：
1. 找到指定的 base_model 目录（如 sd1.5）
2. 列出其下的所有 specific_model 文件夹
3. 执行删除操作（支持 dry-run 模式）
4. 记录操作日志
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime


def get_folder_size(folder_path):
    """
    计算文件夹的总大小
    
    Args:
        folder_path: 文件夹路径
    
    Returns:
        int: 文件夹大小（字节）
    """
    total_size = 0
    try:
        for entry in Path(folder_path).rglob('*'):
            if entry.is_file():
                total_size += entry.stat().st_size
    except:
        pass
    return total_size


def format_size(size_bytes):
    """
    格式化文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def remove_base_model(root_dir, base_model_name, dry_run=False):
    """
    删除指定的 base_model 及其所有内容
    
    Args:
        root_dir: 根目录路径
        base_model_name: 要删除的 base_model 名称（如 'sd1.5'）
        dry_run: 如果为 True，只显示将要删除的内容，不实际删除
    
    Returns:
        dict: 操作统计信息
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
        'base_model_found': False,
        'specific_models_count': 0,
        'total_files': 0,
        'total_size': 0,
        'deletion_status': 'pending',
        'errors': []
    }
    
    print(f"{'='*80}")
    print(f"删除脚本：移除 base_model '{base_model_name}'")
    print(f"{'='*80}\n")
    
    if dry_run:
        print("【干运行模式】 - 仅显示将要删除的内容，不实际删除\n")
    
    # 查找 base_model
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
    
    if not base_model_dir.is_dir():
        print(f"❌ 错误：'{base_model_dir}' 不是目录")
        sys.exit(1)
    
    stats['base_model_found'] = True
    
    print(f"✓ 找到 base_model：{base_model_name}\n")
    
    # 列出该 base_model 下的所有 specific_model
    try:
        specific_models = sorted([d for d in base_model_dir.iterdir() if d.is_dir()])
    except PermissionError:
        print(f"❌ 错误：无权限访问 {base_model_dir}")
        sys.exit(1)
    
    if not specific_models:
        print(f"⚠️  警告：{base_model_name} 下没有找到任何 specific_model")
        stats['deletion_status'] = 'nothing_to_delete'
        return stats
    
    print(f"该 base_model 下包含 {len(specific_models)} 个 specific_model：\n")
    
    # 统计信息
    total_files = 0
    total_size = 0
    
    for idx, specific_model_dir in enumerate(specific_models, 1):
        specific_model_name = specific_model_dir.name
        try:
            files = list(specific_model_dir.rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            folder_size = get_folder_size(specific_model_dir)
            
            total_files += file_count
            total_size += folder_size
            
            print(f"  {idx:2d}. {specific_model_name}")
            print(f"      文件数: {file_count:,}  |  大小: {format_size(folder_size)}")
        except Exception as e:
            print(f"  {idx:2d}. {specific_model_name}")
            print(f"      [获取信息失败: {e}]")
            stats['errors'].append(f"获取信息失败: {specific_model_name} - {e}")
    
    stats['specific_models_count'] = len(specific_models)
    stats['total_files'] = total_files
    stats['total_size'] = total_size
    
    print(f"\n{'='*80}")
    print(f"删除概览：")
    print(f"  Base Model:        {base_model_name}")
    print(f"  Specific Models:   {len(specific_models)}")
    print(f"  总文件数:          {total_files:,}")
    print(f"  总大小:            {format_size(total_size)}")
    print(f"{'='*80}\n")
    
    # 确认删除
    if not dry_run:
        print("⚠️  警告：此操作将永久删除上述内容，无法恢复！\n")
        response = input(f"确认删除 '{base_model_name}' 及其所有内容？ (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n❌ 操作已取消")
            stats['deletion_status'] = 'cancelled'
            return stats
    
    # 执行删除
    print("\n开始删除...\n")
    
    try:
        if not dry_run:
            shutil.rmtree(base_model_dir)
            print(f"✓ 成功删除目录：{base_model_dir}")
        else:
            print(f"[干运行] 将删除目录：{base_model_dir}")
        
        stats['deletion_status'] = 'success'
    except Exception as e:
        print(f"❌ 删除失败：{e}")
        stats['deletion_status'] = 'failed'
        stats['errors'].append(f"删除目录失败：{e}")
    
    return stats


def print_summary(stats, dry_run=False):
    """
    打印操作总结
    """
    print(f"\n{'='*80}")
    print("操作完成 - 总结")
    print(f"{'='*80}")
    
    if stats['base_model_found']:
        print(f"Base Model 找到:     ✓")
        print(f"Specific Models:    {stats['specific_models_count']}")
        print(f"总文件数:           {stats['total_files']:,}")
        print(f"总大小:             {format_size(stats['total_size'])}")
        print(f"删除状态:           {stats['deletion_status'].upper()}")
    else:
        print(f"Base Model 找到:     ❌")
    
    if stats['errors']:
        print(f"\n⚠️  出现 {len(stats['errors'])} 个错误:")
        for error in stats['errors'][:5]:
            print(f"  - {error}")
        if len(stats['errors']) > 5:
            print(f"  ... 还有 {len(stats['errors']) - 5} 个错误")
    
    if dry_run:
        print("\n【干运行模式】 上述操作未被实际执行")
    
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='删除脚本：移除指定的 base_model 及其所有 specific_model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python3 remove_sd1.5_models.py /home/data/yabin/DFLIP3K/fake sd1.5
  python3 remove_sd1.5_models.py /home/data/yabin/DFLIP3K/fake sd1.5 --dry-run
  python3 remove_sd1.5_models.py /path/to/data sdxl --dry-run
        '''
    )
    
    parser.add_argument(
        'root_dir',
        help='图片文件夹的根目录路径'
    )
    
    parser.add_argument(
        'base_model',
        help='要删除的 base_model 名称（如 sd1.5, sdxl 等）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将要删除的内容，不实际删除'
    )
    
    args = parser.parse_args()
    
    stats = remove_base_model(args.root_dir, args.base_model, dry_run=args.dry_run)
    print_summary(stats, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
