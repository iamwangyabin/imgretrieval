# 🔍 图像检索系统

基于 DINOv3 的本地图像检索工具，支持快速搜索相似图片。

## ✨ 特性

- 🎯 使用 DINOv3 模型提取视觉特征
- � 基于 FAISS 的高效向量检索
- � SQLite 数据库管理图像索引

##  安装

```bash
pip install -r requirements.txt
```

## 🚀 快速开始

### 1️⃣ 初始化数据库
```bash
python main.py init
```

### 2️⃣ 扫描图片目录
```bash
python main.py scan /path/to/your/images
```

### 3️⃣ 提取特征
```bash
python main.py process
```

### 4️⃣ 启动 Web 界面
```bash
streamlit run app.py
```
访问 `http://localhost:8501` 上传图片进行搜索

### 5️⃣ 查看统计信息
```bash
python main.py stats
```

## 🧪 测试检索效果

```bash
# 生成可视化测试结果
python test_retrieval_visual.py --queries 5 --topk 10

# 自定义参数
python test_retrieval_visual.py -q 10 -k 20 -o my_test.jpg
```

### 测试结果示例

![Test Results](./retrieval_test_results.jpg)

测试脚本会随机选择图片作为查询，显示检索结果和相似度分数，绿色边框表示精确匹配。


## � 常用命令

| 命令 | 说明 |
|------|------|
| `python main.py init` | 初始化数据库 |
| `python main.py scan <目录>` | 扫描图片 |
| `python main.py process` | 提取特征 |
| `python main.py stats` | 查看统计 |
| `streamlit run app.py` | 启动 Web 界面 |
| `python test_retrieval_visual.py` | 测试检索效果 |

## 📝 License

MIT License
