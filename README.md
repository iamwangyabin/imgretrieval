# 🔍 AI生成图片检测数据集 - 图像检索系统

基于DINOv3的本地图像检索工具，用于构建和管理AI生成图片检测数据集。该系统集成了图片组织、去重、模型重排以及高效的图像检索功能。

## 📋 项目概述

这个项目的核心目标是：
1. **数据收集与处理**：从多个生成模型（Stable Diffusion系列、SDXL等）收集生成的图片
2. **数据组织与清理**：通过脚本对生成的伪造图片进行组织、去重和模型版本管理
3. **检索系统构建**：基于DINOv3特征提取和FAISS向量索引，构建真实图片的快速检索系统
4. **数据集产出**：生成用于AI生成图片检测研究的对标数据集（生成图 vs 真实图）

## ✨ 核心特性

- 🎯 **DINOv3 特征提取**：使用DINOv3模型提取高质量视觉特征
- ⚡ **FAISS 向量检索**：基于FAISS的高效相似图片检索
- 🗄️ **SQLite 数据库管理**：轻量级数据库管理图像索引
- 🔗 **符号链接优化**：使用符号链接节省磁盘空间
- 🎨 **多模型支持**：处理多个生成模型版本的图片
- 📊 **深度去重**：基于fastdup的深度学习相似度检测

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 2️⃣ 初始化检索系统

```bash
python main.py init
```

### 3️⃣ 扫描图片目录

```bash
python main.py scan /path/to/your/images
```

### 4️⃣ 提取特征

```bash
python main.py process
```

### 5️⃣ 构建搜索索引

```bash
python main.py build-index
```

### 6️⃣ 启动 Web 界面

```bash
streamlit run app.py
```

访问 `http://localhost:8501` 上传图片进行搜索

### 7️⃣ 查看统计信息

```bash
python main.py stats
```

---

## 🔧 详细使用指南

### 阶段1：生成图片数据处理

#### 1.1 图片组织脚本

将CSV中的图片元数据映射到目录结构，使用符号链接节省空间：

```bash
python organize_images_optimized.py <csv_file> <image_source_dir> <output_base_dir> [num_workers]
```

**参数说明：**
- `csv_file`: CSV文件路径，包含图片元数据（filename, base_model, model_name, model_type）
- `image_source_dir`: 源图片存储目录（三层级结构的根目录）
- `output_base_dir`: 输出目录的根路径
- `num_workers`: 线程数（可选，默认8）

**示例：**
```bash
python organize_images_optimized.py merged_all_tables.csv /home/data/liyaqid/DATASET/fakeDataset/civitai/images/ ~/DFLIP3K/raw_fake/ 16
```

**目录结构说明：**
源目录采用三层级嵌套：
- 第一层：单个数字 0-9（共10个目录）
- 第二层：四位数字编码 0000-9999
- 文件：数字ID + 扩展名（.png, .jpg, .json等）

输出目录结构：
```
output_base_dir/
├── base_model_1/
│   ├── model_v1/
│   │   ├── image1.png
│   │   ├── image1.json
│   │   └── ...
│   └── model_v2/
└── base_model_2/
```

#### 1.2 模型文件夹重排脚本

根据合并规则JSON，将多个原始模型文件夹合并到新的目标文件夹：

```bash
python reorganize_models.py <source_dir> <rules_file> [options]
```

**参数说明：**
- `source_dir`: 源目录路径（如 ./sd1.5）
- `rules_file`: 合并规则JSON文件路径（如 ./merge_rules.json）

**可选参数：**
- `--output <dir>`: 输出目录。指定时，重排结果将放在此目录，源文件保持不动
- `--dry-run`: 仅显示将要执行的操作，不实际执行

**合并规则JSON格式：**
```json
{
  "DreamShaper": ["DreamShaper_v6", "DreamShaper_v7"],
  "新文件夹名": ["原文件夹1", "原文件夹2"],
  ...
}
```

**示例：**
```bash
# 在新目录中输出重排结果（推荐，源文件完全保留）
python reorganize_models.py ./sd1.5 ./merge_rules.json --output ./sd1.5_organized

# 在源目录中输出，但保留原始文件
python reorganize_models.py ./sd1.5 ./merge_rules.json

# Dry run 模式
python reorganize_models.py ./sd1.5 ./merge_rules.json --dry-run
```

#### 1.3 文件处理命令参考

**使用 rsync 移动文件（删除源文件）：**
```bash
rsync -av --remove-source-files sd_2.0 sd_2.1_768 sd_2.0_768 sd_2.1_unclip sd_2.1/
rsync -av --remove-source-files sdxl_hyper sdxl_turbo sdxl_distilled sdxl_0.9 sdxl_1.0_lcm sdxl_lightning sdxl_1.0/
rsync -av --remove-source-files sd_1.4 sd_1.5_lcm sd_1.5_hyper sd_1.5/
```

**删除空文件夹：**
```bash
# 删除嵌套的空文件夹
rm -rf */*/

# 删除指定的文件夹
rm sd_2.0 sd_2.1_768 sd_2.0_768 sd_2.1_unclip -rf
rm -rf sdxl_hyper sdxl_turbo sdxl_distilled sdxl_0.9 sdxl_1.0_lcm sdxl_lightning
rmdir sd_1.4 sd_1.5_lcm sd_1.5_hyper
```

#### 1.4 图片去重脚本

基于fastdup的深度学习相似度检测，检测并删除重复图片：

```bash
python remove_duplicates.py <image_directory> [threshold] [--force]
```

**参数说明：**
- `image_directory`: 包含图片的目录（支持分层目录结构）
- `threshold`: 相似度阈值，0-1之间（默认0.95）
  - 1.0 = 完全一样
  - 0.95 = 极度相似（推荐）
  - 0.90 = 相似（可能包含连拍图）
  - 0.85 = 比较相似（可能有不同角度）
- `--force`: 跳过确认，直接执行删除

**示例：**
```bash
# 模拟运行（推荐先运行这个）
python remove_duplicates.py ./organized_images

# 使用自定义阈值进行模拟运行
python remove_duplicates.py ./organized_images 0.90

# 实际删除（需要确认）
python remove_duplicates.py ./organized_images 0.95 --force
```

**批量处理多个模型目录：**
```bash
for dir in ~/DFLIP3K/fake/sd_1.5/*/; do 
  python remove_duplicates.py "$dir" 0.90 --force
done
```

---

### 阶段2：检索系统构建与管理

#### 2.1 完整的检索系统工作流

```bash
# 初始化数据库
python main.py init

# 扫描真实图片目录
python main.py scan /path/to/real/images

# 提取所有图片的特征向量
python main.py process

# 构建FAISS搜索索引
python main.py build-index

# 查看系统统计信息
python main.py stats
```

#### 2.2 搜索查询

```bash
python main.py search <query_image_path> --top-k <number>
```

**示例：**
```bash
python main.py search ./test_image.jpg --top-k 10
```

---

### 阶段3：测试与验证

#### 3.1 生成可视化测试结果

```bash
# 生成可视化测试结果，随机选择5张查询图片，显示前10个匹配结果
python test_retrieval_visual.py --queries 5 --topk 10

# 自定义参数
python test_retrieval_visual.py -q 10 -k 20 -o my_test.jpg
```

**参数说明：**
- `-q, --queries`: 用作查询的图片数量（默认5）
- `-k, --topk`: 每次查询显示的top-k结果数量（默认10）
- `-o, --output`: 输出图片路径（默认retrieval_test_results.jpg）

**输出说明：**
- 绿色边框：精确匹配的图片
- 灰色边框：相似匹配的结果
- 分数：归一化的相似度分数（0-1）

---

## 📊 常用命令速查表

| 功能 | 命令 |
|------|------|
| 初始化数据库 | `python main.py init` |
| 扫描图片目录 | `python main.py scan <目录>` |
| 提取特征 | `python main.py process` |
| 构建索引 | `python main.py build-index` |
| 查看统计 | `python main.py stats` |
| 搜索相似图片 | `python main.py search <图片路径> --top-k <数量>` |
| 启动Web界面 | `streamlit run app.py` |
| 测试检索效果 | `python test_retrieval_visual.py` |
| 组织生成图片 | `python organize_images_optimized.py <csv> <源目录> <输出目录>` |
| 重排模型文件夹 | `python reorganize_models.py <源目录> <规则文件> --output <输出目录>` |
| 去重 | `python remove_duplicates.py <目录> <阈值> --force` |

---

## 🏗️ 项目结构

```
imgretrieval/
├── src/                          # 核心模块
│   ├── config.py                # 配置文件
│   ├── database.py              # 数据库管理
│   ├── model.py                 # DINOv3模型
│   ├── processor.py             # 特征提取处理
│   ├── scanner.py               # 目录扫描
│   └── search.py                # 搜索引擎
├── data/                         # 数据目录
├── main.py                       # CLI主程序
├── organize_images_optimized.py  # 图片组织脚本
├── reorganize_models.py          # 模型重排脚本
├── remove_duplicates.py          # 去重脚本
├── test_retrieval_visual.py      # 检索测试脚本
├── visualize_duplicates.py       # 去重可视化
├── requirements.txt              # 依赖列表
└── README.md                     # 本文件
```

---

## 🔍 工作流程示例

### 完整的数据集构建流程

```bash
# 1. 组织生成图片
python organize_images_optimized.py merged_all_tables.csv ./source_images ./raw_fake 16

# 2. 重排模型文件夹
python reorganize_models.py ./raw_fake ./merge_rules.json --output ./organized_fake

# 3. 去重处理（批量）
for dir in ./organized_fake/*/; do 
  python remove_duplicates.py "$dir" 0.90 --force
done

# 4. 初始化检索系统
python main.py init

# 5. 扫描真实图片
python main.py scan /path/to/real/images

# 6. 提取特征
python main.py process

# 7. 构建索引
python main.py build-index

# 8. 测试检索效果
python test_retrieval_visual.py -q 10 -k 20
```

---

## 💾 数据库管理

系统使用SQLite数据库存储：
- 图片元数据（路径、处理状态）
- 特征向量（DINOv3提取的1024维向量）
- 索引信息

数据库文件位置由 `src/config.py` 中的 `DB_PATH` 定义。

---

## 🛠️ 配置调整

### 去重相似度阈值选择

- **0.99-1.0**：仅删除完全重复的图片
- **0.95**：删除极度相似的图片（推荐用于生成图）
- **0.90**：删除明显相似的图片（可能包含连拍）
- **0.85**：删除比较相似的图片（需谨慎，可能误删）

### 特征提取配置

在 `src/config.py` 中可以调整：
- 模型类型（默认DINOv3）
- 批处理大小
- GPU使用

---

## 📝 License

MIT License

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📚 参考资源

- [DINO: Emerging Properties in Self-Supervised Vision Transformers](https://arxiv.org/abs/2104.14294)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [fastdup: Find duplicate images](https://github.com/visualdatabase/fastdup)
