#!/usr/bin/env python3
"""
根据CSV文件中的baseModel整理图片，创建符号链接。

此脚本读取一个CSV文件，其中包含'id'和'baseModel'列。
它会在指定的输出目录中，根据'baseModel'创建子目录，
然后在这些子目录中为每个'id'对应的图片（及其.json文件）创建符号链接。

功能：
1. 读取CSV文件，获取图片ID和基础模型名称
2. 预加载源目录中的所有文件，建立快速查找映射
3. 根据baseModel名称创建清理后的目录名
4. 为每个图片创建符号链接到对应的baseModel目录
5. 同时为对应的.json文件创建符号链接
6. 使用进度条显示处理进度

符号链接的好处：
- 节省存储空间（符号链接只占几百字节）
- 数据仍在原地方，避免数据冗余
- 快速创建链接，性能更好
"""

import csv
import sys
import re
from pathlib import Path
from collections import defaultdict
import os
from tqdm import tqdm

def build_source_file_index(source_dir):
    """
    预加载所有源文件到内存中，建立快速查找映射。
    这避免了在创建符号链接过程中重复的文件系统查询。
    
    支持三层目录结构：
    - 第一层：单个数字 0-9
    - 第二层：四位数字编码 0000-9999
    - 文件：数字ID + 扩展名
    
    Args:
        source_dir: 源目录根路径
    
    Returns:
        dict: {filename: full_path} 的映射
    """
    file_index = {}
    source_path = Path(source_dir)
    
    try:
        # 遍历三层目录（0-9 / 0000-9999）
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
        print(f"警告: 无法读取源目录 {source_dir}")
    
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
    
    # 定义允许的字符：字母、数字、下划线、连字符、点、斜杠变为下划线
    safe_str = safe_str.replace('\\', '_')  # Windows路径分隔符
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


def create_symlink_task(source_path, dest_path, file_index):
    """
    单个符号链接创建任务。
    创建符号链接而不是复制文件，节省磁盘空间。
    
    Args:
        source_path: 源文件路径（字符串）
        dest_path: 目标符号链接路径（Path 对象或字符串）
        file_index: 源文件索引（用于查找 JSON 文件）
    
    Returns:
        tuple: (success, filename)
    """
    try:
        # 转换为 Path 对象以便操作
        source_path_obj = Path(source_path)
        dest_path_obj = Path(dest_path) if not isinstance(dest_path, Path) else dest_path
        
        # 确保目标目录存在
        dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果目标符号链接已存在，先删除
        if dest_path_obj.exists() or dest_path_obj.is_symlink():
            dest_path_obj.unlink()
        
        # 创建符号链接
        # 使用绝对路径确保链接的有效性
        source_abs = source_path_obj.resolve()
        os.symlink(source_abs, dest_path_obj)
        
        # 尝试为对应的 JSON 文件创建符号链接
        name_without_ext = source_path_obj.stem
        json_filename = f"{name_without_ext}.json"
        source_json_path = get_source_image_path_cached(json_filename, file_index)
        
        if source_json_path:
            try:
                dest_json_path = dest_path_obj.parent / json_filename
                
                # 如果目标 JSON 符号链接已存在，先删除
                if dest_json_path.exists() or dest_json_path.is_symlink():
                    dest_json_path.unlink()
                
                source_json_abs = Path(source_json_path).resolve()
                os.symlink(source_json_abs, dest_json_path)
            except Exception:
                pass  # JSON 符号链接创建失败不影响主流程
        
        return True, dest_path_obj.name
    except Exception as e:
        return False, Path(dest_path).name


def organize_images_by_basemodel(csv_file, image_source_dir, output_base_dir):
    """
    根据CSV文件中的baseModel组织图片。
    
    Args:
        csv_file: CSV 文件路径，包含 id 和 baseModel 列
        image_source_dir: 源图片存储目录（三层级结构的根目录）
        output_base_dir: 输出目录的根路径
    """
    
    # 解析 CSV 并分组
    basemodel_images = defaultdict(list)
    total_records = 0
    
    print(f"正在读取 CSV 文件: {csv_file}")
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                image_id = row.get('id', '').strip()
                base_model = row.get('baseModel', 'Unknown').strip()
                
                if not image_id:
                    continue
                
                # 处理空值
                if not base_model or base_model.lower() == 'nan':
                    base_model = 'Unknown'
                
                basemodel_images[base_model].append(image_id)
                total_records += 1
    
    except FileNotFoundError:
        print(f"错误: CSV 文件 '{csv_file}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误读取 CSV: {e}")
        sys.exit(1)
    
    print(f"读取完成，共 {total_records} 条记录\n")
    
    # 预加载源文件索引
    print("正在构建源文件索引...")
    file_index = build_source_file_index(image_source_dir)
    print(f"源文件索引完成：共 {len(file_index)} 个文件\n")
    
    # 准备所有符号链接任务
    symlink_tasks = []
    
    output_dir = Path(output_base_dir)
    
    # 预先创建所有基于baseModel的目录结构
    print("正在创建目录结构...")
    for base_model in basemodel_images.keys():
        safe_base_model = sanitize_path(base_model)
        base_model_path = output_dir / safe_base_model
        base_model_path.mkdir(parents=True, exist_ok=True)
    
    # 构建符号链接任务列表
    print("正在准备符号链接任务...\n")
    for base_model in basemodel_images.keys():
        safe_base_model = sanitize_path(base_model)
        base_model_path = output_dir / safe_base_model
        
        for image_id in basemodel_images[base_model]:
            # 尝试找到对应的图片文件
            # 支持多种扩展名
            for ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff']:
                filename = f"{image_id}{ext}"
                source_file = get_source_image_path_cached(filename, file_index)
                
                if source_file:
                    dest_file = base_model_path / filename
                    symlink_tasks.append((source_file, dest_file))
                    break
    
    print(f"准备了 {len(symlink_tasks)} 个符号链接任务\n")
    
    # 创建符号链接
    print(f"开始创建符号链接...\n")
    
    total_linked = 0
    total_failed = 0
    
    with tqdm(total=len(symlink_tasks), desc="符号链接创建进度", unit="个", disable=False) as pbar:
        for source, dest in symlink_tasks:
            try:
                success, filename = create_symlink_task(source, dest, file_index)
                if success:
                    total_linked += 1
                    pbar.set_postfix({'当前': filename, '状态': '✓'})
                else:
                    total_failed += 1
                    pbar.set_postfix({'当前': filename, '状态': '✗'})
            except Exception as e:
                total_failed += 1
                pbar.set_postfix({'状态': '错误'})
            
            pbar.update(1)
    
    # 打印摘要
    print(f"\n{'='*60}")
    print(f"图片组织完成！")
    print(f"{'='*60}")
    print(f"输出目录: {output_dir}")
    print(f"处理的baseModel数量: {len(basemodel_images)}")
    print(f"成功创建符号链接: {total_linked} 个")
    print(f"创建失败: {total_failed} 个")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 4:
        print("使用方法: python3 organize_by_basemodel.py <csv_file> <image_source_dir> <output_base_dir>")
        print()
        print("参数说明:")
        print("  csv_file: CSV 文件路径，包含 id 和 baseModel 列")
        print("  image_source_dir: 源图片存储目录（三层级结构的根目录）")
        print("  output_base_dir: 输出目录的根路径")
        print()
        print("示例:")
        print("  python3 organize_by_basemodel.py merged_new_fetch_images_v2.csv ./source_images ./organized_images")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    image_source_dir = sys.argv[2]
    output_base_dir = sys.argv[3]
    
    organize_images_by_basemodel(csv_file, image_source_dir, output_base_dir)


if __name__ == '__main__':
    main()
