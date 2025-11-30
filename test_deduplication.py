"""
图片去重复功能测试脚本

这个脚本演示如何使用去重复功能：
1. 检测重复图片
2. 生成过滤列表
3. 重建索引时应用过滤
"""

import os
import json
from src.deduplication import (
    DuplicateDetector, DuplicateSelector, FilterListGenerator, DeduplicationReport, 
    FILTER_LIST_PATH, DEDUP_REPORT_PATH
)
from src.search import SearchEngine
from src.config import DATA_DIR


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title):
    """打印小节标题"""
    print(f"\n>>> {title}")


def test_deduplication_workflow():
    """完整的去重复工作流测试"""
    
    print_section("图片去重复功能测试")
    
    # 步骤1：检测重复图片
    print_subsection("步骤1: 检测重复图片组")
    
    detector = DuplicateDetector(similarity_threshold=0.95)
    
    if not detector.load_features_from_db():
        print("❌ 错误：无法加载特征向量。请先运行以下命令：")
        print("   python main.py init")
        print("   python main.py scan <image_directory>")
        print("   python main.py process")
        return
    
    if not detector.build_faiss_index():
        print("❌ 错误：无法构建索引")
        return
    
    duplicate_groups_dict = detector.find_duplicate_groups()
    merged_groups = detector.merge_duplicate_groups(duplicate_groups_dict)
    
    print(f"\n✓ 检测完成")
    print(f"  总图片数: {len(detector.image_paths)}")
    print(f"  重复组数: {len(merged_groups)}")
    
    if not merged_groups:
        print("\n ℹ️  未检测到重复图片")
        return
    
    # 步骤2：筛选最佳图片
    print_subsection("步骤2: 筛选各组内最佳图片保留")
    
    selector = DuplicateSelector(detector.image_paths)
    retained_paths, filtered_paths = selector.select_best_from_groups(merged_groups)
    
    print(f"\n✓ 筛选完成")
    print(f"  保留图片: {len(retained_paths)} 张")
    print(f"  待过滤图片: {len(filtered_paths)} 张")
    
    # 步骤3：生成过滤列表
    print_subsection("步骤3: 生成过滤列表和报告")
    
    if FilterListGenerator.generate_filter_list(filtered_paths):
        print(f"✓ 过滤列表已生成: {FILTER_LIST_PATH}")
    else:
        print("❌ 生成过滤列表失败")
        return
    
    if DeduplicationReport.generate_report(merged_groups, detector.image_paths, 
                                          filtered_paths, retained_paths):
        print(f"✓ 去重报告已生成: {DEDUP_REPORT_PATH}")
    else:
        print("❌ 生成去重报告失败")
        return
    
    # 显示统计信息
    print_subsection("统计信息")
    print(f"\n总结:")
    print(f"  • 总图片数: {len(detector.image_paths)}")
    print(f"  • 重复组数: {len(merged_groups)}")
    print(f"  • 保留图片: {len(retained_paths)} 张 ({len(retained_paths)/len(detector.image_paths)*100:.1f}%)")
    print(f"  • 待过滤图片: {len(filtered_paths)} 张 ({len(filtered_paths)/len(detector.image_paths)*100:.1f}%)")
    print(f"  • 去重率: {len(filtered_paths)/len(detector.image_paths)*100:.1f}%")
    
    # 显示一些重复组的详情
    print_subsection("重复组示例")
    for i, group in enumerate(merged_groups[:3]):  # 显示前3个组
        group_list = sorted(list(group))
        print(f"\n  组 {i+1} ({len(group)} 张):")
        for img_id in group_list:
            size = os.path.getsize(detector.image_paths[img_id]) / 1024
            marker = " ← 保留" if detector.image_paths[img_id] in retained_paths else " ← 待过滤"
            print(f"    • {detector.image_paths[img_id]} ({size:.1f}KB){marker}")
    
    if len(merged_groups) > 3:
        print(f"\n  ... 还有 {len(merged_groups) - 3} 个重复组")


def test_rebuild_index_with_filter():
    """测试使用过滤列表重建索引"""
    
    print_section("测试重建索引（应用过滤列表）")
    
    print_subsection("检查过滤列表")
    
    if not os.path.exists(FILTER_LIST_PATH):
        print("❌ 过滤列表不存在。请先运行去重复流程。")
        return
    
    with open(FILTER_LIST_PATH, 'r', encoding='utf-8') as f:
        filter_data = json.load(f)
    
    print(f"✓ 过滤列表已加载")
    print(f"  待过滤图片数: {filter_data['total_filtered']}")
    
    print_subsection("重建索引（应用过滤）")
    
    engine = SearchEngine()
    if engine.build_index(apply_filter=True):
        print(f"✓ 索引重建成功")
        print(f"  索引中的图片数: {engine.index.ntotal}")
        print(f"  过滤掉的重复图片: {filter_data['total_filtered']}")
        
        # 保存索引
        if engine.save_index():
            print(f"✓ 索引已保存")
        else:
            print("❌ 索引保存失败")
    else:
        print("❌ 索引重建失败")
        return
    
    print_subsection("验证结果")
    print(f"\n✓ 新索引只包含非重复的图片")
    print(f"  原始图片总数: {filter_data['total_filtered'] + engine.index.ntotal}")
    print(f"  索引中的图片数: {engine.index.ntotal}")
    print(f"  重复被排除的图片: {filter_data['total_filtered']}")


def view_dedup_report():
    """查看去重报告"""
    
    if not os.path.exists(DEDUP_REPORT_PATH):
        print("❌ 去重报告不存在。请先运行去重复流程。")
        return
    
    with open(DEDUP_REPORT_PATH, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    print_section("去重复报告详情")
    
    summary = report['summary']
    print(f"\n总结:")
    print(f"  • 总图片数: {summary['total_images']}")
    print(f"  • 重复组数: {summary['duplicate_groups']}")
    print(f"  • 待过滤图片: {summary['filtered_count']}")
    print(f"  • 保留图片: {summary['retained_count']}")
    
    if summary['duplicate_groups'] > 0:
        print(f"\n前 5 个重复组:")
        for group in report['duplicate_groups'][:5]:
            print(f"\n  组 {group['group_id']} ({group['size']} 张):")
            for img_path in group['images'][:3]:
                print(f"    • {os.path.basename(img_path)}")
            if group['size'] > 3:
                print(f"    ... 还有 {group['size'] - 3} 张")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "report":
            view_dedup_report()
        elif sys.argv[1] == "rebuild":
            test_rebuild_index_with_filter()
        else:
            print("未知参数。用法:")
            print("  python test_deduplication.py          # 完整工作流测试")
            print("  python test_deduplication.py report   # 查看去重报告")
            print("  python test_deduplication.py rebuild  # 测试索引重建")
    else:
        test_deduplication_workflow()
        print("\n" + "=" * 80)
        print("💡 下一步建议:")
        print("=" * 80)
        print("  1. 查看去重报告: python test_deduplication.py report")
        print("  2. 重建索引应用过滤: python test_deduplication.py rebuild")
        print('  3. 查看过滤列表: cat data/filter_list.json')
