#!/usr/bin/env python3
"""
Script to organize images into a hierarchical directory structure.
Creates directories: base_model/model_name/ and copies images there.

图片文件采用三层级嵌套目录结构存储：

目录结构规律：
1. 第一层目录：单个数字 0-9（共10个目录）
   例如：0/, 1/, 2/, ... 9/
2. 第二层目录：四位数字编码 0000-9999（每个第一层目录下有多个）
   例如：2/0000/, 2/0001/, 2/0418/ 等
3. 文件命名：数字ID + 扩展名
   例如：2452418.png, 5812418.json, 6182418.png
   扩展名通常为：.png, .jpg, .json

如果你有一个文件名（例如 2452418.png），可以通过以下方式快速找到它：
•  提取ID：2452418
•  第一层：取ID的倒数第四位 → 2
•  第二层：取ID的后三位 → 418
•  路径：/path/to/images/2/0418/2452418.png
"""

import csv
import shutil
import sys
from pathlib import Path
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
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


def get_source_image_path(filename, source_dir):
    """
    根据文件名构造三层级目录中的源路径。
    
    例如：文件名 9253914.jpg 应该在 9/914/9253914.jpg
    
    Args:
        filename: 文件名（包含扩展名）
        source_dir: 源目录根路径
    
    Returns:
        Path 对象指向源文件的完整路径，如果无法构造则返回 None
    """
    # 提取不带扩展名的数字部分
    name_without_ext = Path(filename).stem
    
    # 检查是否为纯数字
    if not name_without_ext.isdigit():
        return None
    
    # 第一层：取ID的倒数第四位
    first_layer = name_without_ext[-4] if len(name_without_ext) >= 4 else '0'
    
    # 第二层：取ID的后三位，补零到四位
    last_three = name_without_ext[-3:] if len(name_without_ext) >= 3 else name_without_ext
    second_layer = last_three.zfill(4)
    
    # 构造完整路径
    source_path = Path(source_dir) / first_layer / second_layer / filename
    
    return source_path


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
    import re
    
    if not path_str:
        return 'Unknown'
    
    # 首先移除空格
    safe_str = path_str.replace(' ', '_')
    
    # 定义允许的字符：字母、数字、下划线、连字符、点
    # 使用正则表达式保留这些字符，其他全部替换为下划线
    safe_str = re.sub(r'[^a-zA-Z0-9_\-.]', '_', safe_str)
    
    # 移除连续的下划线
    safe_str = re.sub(r'_+', '_', safe_str)
    
    # 移除首尾的下划线
    safe_str = safe_str.strip('_')
    
    # 如果结果为空，返回 Unknown
    if not safe_str:
        return 'Unknown'
    
    # 转换为小写（可选，但更规范）
    safe_str = safe_str.lower()
    
    return safe_str


def organize_images(csv_file, image_source_dir, output_base_dir):
    """
    读取 CSV 文件，根据图片名称查找对应的 model name 和 base model name，
    然后将图片从三层级目录结构复制到 base_model/model_name/ 目录下。
    
    Args:
        csv_file: Path to CSV file containing image metadata
        image_source_dir: 源图片存储目录（三层级结构的根目录）
        output_base_dir: 输出目录的根路径，将创建 base_model/model_name/ 结构
    """
    
    # Parse CSV and group images
    hierarchy = defaultdict(lambda: defaultdict(list))
    image_records = {}  # 存储原始记录用于调试
    
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
    
    # Create directories and copy/move images
    source_dir = Path(image_source_dir)
    output_dir = Path(output_base_dir)
    
    total_files = len(image_records)
    total_copied = 0
    total_failed = 0
    
    print(f"\n开始组织图片...")
    print(f"找到 {total_files} 张图片\n")
    
    # Create progress bar
    with tqdm(total=total_files, desc="复制进度", unit="张") as pbar:
        for base_model in sorted(hierarchy.keys()):
            models = hierarchy[base_model]
            
            # Replace invalid characters in directory names
            safe_base_model = sanitize_path(base_model)
            base_model_path = output_dir / safe_base_model
            
            for model_name in sorted(models.keys()):
                filenames = models[model_name]
                
                # Replace invalid characters in directory names
                safe_model_name = sanitize_path(model_name)
                model_path = base_model_path / safe_model_name
                
                # Create directory if it doesn't exist
                model_path.mkdir(parents=True, exist_ok=True)
                
                # Copy images
                for filename in filenames:
                    # 根据三层级目录结构构造源路径
                    source_file = get_source_image_path(filename, source_dir)
                    
                    if source_file is None:
                        total_failed += 1
                        pbar.update(1)
                        continue
                    
                    dest_file = model_path / filename
                    
                    try:
                        if source_file.exists():
                            shutil.copy2(source_file, dest_file)
                            total_copied += 1
                            
                            # 同时复制对应的 JSON 文件（如果存在）
                            name_without_ext = Path(filename).stem
                            json_filename = f"{name_without_ext}.json"
                            source_json_file = get_source_image_path(json_filename, source_dir)
                            
                            if source_json_file and source_json_file.exists():
                                dest_json_file = model_path / json_filename
                                try:
                                    shutil.copy2(source_json_file, dest_json_file)
                                except Exception:
                                    pass
                        else:
                            total_failed += 1
                    except Exception:
                        total_failed += 1
                    
                    pbar.update(1)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"图片组织完成！")
    print(f"{'='*60}")
    print(f"输出目录: {output_dir}")
    print(f"成功复制: {total_copied} 张图片")
    print(f"复制失败: {total_failed} 张图片")
    print(f"{'='*60}\n")


def print_tree(directory, prefix="", max_depth=3, current_depth=0):
    """Print directory tree structure"""
    if current_depth >= max_depth:
        return
    
    try:
        items = sorted(directory.iterdir())
    except (PermissionError, FileNotFoundError):
        return
    
    dirs = [item for item in items if item.is_dir()]
    files = [item for item in items if item.is_file()]
    
    # Print directories
    for i, dir_item in enumerate(dirs):
        is_last_dir = (i == len(dirs) - 1) and len(files) == 0
        print(f"{prefix}{'└── ' if is_last_dir else '├── '}📁 {dir_item.name}/")
        
        extension = "    " if is_last_dir else "│   "
        print_tree(dir_item, prefix + extension, max_depth, current_depth + 1)
    
    # Print files (only first few and count)
    if files:
        files_to_show = files[:3]
        for i, file_item in enumerate(files_to_show):
            is_last = (i == len(files_to_show) - 1) and len(files) <= 3
            print(f"{prefix}{'└── ' if is_last else '├── '}📄 {file_item.name}")
        
        if len(files) > 3:
            print(f"{prefix}└── ... 还有 {len(files) - 3} 个文件")


def main():
    if len(sys.argv) < 4:
        print("使用方法: python3 organize_images.py <csv_file> <image_source_dir> <output_base_dir>")
        print()
        print("示例:")
        print("  python3 organize_images.py sample_data.csv ./source_images ./organized_images")
        print()
        print("这将创建以下结构:")
        print("  organized_images/")
        print("  ├── SD 1.5/")
        print("  │   ├── Makina Mix/")
        print("  │   └── Anything v3/")
        print("  └── SDXL 1.0/")
        print("      └── LEOSAM's HelloWorld XL/")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    image_source_dir = sys.argv[2]
    output_base_dir = sys.argv[3]
    
    organize_images(csv_file, image_source_dir, output_base_dir)


if __name__ == '__main__':
    main()
