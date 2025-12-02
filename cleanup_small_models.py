#!/usr/bin/env python3
"""
清理脚本：删除图片数量不足的子模型

功能：
1. 扫描 organize_images_optimized.py 建立的目录结构
2. 统计每个子模型中的图片数量（不包括json文件）
3. 如果图片数量少于指定阈值，删除该子模型及其所有文件
4. 提供详细的清理报告

目录结构：
  output_dir/
    ├── base_model_1/
    │   ├── model_1/
    │   │   ├── image1.png
    │   │   ├── image1.json
    │   │   └── ...
    │   └── model_2/
    └── base_model_2/
        └── model_3/
            └── ...
"""

import sys
import shutil
from pathlib import Path
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.count = 0
        
        def __iter__(self):
            for item in self.iterable:
                self.count += 1
                yield item
        
        def update(self, n=1):
            self.count += n
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass


def count_images_in_directory(model_dir):
    """
    统计目录中的图片文件数量（不包括json文件）。
    
    Args:
        model_dir: 模型目录路径
    
    Returns:
        tuple: (图片数量, 所有文件名列表)
    """
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}
    image_count = 0
    all_files = []
    
    try:
        for file in model_dir.iterdir():
            if file.is_file():
                all_files.append(file.name)
                if file.suffix.lower() in image_extensions:
                    image_count += 1
    except (PermissionError, OSError) as e:
        print(f"警告: 无法读取目录 {model_dir}: {e}")
    
    return image_count, all_files


def cleanup_small_models(output_dir, threshold=100, dry_run=False):
    """
    清理图片数量不足的子模型。
    
    Args:
        output_dir: 输出目录的根路径
        threshold: 最小图片数量阈值（少于此数量的模型将被删除）
        dry_run: 是否为试运行模式（不实际删除，仅显示将要删除的内容）
    """
    
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"错误: 输出目录不存在: {output_dir}")
        sys.exit(1)
    
    print(f"{'='*70}")
    print(f"清理小型模型脚本")
    print(f"{'='*70}")
    print(f"输出目录: {output_dir}")
    print(f"最小图片数量阈值: {threshold}")
    print(f"运行模式: {'试运行 (不删除任何文件)' if dry_run else '实际删除'}")
    print(f"{'='*70}\n")
    
    # 统计信息
    stats = {
        'total_base_models': 0,
        'total_models': 0,
        'models_to_delete': 0,
        'images_to_delete': 0,
        'files_to_delete': 0,
        'models_kept': 0,
        'images_kept': 0
    }
    
    # 收集所有要删除的模型
    models_to_delete = []  # [(base_model, model_name, image_count, file_count), ...]
    models_to_keep = []    # [(base_model, model_name, image_count, file_count), ...]
    
    print("正在扫描目录结构...\n")
    
    # 遍历base_model目录
    for base_model_dir in output_path.iterdir():
        if not base_model_dir.is_dir():
            continue
        
        stats['total_base_models'] += 1
        base_model_name = base_model_dir.name
        
        # 遍历每个base_model下的model目录
        for model_dir in base_model_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            stats['total_models'] += 1
            model_name = model_dir.name
            
            # 统计该模型目录中的图片数量
            image_count, all_files = count_images_in_directory(model_dir)
            file_count = len(all_files)
            
            if image_count < threshold:
                models_to_delete.append({
                    'base_model': base_model_name,
                    'model_name': model_name,
                    'path': model_dir,
                    'image_count': image_count,
                    'file_count': file_count
                })
                stats['models_to_delete'] += 1
                stats['images_to_delete'] += image_count
                stats['files_to_delete'] += file_count
            else:
                models_to_keep.append({
                    'base_model': base_model_name,
                    'model_name': model_name,
                    'path': model_dir,
                    'image_count': image_count,
                    'file_count': file_count
                })
                stats['models_kept'] += 1
                stats['images_kept'] += image_count
    
    # 显示要删除的模型列表
    print(f"将删除的模型 (图片数 < {threshold}):\n")
    if models_to_delete:
        print(f"{'Base Model':<30} {'Model Name':<30} {'图片数':<8} {'文件数':<8}")
        print("-" * 76)
        
        with tqdm(total=len(models_to_delete), desc="扫描删除列表", disable=False) as pbar:
            for item in models_to_delete:
                print(f"{item['base_model']:<30} {item['model_name']:<30} {item['image_count']:<8} {item['file_count']:<8}")
                pbar.update(1)
        
        print()
    else:
        print("没有需要删除的模型\n")
    
    # 显示保留的模型列表
    print(f"\n将保留的模型 (图片数 >= {threshold}):\n")
    if models_to_keep:
        print(f"{'Base Model':<30} {'Model Name':<30} {'图片数':<8}")
        print("-" * 68)
        
        with tqdm(total=len(models_to_keep), desc="扫描保留列表", disable=False) as pbar:
            for item in models_to_keep[:10]:  # 只显示前10个
                print(f"{item['base_model']:<30} {item['model_name']:<30} {item['image_count']:<8}")
                pbar.update(1)
            
            if len(models_to_keep) > 10:
                print(f"... 还有 {len(models_to_keep) - 10} 个模型")
                remaining_count = len(models_to_keep) - 10
                with tqdm(total=remaining_count, desc="计数剩余", disable=False) as pbar2:
                    pbar2.update(remaining_count)
        
        print()
    else:
        print("没有需要保留的模型\n")
    
    # 显示统计信息
    print(f"\n{'='*70}")
    print(f"统计信息")
    print(f"{'='*70}")
    print(f"Base Model 总数: {stats['total_base_models']}")
    print(f"模型总数: {stats['total_models']}")
    print(f"-" * 70)
    print(f"将删除的模型数: {stats['models_to_delete']}")
    print(f"将删除的图片数: {stats['images_to_delete']}")
    print(f"将删除的文件数: {stats['files_to_delete']}")
    print(f"-" * 70)
    print(f"将保留的模型数: {stats['models_kept']}")
    print(f"将保留的图片数: {stats['images_kept']}")
    print(f"{'='*70}\n")
    
    # 执行删除操作
    if models_to_delete:
        if dry_run:
            print("试运行模式: 不进行实际删除\n")
        else:
            confirm = input(f"确定要删除 {stats['models_to_delete']} 个模型吗? (y/n): ").strip().lower()
            
            if confirm != 'y':
                print("取消操作")
                return
            
            print(f"\n正在删除 {stats['models_to_delete']} 个模型...\n")
            
            deleted_count = 0
            with tqdm(total=len(models_to_delete), desc="删除进度", unit="个", disable=False) as pbar:
                for item in models_to_delete:
                    try:
                        model_path = item['path']
                        shutil.rmtree(model_path)
                        deleted_count += 1
                        pbar.set_postfix({'当前': item['model_name'][:20], '状态': '✓'})
                    except Exception as e:
                        pbar.set_postfix({'当前': item['model_name'][:20], '状态': f'✗ {str(e)[:20]}'})
                    
                    pbar.update(1)
            
            print(f"\n删除完成!")
            print(f"成功删除: {deleted_count} 个模型")
            
            # 清理空的base_model目录
            print(f"\n正在清理空的Base Model目录...\n")
            empty_base_models = 0
            for base_model_dir in output_path.iterdir():
                if not base_model_dir.is_dir():
                    continue
                
                # 检查目录是否为空
                try:
                    if not any(base_model_dir.iterdir()):
                        base_model_dir.rmdir()
                        empty_base_models += 1
                except OSError:
                    pass
            
            if empty_base_models > 0:
                print(f"删除了 {empty_base_models} 个空的Base Model目录\n")
            
            print(f"{'='*70}")
            print(f"清理完成!")
            print(f"{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 cleanup_small_models.py <output_dir> [threshold] [--dry-run]")
        print()
        print("参数说明:")
        print("  output_dir: organize_images_optimized.py 创建的输出目录")
        print("  threshold: 最小图片数量阈值（可选，默认 100）")
        print("  --dry-run: 试运行模式，不实际删除任何文件（可选）")
        print()
        print("示例:")
        print("  python3 cleanup_small_models.py ./organized_images")
        print("  python3 cleanup_small_models.py ./organized_images 100")
        print("  python3 cleanup_small_models.py ./organized_images 100 --dry-run")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 100
    dry_run = '--dry-run' in sys.argv
    
    cleanup_small_models(output_dir, threshold, dry_run)


if __name__ == '__main__':
    main()
