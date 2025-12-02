#!/usr/bin/env python3
"""
图片去重程序 - 基于 fastdup 的深度学习相似度检测

支持分层目录结构：
- 输入：分层组织的图片目录（base_model/model_name/）
- 功能：递归扫描所有子目录，检测重复图片
- 输出：详细的去重报告，支持模拟删除和实际删除

特点：
1. 支持分层目录结构的递归处理
2. 自动处理配套的 JSON 元数据文件
3. 可配置的相似度阈值
4. 模拟运行模式，先预览再删除
5. 详细的日志和统计报告
"""

import os
import sys
import json
import shutil
from pathlib import Path
from collections import defaultdict
import tempfile

try:
    import fastdup
except ImportError:
    print("错误：未安装 fastdup 库")
    print("请运行：pip install fastdup")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("错误：未安装 pandas 库")
    print("请运行：pip install pandas")
    sys.exit(1)


# ================= 配置区域 =================
# 这些参数可根据需要调整
THRESHOLD = 0.95              # 相似度阈值 (0-1)
                              # 1.0 = 完全一样
                              # 0.95 = 极度相似 (推荐)
                              # 0.90 = 相似（可能包含连拍图）
                              # 0.85 = 比较相似（可能有不同角度）

DRY_RUN = True                # 设置为 True 进行模拟运行
                              # 设置为 False 时会实际删除文件

KEEP_STRATEGY = "first"       # 保留策略：
                              # "first"  - 保留列表中的第一个
                              # "largest" - 保留文件最大的
                              # "alphabetical" - 按字母顺序保留第一个

SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff'}
# ===========================================


def scan_images_in_directory(directory):
    """
    递归扫描目录中的所有图片文件。
    
    Args:
        directory: 要扫描的目录
    
    Returns:
        list: 所有图片文件的完整路径列表
    """
    images = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"错误：目录不存在 {directory}")
        return images
    
    for file_path in dir_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(str(file_path))
    
    return sorted(images)


def get_keep_file(group, strategy="first"):
    """
    根据策略选择要保留的文件。
    
    Args:
        group: DataFrame 的图片组
        strategy: 保留策略
    
    Returns:
        tuple: (保留的文件名, 待删除的文件列表)
    """
    if strategy == "largest":
        # 按文件大小排序，保留最大的
        group = group.sort_values(by='file_size', ascending=False)
    elif strategy == "alphabetical":
        # 按文件名排序，保留第一个
        group = group.sort_values(by='filename', ascending=True)
    else:
        # 默认：保留列表中的第一个
        pass
    
    keep_file = group.iloc[0]['filename']
    remove_files = group.iloc[1:]['filename'].tolist()
    
    return keep_file, remove_files


def get_associated_json(image_file):
    """
    获取图片关联的 JSON 文件路径（如果存在）。
    
    Args:
        image_file: 图片文件路径
    
    Returns:
        str: JSON 文件路径，如果不存在返回 None
    """
    json_path = Path(image_file).with_suffix('.json')
    if json_path.exists():
        return str(json_path)
    return None


def delete_file_pair(image_file, dry_run=True):
    """
    删除图片文件及其关联的 JSON 文件。
    
    Args:
        image_file: 图片文件路径
        dry_run: 如果为 True，只进行模拟删除
    
    Returns:
        bool: 删除是否成功
    """
    try:
        # 删除图片文件
        if not dry_run:
            os.remove(image_file)
        
        # 删除关联的 JSON 文件
        json_file = get_associated_json(image_file)
        if json_file:
            if not dry_run:
                os.remove(json_file)
        
        return True
    except Exception as e:
        print(f"    [错误] 删除失败 {image_file}: {e}")
        return False


def remove_duplicates(input_dir, threshold=THRESHOLD, dry_run=DRY_RUN, 
                     keep_strategy=KEEP_STRATEGY):
    """
    主程序：检测并删除重复图片。
    
    Args:
        input_dir: 输入图片目录
        threshold: 相似度阈值
        dry_run: 是否为模拟运行
        keep_strategy: 保留策略
    """
    
    print("\n" + "="*70)
    print("图片去重程序 - 基于 fastdup")
    print("="*70)
    
    # 1. 扫描图片
    print(f"\n[步骤 1/4] 扫描目录中的图片文件...")
    images = scan_images_in_directory(input_dir)
    
    if not images:
        print(f"错误：在 {input_dir} 中未找到任何图片文件")
        return
    
    print(f"  ✓ 找到 {len(images)} 个图片文件")
    print(f"  支持的格式：{', '.join(SUPPORTED_EXTENSIONS)}")
    
    # 2. 创建临时工作目录并运行 fastdup
    print(f"\n[步骤 2/4] 运行 fastdup 分析...")
    
    with tempfile.TemporaryDirectory() as work_dir:
        try:
            # 初始化 fastdup
            fd = fastdup.create(
                work_dir=work_dir,
                input_dir=input_dir,
                verbose=False
            )
            
            # 运行分析
            print(f"  处理中（使用阈值 {threshold}）...")
            fd.run(cc_threshold=threshold, verbose=False)
            
            # 获取重复组信息
            duplicates_df = fd.connected_components()
            
            if duplicates_df.empty or len(duplicates_df) == 0:
                print(f"  ✓ 分析完成：未发现重复图片")
                return
            
            print(f"  ✓ 分析完成")
            
        except Exception as e:
            print(f"  错误：fastdup 分析失败 - {e}")
            print(f"  提示：确保 fastdup 库已正确安装：pip install fastdup")
            return
    
    # 3. 处理重复项
    print(f"\n[步骤 3/4] 处理重复组...")
    
    files_to_delete = []
    duplicate_groups = []
    
    for component_id, group in duplicates_df.groupby('component_id'):
        if len(group) > 1:
            keep_file, remove_files = get_keep_file(group, keep_strategy)
            
            duplicate_groups.append({
                'component_id': component_id,
                'group_size': len(group),
                'keep': keep_file,
                'remove': remove_files
            })
            
            files_to_delete.extend(remove_files)
    
    print(f"  ✓ 发现 {len(duplicate_groups)} 个重复组")
    print(f"  ✓ 共 {len(files_to_delete)} 个文件待删除")
    
    # 4. 显示详细信息并执行删除
    print(f"\n[步骤 4/4] 重复组详情及删除操作...")
    print("-" * 70)
    
    if len(duplicate_groups) > 0:
        total_space = 0
        deleted_count = 0
        failed_count = 0
        
        for i, group_info in enumerate(duplicate_groups, 1):
            print(f"\n组 {i}/{len(duplicate_groups)} (ID: {group_info['component_id']})")
            print(f"  组内文件数：{group_info['group_size']}")
            print(f"  保留文件：{group_info['keep']}")
            
            if group_info['remove']:
                print(f"  待删除文件：")
                for f in group_info['remove']:
                    file_size = 0
                    if os.path.exists(f):
                        file_size = os.path.getsize(f)
                        total_space += file_size
                    
                    size_str = f"{file_size / 1024 / 1024:.2f} MB" if file_size > 0 else "0 B"
                    
                    success = delete_file_pair(f, dry_run=dry_run)
                    
                    status = "✓ 已删除" if success and not dry_run else "✓ 模拟删除"
                    print(f"    {status}: {Path(f).name} ({size_str})")
                    
                    if success:
                        deleted_count += 1
                    else:
                        failed_count += 1
        
        # 显示摘要
        print("\n" + "=" * 70)
        print("删除完成摘要")
        print("=" * 70)
        print(f"重复组数：{len(duplicate_groups)}")
        print(f"删除文件数：{deleted_count}")
        print(f"删除失败数：{failed_count}")
        print(f"可释放空间：{total_space / 1024 / 1024:.2f} MB")
        
        if dry_run:
            print("\n[模拟运行] 未执行实际删除操作")
            print("若要执行实际删除，请将脚本中的 DRY_RUN 设置为 False")
        else:
            print("\n[完成] 已执行实际删除操作")
    
    print("=" * 70 + "\n")


def main():
    """主入口函数"""
    
    if len(sys.argv) < 2:
        print("使用方法：python remove_duplicates.py <image_directory> [threshold] [--force]")
        print()
        print("参数说明：")
        print("  image_directory: 包含图片的目录（支持分层目录结构）")
        print("  threshold: 相似度阈值，0-1 之间（默认 0.95）")
        print("  --force: 跳过确认，直接执行删除（默认为模拟运行）")
        print()
        print("示例：")
        print("  # 模拟运行（推荐先运行这个）")
        print('  python remove_duplicates.py ./organized_images')
        print()
        print("  # 使用自定义阈值进行模拟运行")
        print('  python remove_duplicates.py ./organized_images 0.90')
        print()
        print("  # 实际删除（需要确认）")
        print('  python remove_duplicates.py ./organized_images 0.95 --force')
        sys.exit(1)
    
    image_dir = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else THRESHOLD
    force = '--force' in sys.argv
    
    # 验证阈值
    if not 0 < threshold <= 1:
        print(f"错误：阈值必须在 0-1 之间，收到 {threshold}")
        sys.exit(1)
    
    # 验证目录
    if not os.path.isdir(image_dir):
        print(f"错误：目录不存在 {image_dir}")
        sys.exit(1)
    
    # 如果不是模拟运行且不是 --force，要求用户确认
    if not DRY_RUN and not force:
        print("\n警告：这将删除检测到的重复文件！")
        print("建议先运行模拟模式查看结果后再执行实际删除操作。")
        response = input("确认执行删除操作？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消操作")
            sys.exit(0)
    
    remove_duplicates(image_dir, threshold=threshold, dry_run=DRY_RUN, 
                     keep_strategy=KEEP_STRATEGY)


if __name__ == '__main__':
    main()
