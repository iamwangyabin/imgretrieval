#!/usr/bin/env python3
"""
优化版本的图片组织脚本 - 使用多线程并行复制文件

性能改进：
1. 使用 ThreadPoolExecutor 进行并行文件复制（I/O 密集操作）
2. 预加载源文件映射，避免重复的 Path 操作和文件系统查询
3. 批量构建目录，减少系统调用
4. 优化路径操作，缓存中间结果

图片文件采用三层级嵌套目录结构存储：

目录结构规律：
1. 第一层目录：单个数字 0-9（共10个目录）
   例如：0/, 1/, 2/, ... 9/
2. 第二层目录：四位数字编码 0000-9999（每个第一层目录下有多个）
   例如：2/0000/, 2/0001/, 2/0418/ 等
3. 文件命名：数字ID + 扩展名
   例如：2452418.png, 5812418.json, 6182418.png
   扩展名通常为：.png, .jpg, .json
"""

import csv
import shutil
import sys
import re
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

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


def build_source_file_index(source_dir):
    """
    预加载所有源文件到内存中，建立快速查找映射。
    这避免了在复制过程中重复的文件系统查询。
    
    Args:
        source_dir: 源目录根路径
    
    Returns:
        dict: {filename: full_path} 的映射
    """
    file_index = {}
    source_path = Path(source_dir)
    
    try:
        # 只遍历三层目录（0-9 / 0000-9999）
        for first_level in source_path.iterdir():
            if not first_level.is_dir() or len(first_level.name) != 1:
                continue
            
            for second_level in first_level.iterdir():
                if not second_level.is_dir():
                    continue
                
                # 快速读取此目录下的所有文件
                try:
                    for file in second_level.iterdir():
                        if file.is_file():
                            file_index[file.name] = str(file)
                except (PermissionError, OSError):
                    pass
    except (FileNotFoundError, PermissionError):
        print(f"Warning: Cannot read source directory {source_dir}")
    
    return file_index


def get_source_image_path_cached(filename, file_index):
    """
    从预加载的索引中快速获取文件路径。
    
    Args:
        filename: 文件名
        file_index: 预加载的文件索引
    
    Returns:
        str: 完整路径，如果不存在返回 None
    """
    return file_index.get(filename)


def sanitize_path(path_str):
    """
    将目录名转换为 Linux 友好的格式。
    - 移除所有空格
    - 移除/替换所有特殊字符
    - 只保留字母、数字、下划线、连字符和点
    
    Args:
        path_str: 原始路径字符串
    
    Returns:
        清理后的安全路径字符串
    """
    if not path_str:
        return 'Unknown'
    
    # 首先移除空格
    safe_str = path_str.replace(' ', '_')
    
    # 定义允许的字符：字母、数字、下划线、连字符、点
    safe_str = re.sub(r'[^a-zA-Z0-9_\-.]', '_', safe_str)
    
    # 移除连续的下划线
    safe_str = re.sub(r'_+', '_', safe_str)
    
    # 移除首尾的下划线
    safe_str = safe_str.strip('_')
    
    # 如果结果为空，返回 Unknown
    if not safe_str:
        return 'Unknown'
    
    # 转换为小写
    safe_str = safe_str.lower()
    
    return safe_str


def copy_file_task(source_path, dest_path, file_index):
    """
    单个文件复制任务（用于线程池）。
    
    Args:
        source_path: 源文件路径
        dest_path: 目标文件路径
        file_index: 源文件索引（用于查找 JSON 文件）
    
    Returns:
        tuple: (success, filename)
    """
    try:
        # 确保目标目录存在
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(source_path, dest_path)
        
        # 尝试复制对应的 JSON 文件
        name_without_ext = Path(source_path).stem
        json_filename = f"{name_without_ext}.json"
        source_json_path = get_source_image_path_cached(json_filename, file_index)
        
        if source_json_path:
            try:
                dest_json_path = dest_path.parent / json_filename
                shutil.copy2(source_json_path, dest_json_path)
            except Exception:
                pass  # JSON 复制失败不影响主流程
        
        return True, dest_path.name
    except Exception as e:
        return False, dest_path.name


def organize_images_optimized(csv_file, image_source_dir, output_base_dir, num_workers=8):
    """
    优化版本：读取 CSV 文件，使用多线程并行复制图片。
    
    Args:
        csv_file: CSV 文件路径
        image_source_dir: 源图片存储目录
        output_base_dir: 输出目录基础路径
        num_workers: 线程池工作线程数（默认 8）
    """
    
    # 解析 CSV 并分组
    hierarchy = defaultdict(lambda: defaultdict(list))
    image_records = {}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                filename = row.get('filename', '').strip()
                base_model = row.get('base_model', 'Unknown').strip()
                model_name = row.get('model_name', 'Unknown').strip()
                
                if not filename:
                    continue
                
                # 处理空值
                if not base_model or base_model.lower() == 'nan':
                    base_model = 'Unknown'
                if not model_name or model_name.lower() == 'nan':
                    model_name = 'Unknown'
                
                hierarchy[base_model][model_name].append(filename)
                image_records[filename] = {
                    'base_model': base_model,
                    'model_name': model_name
                }
    
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    
    # 预加载源文件索引
    print("正在构建源文件索引...")
    file_index = build_source_file_index(image_source_dir)
    print(f"源文件索引完成：共 {len(file_index)} 个文件\n")
    
    # 准备所有复制任务
    total_files = len(image_records)
    copy_tasks = []
    
    output_dir = Path(output_base_dir)
    
    # 预先创建所有目录结构
    print("正在创建目录结构...")
    for base_model in hierarchy.keys():
        safe_base_model = sanitize_path(base_model)
        base_model_path = output_dir / safe_base_model
        
        for model_name in hierarchy[base_model].keys():
            safe_model_name = sanitize_path(model_name)
            model_path = base_model_path / safe_model_name
            model_path.mkdir(parents=True, exist_ok=True)
    
    # 构建复制任务列表
    print("正在准备复制任务...")
    for base_model in hierarchy.keys():
        safe_base_model = sanitize_path(base_model)
        base_model_path = output_dir / safe_base_model
        
        for model_name in hierarchy[base_model].keys():
            safe_model_name = sanitize_path(model_name)
            model_path = base_model_path / safe_model_name
            
            for filename in hierarchy[base_model][model_name]:
                source_file = get_source_image_path_cached(filename, file_index)
                
                if source_file:
                    dest_file = model_path / filename
                    copy_tasks.append((source_file, dest_file))
    
    print(f"准备了 {len(copy_tasks)} 个复制任务\n")
    print(f"开始复制（使用 {num_workers} 个线程）...\n")
    
    # 使用线程池并行复制
    total_copied = 0
    total_failed = 0
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(copy_file_task, source, dest, file_index): (source, dest)
            for source, dest in copy_tasks
        }
        
        # 使用进度条处理完成的任务
        with tqdm(total=len(copy_tasks), desc="复制进度", unit="张") as pbar:
            for future in as_completed(futures):
                try:
                    success, filename = future.result()
                    if success:
                        total_copied += 1
                    else:
                        total_failed += 1
                except Exception:
                    total_failed += 1
                
                pbar.update(1)
    
    # 打印摘要
    print(f"\n{'='*60}")
    print(f"图片组织完成！")
    print(f"{'='*60}")
    print(f"输出目录: {output_dir}")
    print(f"成功复制: {total_copied} 张图片")
    print(f"复制失败: {total_failed} 张图片")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 4:
        print("使用方法: python3 organize_images_optimized.py <csv_file> <image_source_dir> <output_base_dir> [num_workers]")
        print()
        print("参数说明:")
        print("  csv_file: CSV 文件路径，包含图片元数据")
        print("  image_source_dir: 源图片存储目录（三层级结构的根目录）")
        print("  output_base_dir: 输出目录的根路径")
        print("  num_workers: 线程数（可选，默认 8）")
        print()
        print("示例:")
        print("  python3 organize_images_optimized.py sample_data.csv ./source_images ./organized_images")
        print("  python3 organize_images_optimized.py sample_data.csv ./source_images ./organized_images 16")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    image_source_dir = sys.argv[2]
    output_base_dir = sys.argv[3]
    num_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    
    organize_images_optimized(csv_file, image_source_dir, output_base_dir, num_workers)


if __name__ == '__main__':
    main()