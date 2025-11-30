"""
图片去重复模块
实现三大步骤：
1. 检测重复图片组
2. 筛选组内最佳图片保留
3. 重建索引时应用过滤
"""

import os
import json
import numpy as np
import faiss
from typing import List, Tuple, Dict, Set
from collections import defaultdict
from src.config import DATA_DIR, FEATURE_DIM
from src.database import get_all_features


FILTER_LIST_PATH = os.path.join(DATA_DIR, "filter_list.json")
DEDUP_REPORT_PATH = os.path.join(DATA_DIR, "dedup_report.json")


class DuplicateDetector:
    """检测重复图片组"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        初始化重复检测器
        
        Args:
            similarity_threshold: 相似度阈值，范围[0, 1]，0.95表示非常相似
        """
        self.similarity_threshold = similarity_threshold
        self.index = None
        self.image_paths = []
        self.vectors = None
        
    def load_features_from_db(self):
        """从数据库加载所有特征向量"""
        print("从数据库加载特征向量...")
        paths, vectors_bytes = get_all_features()
        
        if not paths:
            print("数据库中没有特征向量。请先处理图片。")
            return False
            
        print(f"找到 {len(paths)} 张已处理的图片")
        
        # 将字节转换回numpy数组
        vectors = []
        for vec_bytes in vectors_bytes:
            vec = np.frombuffer(vec_bytes, dtype=np.float32)
            vectors.append(vec)
        
        self.vectors = np.array(vectors, dtype=np.float32)
        self.image_paths = paths
        
        print(f"特征向量形状: {self.vectors.shape}")
        return True
    
    def build_faiss_index(self):
        """构建FAISS索引用于相似度搜索"""
        if self.vectors is None:
            print("错误：特征向量未加载")
            return False
            
        print("构建FAISS索引...")
        # 使用内积搜索（对于归一化向量等同于余弦相似度）
        self.index = faiss.IndexFlatIP(self.vectors.shape[1])
        self.index.add(self.vectors)
        print(f"索引构建完成，包含 {self.index.ntotal} 个向量")
        return True
    
    def find_duplicate_groups(self) -> Dict[int, List[Tuple[int, float]]]:
        """
        找到所有重复图片组
        
        Returns:
            字典，键为组代表ID，值为[(图片ID, 相似度), ...]
        """
        if self.index is None:
            print("错误：索引未构建")
            return {}
        
        print(f"开始检测重复图片（相似度阈值: {self.similarity_threshold})...")
        
        duplicate_groups = defaultdict(list)
        n = len(self.image_paths)
        
        # 对每张图片搜索最相似的图片
        for i in range(n):
            if i % max(1, n // 10) == 0:
                print(f"  进度: {i}/{n}")
            
            query_vector = self.vectors[i:i+1].astype(np.float32)
            
            # 搜索最相似的k张图片（包括自己）
            k = min(50, n)  # 搜索最多50张相似图片
            distances, indices = self.index.search(query_vector, k)
            
            # 处理搜索结果
            for dist, idx in zip(distances[0], indices[0]):
                if idx != i:  # 排除自己
                    similarity = float(dist)
                    if similarity >= self.similarity_threshold:
                        duplicate_groups[i].append((idx, similarity))
        
        print(f"检测完成，找到 {len(duplicate_groups)} 个潜在重复组")
        return duplicate_groups
    
    def merge_duplicate_groups(self, duplicate_groups: Dict[int, List[Tuple[int, float]]]) -> List[Set[int]]:
        """
        合并重复关系，得到不重叠的重复图片组
        
        Args:
            duplicate_groups: 原始重复关系
            
        Returns:
            重复图片组列表，每个组是一个图片ID集合
        """
        print("合并重复关系...")
        
        # 使用并查集(Union-Find)来合并重复关系
        parent = list(range(len(self.image_paths)))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # 建立所有重复关系
        for img_id, duplicates in duplicate_groups.items():
            for dup_id, _ in duplicates:
                union(img_id, dup_id)
        
        # 合并成组
        groups_dict = defaultdict(set)
        for i in range(len(self.image_paths)):
            root = find(i)
            groups_dict[root].add(i)
        
        # 筛选出包含重复的组（大小>1）
        duplicate_image_groups = [group for group in groups_dict.values() if len(group) > 1]
        
        print(f"合并后得到 {len(duplicate_image_groups)} 个重复图片组")
        for i, group in enumerate(duplicate_image_groups):
            print(f"  组 {i+1}: {len(group)} 张图片")
        
        return duplicate_image_groups


class DuplicateSelector:
    """从重复图片组中筛选最佳图片保留"""
    
    def __init__(self, image_paths: List[str]):
        """
        初始化选择器
        
        Args:
            image_paths: 图片路径列表
        """
        self.image_paths = image_paths
    
    def select_best_from_groups(self, duplicate_groups: List[Set[int]]) -> Tuple[List[str], List[str]]:
        """
        从每个重复组中选择最佳图片保留，其他标记为待过滤
        
        选择标准：选择文件尺寸最大的图片（对应质量最高）
        
        Args:
            duplicate_groups: 重复图片组列表
            
        Returns:
            (保留_的图片路径列表, 待过滤的图片路径列表)
        """
        print("筛选各组内最佳图片...")
        
        retained_paths = set()
        filtered_paths = set()
        
        for group_idx, group in enumerate(duplicate_groups):
            group_list = list(group)
            
            # 获取每张图片的文件大小
            file_sizes = {}
            for img_id in group_list:
                path = self.image_paths[img_id]
                if os.path.exists(path):
                    try:
                        size = os.path.getsize(path)
                        file_sizes[img_id] = size
                    except Exception as e:
                        print(f"  警告：无法获取文件大小 {path}: {e}")
                        file_sizes[img_id] = 0
                else:
                    print(f"  警告：文件不存在 {path}")
                    file_sizes[img_id] = 0
            
            # 选择最大的
            best_id = max(group_list, key=lambda x: file_sizes.get(x, 0))
            retained_paths.add(self.image_paths[best_id])
            
            print(f"  组 {group_idx+1}: 保留 {self.image_paths[best_id]} "
                  f"(大小: {file_sizes.get(best_id, 0) / 1024:.1f}KB)")
            
            # 其他标记为待过滤
            for img_id in group_list:
                if img_id != best_id:
                    filtered_paths.add(self.image_paths[img_id])
        
        print(f"筛选完成: 保留 {len(retained_paths)} 张, 待过滤 {len(filtered_paths)} 张")
        
        return list(retained_paths), list(filtered_paths)


class FilterListGenerator:
    """生成过滤列表"""
    
    @staticmethod
    def generate_filter_list(filtered_paths: List[str], output_path: str = FILTER_LIST_PATH) -> bool:
        """
        生成过滤列表JSON文件
        
        Args:
            filtered_paths: 待过滤的图片路径列表
            output_path: 输出文件路径
            
        Returns:
            是否成功生成
        """
        print(f"生成过滤列表到 {output_path}...")
        
        filter_data = {
            "version": "1.0",
            "description": "图片去重复过滤列表",
            "total_filtered": len(filtered_paths),
            "filtered_images": sorted(filtered_paths)
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filter_data, f, ensure_ascii=False, indent=2)
            print(f"过滤列表已生成: {len(filtered_paths)} 张图片待过滤")
            return True
        except Exception as e:
            print(f"错误：无法生成过滤列表 {e}")
            return False
    
    @staticmethod
    def load_filter_list(filter_path: str = FILTER_LIST_PATH) -> Set[str]:
        """
        加载过滤列表
        
        Args:
            filter_path: 过滤列表文件路径
            
        Returns:
            待过滤的图片路径集合
        """
        if not os.path.exists(filter_path):
            return set()
        
        try:
            with open(filter_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return set(data.get("filtered_images", []))
        except Exception as e:
            print(f"错误：无法加载过滤列表 {e}")
            return set()


class DeduplicationReport:
    """生成去重报告"""
    
    @staticmethod
    def generate_report(duplicate_groups: List[Set[int]], 
                       image_paths: List[str],
                       filtered_paths: List[str],
                       retained_paths: List[str],
                       output_path: str = DEDUP_REPORT_PATH) -> bool:
        """
        生成详细的去重报告
        
        Args:
            duplicate_groups: 重复图片组
            image_paths: 所有图片路径
            filtered_paths: 待过滤的图片路径
            retained_paths: 保留的图片路径
            output_path: 输出文件路径
            
        Returns:
            是否成功生成
        """
        print(f"生成去重报告到 {output_path}...")
        
        report = {
            "summary": {
                "total_images": len(image_paths),
                "duplicate_groups": len(duplicate_groups),
                "filtered_count": len(filtered_paths),
                "retained_count": len(retained_paths)
            },
            "duplicate_groups": []
        }
        
        # 添加每个重复组的详细信息
        for group_idx, group in enumerate(duplicate_groups):
            group_list = list(group)
            group_info = {
                "group_id": group_idx + 1,
                "size": len(group_list),
                "images": [image_paths[img_id] for img_id in sorted(group_list)]
            }
            report["duplicate_groups"].append(group_info)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"去重报告已生成")
            return True
        except Exception as e:
            print(f"错误：无法生成去重报告 {e}")
            return False
