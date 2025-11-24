# 🔍 Local Image Retrieval System

一个基于深度学习的轻量级本地图像检索系统，使用 DINOv3 模型进行特征提取，支持大规模图像库的快速相似图片搜索。

## ✨ 特性

- 🚀 **高性能**：基于 FAISS 的向量检索，支持百万级图像库
- 🎯 **高精度**：使用 DINOv3 (Vision Transformer) 提取视觉特征
- 💾 **内存高效**：采用 mmap 技术，低内存占用
- 🖥️ **友好界面**：提供 Streamlit Web 界面和命令行工具
- 📊 **状态追踪**：SQLite 数据库管理图像处理状态

## 🏗️ 系统架构

```
imgretrieval/
├── app.py                  # Streamlit Web 应用
├── main.py                 # 命令行工具
├── requirements.txt        # 依赖列表
├── src/
│   ├── config.py          # 配置文件
│   ├── model.py           # DINOv3 特征提取器
│   ├── database.py        # SQLite 数据库操作
│   ├── scanner.py         # 图像文件扫描器
│   ├── processor.py       # 批量特征提取处理
│   └── search.py          # FAISS 检索引擎
├── scripts/
│   └── setup_test_data.py # 测试数据生成工具
└── data/
    ├── db.sqlite3         # 图像索引数据库
    └── features.bin       # 特征向量二进制文件
```

## 🛠️ 技术栈

- **深度学习框架**: PyTorch
- **模型**: DINOv3 (ViT-Base-16) via timm
- **向量检索**: FAISS (Facebook AI Similarity Search)
- **数据库**: SQLite
- **Web 框架**: Streamlit
- **图像处理**: Pillow

## 📦 安装

### 环境要求

- Python 3.8+
- PyTorch (支持 CPU/CUDA)

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/iamwangyabin/imgretrieval.git
cd imgretrieval

# 安装依赖
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. 初始化数据库

```bash
python main.py init
```

### 2. 扫描图像目录

```bash
python main.py scan /path/to/your/images
```

该命令会递归扫描指定目录下的所有图像文件（jpg, jpeg, png, webp），并将路径存入数据库。

### 3. 提取特征向量

```bash
python main.py process
```

系统会批量处理待处理的图像，使用 DINOv3 模型提取 768 维特征向量，并保存到 `data/features.bin`。

### 4. 启动 Web 界面

```bash
streamlit run app.py
```

访问 `http://localhost:8501`，上传查询图像即可搜索相似图片。

### 5. 查看系统状态

```bash
python main.py stats
```

显示数据库中图像的处理状态统计：
- `0`: 待处理
- `1`: 已处理
- `2`: 处理失败

## 📖 使用示例

### 命令行模式

```bash
# 初始化系统
python main.py init

# 扫描多个目录
python main.py scan ~/Pictures/Photos
python main.py scan ~/Downloads/Images

# 批量提取特征
python main.py process

# 查看统计信息
python main.py stats
```

### Web 界面模式

1. 启动 Streamlit 应用：
   ```bash
   streamlit run app.py
   ```

2. 在浏览器中：
   - 上传查询图像
   - 系统自动提取特征并检索
   - 显示 Top-K 最相似的图像及相似度分数

## 🎯 核心功能说明

### 特征提取 (model.py)

使用 `timm` 库加载预训练的 DINOv3 模型：
- 模型：`vit_base_patch16_dinov3.lvd1689m`
- 特征维度：768
- L2 归一化：支持余弦相似度搜索

### 数据库管理 (database.py)

SQLite 数据库存储图像元数据：
- `id`: 自增主键
- `path`: 图像文件路径（唯一索引）
- `status`: 处理状态（0/1/2）

### 向量检索 (search.py)

FAISS IndexFlatIP 实现精确内积搜索：
- 特征向量内存映射（mmap）
- 余弦相似度排序
- Top-K 结果返回

## 🧪 测试数据

生成测试图像：

```bash
python scripts/setup_test_data.py
```

会在 `data/test_images/` 目录下生成 10 张随机颜色的测试图像。

## ⚙️ 配置说明

编辑 `src/config.py` 自定义参数：

```python
# 模型配置
MODEL_NAME = "vit_base_patch16_dinov3.lvd1689m"  # DINOv3 模型名称
FEATURE_DIM = 768                                 # 特征向量维度

# 处理配置
BATCH_SIZE = 32                                   # 批处理大小
```

## 📊 性能优化

- **批量处理**：支持批量特征提取，提高 GPU 利用率
- **内存映射**：使用 mmap 读取特征文件，减少内存占用
- **增量索引**：支持增量添加图像，无需重新索引全部数据
- **GPU 加速**：自动检测 CUDA 可用性

## 🔧 常见问题

### 1. 如何更换模型？

修改 `src/config.py` 中的 `MODEL_NAME`，可选择 timm 支持的其他模型：
- `vit_large_patch16_dinov3.lvd1689m` (更大更准确)
- `vit_small_patch16_dinov3.lvd1689m` (更快更轻量)

### 2. 如何添加新图像？

```bash
python main.py scan ~/DFLIP3K/real/safebooru
python main.py process
```

然后重启 Streamlit 应用以重新加载索引。

### 3. 特征文件和数据库不同步怎么办？

删除 `data/features.bin` 和 `data/db.sqlite3`，重新初始化：
```bash
rm data/features.bin data/db.sqlite3
python main.py init
python main.py scan /path/to/images
python main.py process
```

## 📝 TODO

- [ ] 支持图像去重功能
- [ ] 添加增量索引 API
- [ ] 支持更多图像格式
- [ ] 优化大规模数据集的索引速度
- [ ] 添加配置文件支持
- [ ] Docker 部署支持

## 📄 License

MIT License

## 🙏 致谢

- [DINOv3](https://github.com/facebookresearch/dinov2) - Meta AI 的自监督视觉模型
- [FAISS](https://github.com/facebookresearch/faiss) - 高效向量检索库
- [timm](https://github.com/huggingface/pytorch-image-models) - PyTorch 图像模型库
- [Streamlit](https://streamlit.io/) - 快速 Web 应用框架

