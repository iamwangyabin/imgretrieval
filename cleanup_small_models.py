#!/usr/bin/env python3
"""
一个简单的脚本，用于扫描指定目录下的子文件夹。
如果子文件夹中的图片数量少于给定的阈值，则将其删除。
"""
import shutil
import argparse
from pathlib import Path

# 定义常见的图片文件扩展名
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}


def cleanup_subdirectories(target_dir: str, threshold: int, dry_run: bool = False, skip_confirm: bool = False):
    """
    扫描子文件夹并删除图片数量不足的文件夹。

    Args:
        target_dir: 要扫描的目标目录。
        threshold: 图片数量的最小阈值。
        dry_run: 是否为试运行模式。
        skip_confirm: 是否跳过删除前的确认步骤。
    """
    root_path = Path(target_dir)
    if not root_path.is_dir():
        print(f"错误：目录 '{target_dir}' 不存在。")
        return

    print(f"======== 清理脚本 ========")
    print(f"扫描目录: {root_path.resolve()}")
    print(f"图片数量阈值: < {threshold}")
    if dry_run:
        print("模式: 试运行 (不会删除任何文件)")
    print("==========================\n")

    dirs_to_delete = []

    # 遍历第一层子目录
    for sub_path in root_path.iterdir():
        if sub_path.is_dir():
            try:
                # 统计图片数量
                image_count = len([f for f in sub_path.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS])

                if image_count < threshold:
                    dirs_to_delete.append((sub_path, image_count))
                else:
                    print(f"[保留] '{sub_path.name}' (包含 {image_count} 张图片)")

            except OSError as e:
                print(f"[警告] 无法访问 '{sub_path.name}': {e}")

    if not dirs_to_delete:
        print("\n没有找到需要删除的文件夹。")
        return

    print("\n以下文件夹将被删除：")
    for path, count in dirs_to_delete:
        print(f"  - '{path.name}' (包含 {count} 张图片)")

    if dry_run:
        print("\n试运行结束。")
        return

    # 确认删除
    if not skip_confirm:
        confirm = input(f"\n确定要删除这 {len(dirs_to_delete)} 个文件夹吗? (y/n): ").lower().strip()
        if confirm != 'y':
            print("操作已取消。")
            return

    print("\n正在删除...")
    deleted_count = 0
    for path, _ in dirs_to_delete:
        try:
            shutil.rmtree(path)
            print(f"[已删除] '{path.name}'")
            deleted_count += 1
        except OSError as e:
            print(f"[错误] 删除 '{path.name}' 失败: {e}")

    print(f"\n清理完成！共删除了 {deleted_count} 个文件夹。")


def main():
    parser = argparse.ArgumentParser(
        description="扫描并清理图片数量不足的子文件夹。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("target_dir", help="要扫描的目标目录。")
    parser.add_argument("threshold", type=int, help="图片数量的最小阈值。")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，只显示将要删除的文件夹，不实际操作。")
    parser.add_argument("-y", "--yes", action="store_true", help="跳过删除前的确认提示。")

    args = parser.parse_args()

    cleanup_subdirectories(args.target_dir, args.threshold, args.dry_run, args.yes)


if __name__ == "__main__":
    main()
