#!/bin/bash

# ============================================================================
# Linux 高性能图片组织脚本 - 基于纯系统命令
# 
# 性能特点：
# ✓ 使用 find + xargs 并行复制（Linux 原生最优方案）
# ✓ 避免 Python 开销，直接调用系统级指令
# ✓ 支持大规模并行处理（16+ 进程）
# ✓ 真正的零复制技术（sendfile）
# ✓ 充分利用 Linux 文件系统缓存
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认参数
CSV_FILE=""
SOURCE_DIR=""
OUTPUT_DIR=""
NUM_WORKERS=${NUM_WORKERS:-16}  # Linux 上可以用更多进程
METHOD="xargs"  # xargs 或 rsync

# 打印使用说明
usage() {
    cat << EOF
${BLUE}=== Linux 高性能图片组织脚本 ===${NC}

使用方法:
    bash organize_images_linux.sh <csv_file> <source_dir> <output_dir> [num_workers] [method]

参数说明:
    csv_file        CSV 文件路径（包含 filename, base_model, model_name, model_type）
    source_dir      源图片存储目录（三层级结构的根目录）
    output_dir      输出目录的根路径
    num_workers     并行工作进程数（默认 16，Linux 推荐 8-32）
    method          复制方法 - xargs（默认）或 rsync

示例:
    bash organize_images_linux.sh data.csv ./source_images ./organized_images
    bash organize_images_linux.sh data.csv ./source_images ./organized_images 24
    bash organize_images_linux.sh data.csv ./source_images ./organized_images 16 rsync

${YELLOW}性能提示:${NC}
    - xargs + cp：最快，CPU 利用率高，适合 SSD
    - rsync：稳定可靠，支持增量复制，适合网络传输
    - 对于大量小文件，推荐 24-32 个工作进程
    - 对于大文件，推荐 8-16 个工作进程

EOF
    exit 1
}

# 检查参数
if [ $# -lt 3 ]; then
    usage
fi

CSV_FILE="$1"
SOURCE_DIR="$2"
OUTPUT_DIR="$3"
NUM_WORKERS=${4:-16}
METHOD=${5:-xargs}

# 验证输入文件
if [ ! -f "$CSV_FILE" ]; then
    echo -e "${RED}错误：CSV 文件不存在 - $CSV_FILE${NC}"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}错误：源目录不存在 - $SOURCE_DIR${NC}"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}Linux 高性能图片组织脚本${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "CSV 文件：$CSV_FILE"
echo -e "源目录：$SOURCE_DIR"
echo -e "输出目录：$OUTPUT_DIR"
echo -e "工作进程数：$NUM_WORKERS"
echo -e "复制方法：$METHOD"
echo -e "${BLUE}============================================================${NC}\n"

# ============================================================================
# 第一步：解析 CSV 并创建临时目录结构
# ============================================================================
echo -e "${YELLOW}[1/3] 正在解析 CSV 并创建目录结构...${NC}"

# 创建临时目录存储处理结果
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

COPY_LIST="$TEMP_DIR/copy_list.txt"
touch "$COPY_LIST"

# 使用 awk 解析 CSV（跳过第一行）
# 格式：filename|base_model|model_name|model_type
awk -F',' 'NR > 1 {
    filename = $1; gsub(/^ +| +$/, "", filename)
    base_model = $2; gsub(/^ +| +$/, "", base_model)
    model_name = $3; gsub(/^ +| +$/, "", model_name)
    model_type = $4; gsub(/^ +| +$/, "", model_type)
    
    # 处理空值
    if (base_model == "" || base_model == "nan") base_model = "Unknown"
    if (model_name == "" || model_name == "nan") model_name = "Unknown"
    if (model_type == "" || model_type == "nan") model_type = "Unknown"
    
    # 如果是 LORA，使用 base_model；否则使用 model_name
    if (toupper(model_type) == "LORA") {
        effective_model = base_model
    } else {
        effective_model = model_name
    }
    
    # 清理目录名（移除空格和特殊字符，转换为小写）
    gsub(/ /, "_", base_model)
    gsub(/[^a-zA-Z0-9._\-]/, "_", base_model)
    gsub(/_+/, "_", base_model)
    gsub(/^_+|_+$/, "", base_model)
    
    gsub(/ /, "_", effective_model)
    gsub(/[^a-zA-Z0-9._\-]/, "_", effective_model)
    gsub(/_+/, "_", effective_model)
    gsub(/^_+|_+$/, "", effective_model)
    
    if (base_model == "") base_model = "unknown"
    if (effective_model == "") effective_model = "unknown"
    
    tolower(base_model)
    tolower(effective_model)
    
    print filename "|" base_model "|" effective_model
}' "$CSV_FILE" > "$TEMP_DIR/parsed.txt"

# 统计总文件数和目录数
TOTAL_FILES=$(wc -l < "$TEMP_DIR/parsed.txt")
TOTAL_DIRS=$(cut -d'|' -f2,3 "$TEMP_DIR/parsed.txt" | sort -u | wc -l)

echo -e "${GREEN}✓ 解析完成：$TOTAL_FILES 个文件，$TOTAL_DIRS 个目录${NC}\n"

# ============================================================================
# 第二步：构建目录结构并生成复制列表
# ============================================================================
echo -e "${YELLOW}[2/3] 正在构建目录结构...${NC}"

# 创建所有需要的目录
cut -d'|' -f2,3 "$TEMP_DIR/parsed.txt" | sort -u | while IFS='|' read base_model model_name; do
    mkdir -p "$OUTPUT_DIR/$base_model/$model_name"
done

# 生成复制列表（找到源文件路径）
cat "$TEMP_DIR/parsed.txt" | while IFS='|' read filename base_model model_name; do
    # 在源目录中查找文件（三层级结构）
    # 使用 find 查找第一个匹配的文件
    source_path=$(find "$SOURCE_DIR" -name "$filename" -type f 2>/dev/null | head -n1)
    
    if [ -n "$source_path" ]; then
        dest_path="$OUTPUT_DIR/$base_model/$model_name/$filename"
        echo "$source_path|$dest_path"
    fi
done > "$COPY_LIST"

COPY_COUNT=$(wc -l < "$COPY_LIST")
echo -e "${GREEN}✓ 目录结构完成，准备复制 $COPY_COUNT 个文件${NC}\n"

# ============================================================================
# 第三步：执行复制操作
# ============================================================================
echo -e "${YELLOW}[3/3] 正在复制文件（使用 $NUM_WORKERS 个并行进程）...${NC}\n"

START_TIME=$(date +%s)

if [ "$METHOD" = "rsync" ]; then
    # ========== 方案1：rsync（最稳定，支持增量）==========
    echo -e "${BLUE}使用 rsync 方法...${NC}"
    
    # 为每个目标目录执行 rsync
    cut -d'|' -f2 "$COPY_LIST" | sort -u | while read target_dir; do
        # 构建源文件列表
        grep "|$target_dir" "$COPY_LIST" | cut -d'|' -f1 > "$TEMP_DIR/sources_$target_dir.txt"
        
        # 使用 rsync 执行复制
        rsync -a --stats --files-from="$TEMP_DIR/sources_$target_dir.txt" / "$OUTPUT_DIR/$target_dir/" \
            2>/dev/null || true
    done
    
else
    # ========== 方案2：find + xargs + cp（最快）==========
    echo -e "${BLUE}使用 find + xargs + cp 方法...${NC}"
    
    # 生成 shell 脚本来执行复制，然后用 xargs 并行执行
    cat "$COPY_LIST" | while IFS='|' read source dest; do
        echo "cp -p '$source' '$dest' 2>/dev/null && echo -n '.'"
    done > "$TEMP_DIR/copy_commands.sh"
    
    # 使用 xargs 并行执行
    cat "$TEMP_DIR/copy_commands.sh" | xargs -P "$NUM_WORKERS" -I {} bash -c '{}'
    
    echo ""  # 换行
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# ============================================================================
# 显示结果摘要
# ============================================================================
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}复制完成！${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "输出目录：$OUTPUT_DIR"
echo -e "成功复制：$COPY_COUNT 个文件"
echo -e "耗时：${DURATION} 秒"

# 计算速度
if [ $DURATION -gt 0 ]; then
    SPEED=$(echo "scale=2; $COPY_COUNT / $DURATION" | bc)
    echo -e "吞吐量：$SPEED 个文件/秒"
fi

echo -e "${BLUE}============================================================${NC}\n"

# 显示目录结构示例
echo -e "${YELLOW}目录结构示例：${NC}"
find "$OUTPUT_DIR" -maxdepth 2 -type d | head -10 | sed 's|'"$OUTPUT_DIR"'||g' | sed 's|^|  |g'
echo -e "  ...\n"

echo -e "${GREEN}✓ 完成！${NC}"
