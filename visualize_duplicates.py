"""
图片重复组可视化模块 - 用于展示 remove_duplicates 的分析结果

生成可视化图片，显示每个重复组中的图片
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
import math

try:
    import pandas as pd
except ImportError:
    print("错误：未安装 pandas 库")
    sys.exit(1)


def load_image_safe(image_path, max_size=(150, 150)):
    """
    安全加载图片文件。
    
    Args:
        image_path: 图片路径
        max_size: 缩放大小
    
    Returns:
        PIL Image 对象，如果加载失败返回 None
    """
    try:
        img = Image.open(image_path)
        # 转换为 RGB（处理透明度等）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 缩放
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"    警告：无法加载图片 {image_path}: {e}")
        return None


def create_duplicate_group_visualization(duplicates_df, output_path='duplicates_visualization.jpg', 
                                         max_groups=20, thumb_size=150):
    """
    创建重复组的可视化图片。
    
    Args:
        duplicates_df: fastdup 返回的 DataFrame（或其元组的第一个元素）
        output_path: 输出图片路径
        max_groups: 最多显示的重复组数
        thumb_size: 缩略图大小（像素）
    
    Returns:
        bool: 是否成功生成图片
    """
    
    # 处理 DataFrame 或元组
    if isinstance(duplicates_df, tuple):
        duplicates_df = duplicates_df[0]
    
    if duplicates_df.empty or len(duplicates_df) == 0:
        print("  没有重复组可视化")
        return False
    
    # 提取重复组
    duplicate_groups = []
    for component_id, group in duplicates_df.groupby('component_id'):
        if len(group) > 1:
            files = group['filename'].tolist() if 'filename' in group.columns else group.iloc[:, 0].tolist()
            duplicate_groups.append({
                'component_id': component_id,
                'files': files,
                'group_size': len(group)
            })
    
    if not duplicate_groups:
        print("  没有发现重复组")
        return False
    
    # 限制显示的组数
    if len(duplicate_groups) > max_groups:
        duplicate_groups = duplicate_groups[:max_groups]
    
    print(f"  准备可视化 {len(duplicate_groups)} 个重复组...")
    
    # 计算布局
    groups_per_row = 2
    rows = math.ceil(len(duplicate_groups) / groups_per_row)
    
    # 图片尺寸
    padding = 20
    group_spacing = 40
    thumb_display_size = thumb_size + 20  # 缩略图加边框
    max_thumbs_in_group = 4
    
    group_width = thumb_display_size * max_thumbs_in_group + padding * 2
    group_height = thumb_display_size + padding * 2 + 40  # 额外空间用于标签
    
    canvas_width = group_width * groups_per_row + group_spacing * (groups_per_row - 1) + padding * 2
    canvas_height = group_height * rows + group_spacing * (rows - 1) + padding * 2 + 60
    
    # 创建画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), color=(245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    
    # 尝试加载字体（如果失败使用默认字体）
    try:
        title_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 24)
        label_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
        info_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
    
    # 绘制标题
    title = f"图片重复组可视化 - 共 {len(duplicate_groups)} 个重复组"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (canvas_width - title_width) // 2
    draw.text((title_x, padding), title, fill=(0, 0, 0), font=title_font)
    
    # 绘制每个重复组
    for idx, group_info in enumerate(duplicate_groups):
        row = idx // groups_per_row
        col = idx % groups_per_row
        
        x_offset = padding + col * (group_width + group_spacing)
        y_offset = padding + 60 + row * (group_height + group_spacing)
        
        # 绘制组框
        group_color = (220, 240, 255)
        draw.rectangle(
            [x_offset, y_offset, x_offset + group_width, y_offset + group_height],
            outline=(100, 150, 200),
            width=2,
            fill=group_color
        )
        
        # 绘制组标签
        group_label = f"组 {group_info['component_id']} - {group_info['group_size']} 张图片"
        draw.text(
            (x_offset + padding, y_offset + padding),
            group_label,
            fill=(0, 0, 0),
            font=label_font
        )
        
        # 绘制缩略图
        thumb_y = y_offset + padding + 30
        loaded_count = 0
        
        for file_idx, file_path in enumerate(group_info['files']):
            if file_idx >= max_thumbs_in_group:
                # 如果超过显示数量，显示省略号
                remaining = len(group_info['files']) - max_thumbs_in_group
                if remaining > 0:
                    draw.text(
                        (x_offset + padding + file_idx * thumb_display_size, thumb_y + thumb_size // 2),
                        f"+{remaining}",
                        fill=(100, 100, 100),
                        font=label_font
                    )
                break
            
            thumb_x = x_offset + padding + file_idx * thumb_display_size
            
            # 加载图片
            img = load_image_safe(file_path, max_size=(thumb_size, thumb_size))
            
            if img:
                # 居中放置缩略图
                img_x = thumb_x + (thumb_display_size - img.width) // 2
                img_y = thumb_y + (thumb_display_size - img.height) // 2
                
                # 绘制边框
                border_color = (255, 100, 100) if file_idx > 0 else (100, 200, 100)
                draw.rectangle(
                    [img_x - 3, img_y - 3, img_x + img.width + 3, img_y + img.height + 3],
                    outline=border_color,
                    width=2
                )
                
                # 粘贴图片
                canvas.paste(img, (img_x, img_y))
                loaded_count += 1
                
                # 添加标签（保留或删除）
                label_text = "保留" if file_idx == 0 else "删除"
                label_color = (0, 150, 0) if file_idx == 0 else (200, 0, 0)
                
                draw.text(
                    (img_x, img_y + img.height + 5),
                    label_text,
                    fill=label_color,
                    font=info_font
                )
    
    # 保存图片
    canvas.save(output_path, quality=95)
    print(f"  ✓ 可视化图片已保存到：{output_path}")
    
    return True


def visualize_from_duplicates_info(duplicate_groups_info, output_path='duplicates_visualization.jpg',
                                   thumb_size=150):
    """
    从重复组信息列表创建可视化（备选方法）。
    
    Args:
        duplicate_groups_info: 重复组信息列表
        output_path: 输出图片路径
        thumb_size: 缩略图大小
    
    Returns:
        bool: 是否成功
    """
    
    if not duplicate_groups_info:
        print("  没有重复组信息")
        return False
    
    print(f"  准备可视化 {len(duplicate_groups_info)} 个重复组...")
    
    # 计算布局
    groups_per_row = 2
    rows = math.ceil(len(duplicate_groups_info) / groups_per_row)
    
    padding = 20
    group_spacing = 40
    thumb_display_size = thumb_size + 20
    max_thumbs_in_group = 4
    
    group_width = thumb_display_size * max_thumbs_in_group + padding * 2
    group_height = thumb_display_size + padding * 2 + 40
    
    canvas_width = group_width * groups_per_row + group_spacing * (groups_per_row - 1) + padding * 2
    canvas_height = group_height * rows + group_spacing * (rows - 1) + padding * 2 + 60
    
    canvas = Image.new('RGB', (canvas_width, canvas_height), color=(245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    
    # 尝试加载字体
    try:
        title_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 24)
        label_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
        info_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
    
    # 绘制标题
    title = f"图片重复组可视化 - 共 {len(duplicate_groups_info)} 个重复组"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (canvas_width - title_width) // 2
    draw.text((title_x, padding), title, fill=(0, 0, 0), font=title_font)
    
    # 绘制每个重复组
    for idx, group_info in enumerate(duplicate_groups_info):
        row = idx // groups_per_row
        col = idx % groups_per_row
        
        x_offset = padding + col * (group_width + group_spacing)
        y_offset = padding + 60 + row * (group_height + group_spacing)
        
        # 绘制组框
        group_color = (220, 240, 255)
        draw.rectangle(
            [x_offset, y_offset, x_offset + group_width, y_offset + group_height],
            outline=(100, 150, 200),
            width=2,
            fill=group_color
        )
        
        # 绘制组标签
        group_label = f"组 {group_info['component_id']} - {group_info['group_size']} 张图片"
        draw.text(
            (x_offset + padding, y_offset + padding),
            group_label,
            fill=(0, 0, 0),
            font=label_font
        )
        
        # 绘制缩略图
        thumb_y = y_offset + padding + 30
        all_files = [group_info['keep']] + group_info['remove']
        
        for file_idx, file_path in enumerate(all_files):
            if file_idx >= max_thumbs_in_group:
                remaining = len(all_files) - max_thumbs_in_group
                if remaining > 0:
                    draw.text(
                        (x_offset + padding + file_idx * thumb_display_size, thumb_y + thumb_size // 2),
                        f"+{remaining}",
                        fill=(100, 100, 100),
                        font=label_font
                    )
                break
            
            thumb_x = x_offset + padding + file_idx * thumb_display_size
            
            # 加载图片
            img = load_image_safe(file_path, max_size=(thumb_size, thumb_size))
            
            if img:
                img_x = thumb_x + (thumb_display_size - img.width) // 2
                img_y = thumb_y + (thumb_display_size - img.height) // 2
                
                # 绘制边框
                border_color = (100, 200, 100) if file_idx == 0 else (200, 0, 0)
                draw.rectangle(
                    [img_x - 3, img_y - 3, img_x + img.width + 3, img_y + img.height + 3],
                    outline=border_color,
                    width=2
                )
                
                canvas.paste(img, (img_x, img_y))
                
                # 添加标签
                label_text = "保留" if file_idx == 0 else "删除"
                label_color = (0, 150, 0) if file_idx == 0 else (200, 0, 0)
                
                draw.text(
                    (img_x, img_y + img.height + 5),
                    label_text,
                    fill=label_color,
                    font=info_font
                )
    
    canvas.save(output_path, quality=95)
    print(f"  ✓ 可视化图片已保存到：{output_path}")
    
    return True


if __name__ == '__main__':
    print("这是 remove_duplicates.py 的可视化模块，应通过主程序调用。")
