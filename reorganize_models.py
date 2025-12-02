#!/usr/bin/env python3
"""
模型文件夹重排程序

功能：
根据合并规则JSON文件，将多个原始模型文件夹合并到新的目标文件夹中。

使用场景：
- 将不同版本的模型合并：如 DreamShaper_v6, DreamShaper_v7 -> DreamShaper
- 管理大量模型文件时进行结构优化
- 支持复制和移动两种操作模式

合并规则文件格式 (JSON):
{
  "新文件夹名": ["原文件夹1", "原文件夹2", ...],
  "DreamShaper": ["DreamShaper_v6", "DreamShaper_v7"],
  ...
}
"""

import json
import shutil
import sys
import subprocess
import os
from pathlib import Path
from collections import defaultdict

from tqdm import tqdm


def load_merge_rules(rules_file):
    with open(rules_file, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    return rules


def count_items_in_folder(folder_path):
    return len(list(folder_path.iterdir()))


def copy_folder_contents(src_dir, dest_dir):
    """
    使用系统 cp 命令将源文件夹中的所有内容复制到目标文件夹，保留符号链接。
    
    Args:
        src_dir: 源文件夹路径
        dest_dir: 目标文件夹路径

    Returns:
        tuple: (成功数, 失败数, 失败列表)
    """
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    if not src_path.exists():
        return 0, 0, []

    try:
        items = list(src_path.iterdir())
        item_count = len(items)
        
        if item_count == 0:
            return 0, 0, []

        dest_path.mkdir(parents=True, exist_ok=True)

        # 使用 find + xargs + cp 保留符号链接
        # -P 选项保留符号链接，-r 递归复制
        cmd = f'find "{src_path}" -maxdepth 1 ! -name . -print0 | xargs -0 -I {{}} cp -P -r {{}} "{dest_path}/"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return item_count, 0, []
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return 0, item_count, [error_msg]

    except Exception as e:
        print(f"警告：复制文件夹 {src_dir} 时出错: {e}")
        return 0, 1, [str(e)]


def move_folder_contents(src_dir, dest_dir):
    """
    使用系统 mv 命令将源文件夹中的所有内容移动到目标文件夹，保留符号链接。
    
    Args:
        src_dir: 源文件夹路径
        dest_dir: 目标文件夹路径

    Returns:
        tuple: (成功数, 失败数, 失败列表)
    """
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    if not src_path.exists():
        return 0, 0, []

    try:
        items = list(src_path.iterdir())
        item_count = len(items)
        
        if item_count == 0:
            return 0, 0, []

        dest_path.mkdir(parents=True, exist_ok=True)

        # 使用 find + xargs + mv
        cmd = f'find "{src_path}" -maxdepth 1 ! -name . -print0 | xargs -0 -I {{}} mv {{}} "{dest_path}/"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return item_count, 0, []
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return 0, item_count, [error_msg]

    except Exception as e:
        print(f"警告：移动文件夹 {src_dir} 时出错: {e}")
        return 0, 1, [str(e)]


def cleanup_empty_folders(root_dir, max_depth=5):
    """
    删除空文件夹（递归）。

    Args:
        root_dir: 根目录路径
        max_depth: 最大递归深度
    """
    root_path = Path(root_dir)

    def remove_empty_dirs(path, depth=0):
        if depth > max_depth:
            return

        try:
            for item in path.iterdir():
                if item.is_dir():
                    remove_empty_dirs(item, depth + 1)
                    try:
                        if not list(item.iterdir()):
                            item.rmdir()
                    except OSError:
                        pass
        except (OSError, PermissionError):
            pass

    remove_empty_dirs(root_path)


def reorganize_models(source_dir, rules_file, output_dir=None, dry_run=False):
    """
    根据合并规则重排模型文件夹。

    Args:
        source_dir: 源目录路径（如 sd1.5）
        rules_file: 合并规则JSON文件路径
        output_dir: 输出目录路径。如果指定，重排结果将放在此目录下，原始文件不会被修改。
                   如果不指定，将在源目录下执行操作（保留原始文件，使用复制模式）
        dry_run: 如果为 True，只显示将要执行的操作，不实际执行
    """
    source_path = Path(source_dir)

    if not source_path.exists():
        print(f"错误：源目录 '{source_dir}' 不存在")
        sys.exit(1)

    if not source_path.is_dir():
        print(f"错误：'{source_dir}' 不是一个目录")
        sys.exit(1)

    # 确定工作目录
    if output_dir:
        work_path = Path(output_dir)
        work_path.mkdir(parents=True, exist_ok=True)
        print(f"输出目录: {output_dir}")
        print(f"原始源目录将被保留: {source_dir}\n")
    else:
        work_path = source_path
        print(f"工作目录: {source_dir}（原始文件保留，使用复制模式）\n")

    # 加载合并规则
    print(f"正在加载合并规则文件: {rules_file}")
    merge_rules = load_merge_rules(rules_file)
    print(f"已加载 {len(merge_rules)} 条合并规则\n")

    # 建立反向映射：原文件夹 -> 目标文件夹
    original_to_target = {}
    for target_name, original_list in merge_rules.items():
        for original_name in original_list:
            original_to_target[original_name] = target_name

    # 扫描源目录
    print(f"正在扫描源目录: {source_dir}")
    existing_folders = {}
    for item in source_path.iterdir():
        if item.is_dir():
            existing_folders[item.name] = item

    print(f"找到 {len(existing_folders)} 个文件夹\n")

    # 分类文件夹
    to_merge = defaultdict(list)  # {目标文件夹: [原文件夹路径]}
    to_keep = []  # 不需要合并的文件夹
    missing = set()  # 规则中指定但不存在的文件夹

    for original_name, folder_path in existing_folders.items():
        if original_name in original_to_target:
            target_name = original_to_target[original_name]
            to_merge[target_name].append((original_name, folder_path))
        else:
            to_keep.append((original_name, folder_path))

    # 检查规则中缺失的文件夹
    for target_name, original_list in merge_rules.items():
        for original_name in original_list:
            if original_name not in existing_folders:
                missing.add(original_name)

    # 打印统计信息
    print("=" * 70)
    print("重排计划摘要")
    print("=" * 70)
    print(f"源目录: {source_dir}")
    print(f"工作目录: {work_path}")
    print(f"操作模式: 复制（原始文件保留）")
    print(f"Dry Run: {'是' if dry_run else '否'}\n")

    if to_merge:
        print("将要合并的文件夹:")
        print("-" * 70)
        total_merge_items = 0
        for target_name, original_folders in sorted(to_merge.items()):
            print(f"\n  ✓ 新文件夹: {target_name}")
            for original_name, folder_path in original_folders:
                item_count = count_items_in_folder(folder_path)
                print(f"    ├─ {original_name} ({item_count} 项)")
                total_merge_items += item_count
        print(f"\n  合并总项数: {total_merge_items}")

    if to_keep:
        print(f"\n不进行合并的文件夹 ({len(to_keep)} 个):")
        print("-" * 70)
        for original_name, folder_path in to_keep[:10]:  # 只显示前10个
            item_count = count_items_in_folder(folder_path)
            print(f"  • {original_name} ({item_count} 项)")
        if len(to_keep) > 10:
            print(f"  ... 及其他 {len(to_keep) - 10} 个文件夹")

    if missing:
        print(f"\n规则中指定但未找到的文件夹 ({len(missing)} 个):")
        print("-" * 70)
        for name in sorted(missing)[:10]:
            print(f"  ⚠ {name}")
        if len(missing) > 10:
            print(f"  ... 及其他 {len(missing) - 10} 个")

    print("\n" + "=" * 70 + "\n")

    if dry_run:
        print("Dry Run 模式：不进行实际操作\n")
        return

    # 执行合并操作
    if not to_merge:
        print("没有需要合并的文件夹，操作已完成。")
        return

    confirm = input("是否继续执行？(yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("操作已取消。")
        return

    print(f"\n开始执行复制操作到 {work_path}...\n")

    total_success = 0
    total_fail = 0
    all_fail_items = []

    with tqdm(total=len(to_merge) + len(to_keep), desc="处理进度", unit="组") as pbar:
        # 处理需要合并的文件夹
        for target_name, original_folders in to_merge.items():
            target_path = work_path / target_name
            target_path.mkdir(parents=True, exist_ok=True)

            for original_name, original_path in original_folders:
                # 始终使用复制操作，不删除任何源文件
                success, fail, fail_list = copy_folder_contents(str(original_path), str(target_path))
                total_success += success
                total_fail += fail
                all_fail_items.extend(fail_list)

            pbar.update(1)
        
        # 处理不需要合并的文件夹：原封不动复制到目标文件夹
        for original_name, folder_path in to_keep:
            dest_folder = work_path / original_name
            try:
                # 使用 cp -P -r 保留符号链接并递归复制整个文件夹
                cmd = 'cp -P -r "{}" "{}"'.format(folder_path, dest_folder)
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    total_success += count_items_in_folder(folder_path)
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    total_fail += 1
                    all_fail_items.append("复制文件夹 {} 失败: {}".format(original_name, error_msg))
            except Exception as e:
                total_fail += 1
                all_fail_items.append("复制文件夹 {} 异常: {}".format(original_name, str(e)))
            
            pbar.update(1)

    # 清理空文件夹（仅清理工作目录中的空文件夹，不触及源目录）
    print("\n正在清理空文件夹...")
    cleanup_empty_folders(str(work_path))

    # 打印最终统计
    print("\n" + "=" * 70)
    print("重排完成！")
    print("=" * 70)
    print(f"源目录（保留不动）: {source_dir}")
    print(f"输出目录: {work_path}")
    print(f"成功处理: {total_success} 项")
    print(f"处理失败: {total_fail} 项")

    if all_fail_items:
        print("\n失败项详情:")
        for item in all_fail_items[:20]:
            print(f"  • {item}")
        if len(all_fail_items) > 20:
            print(f"  ... 及其他 {len(all_fail_items) - 20} 项")

    print("=" * 70 + "\n")


def main():
    if len(sys.argv) < 3:
        print("使用方法: python3 reorganize_models.py <source_dir> <rules_file> [options]")
        print()
        print("参数说明:")
        print("  source_dir: 源目录路径（如 ./sd1.5）")
        print("  rules_file: 合并规则JSON文件路径（如 ./merge_rules.json）")
        print()
        print("可选参数:")
        print("  --output <dir>  输出目录。指定时，重排结果将放在此目录，源文件保持不动")
        print("                  不指定时，使用源目录本身（仍然保留原始文件，使用复制模式）")
        print("  --dry-run       仅显示将要执行的操作，不实际执行")
        print()
        print("示例:")
        print("  # 在新目录中输出重排结果（推荐，源文件完全保留）")
        print("  python3 reorganize_models.py ./sd1.5 ./merge_rules.json --output ./sd1.5_organized")
        print()
        print("  # 在源目录中输出，但保留原始文件")
        print("  python3 reorganize_models.py ./sd1.5 ./merge_rules.json")
        print()
        print("  # Dry run 模式")
        print("  python3 reorganize_models.py ./sd1.5 ./merge_rules.json --dry-run")
        sys.exit(1)

    source_dir = sys.argv[1]
    rules_file = sys.argv[2]

    # 解析可选参数
    output_dir = None
    dry_run = False

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--dry-run':
            dry_run = True
            i += 1
        else:
            i += 1

    reorganize_models(source_dir, rules_file, output_dir, dry_run)


if __name__ == '__main__':
    main()
