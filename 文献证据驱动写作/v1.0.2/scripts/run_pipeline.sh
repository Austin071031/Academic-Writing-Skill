#!/usr/bin/env bash
# 阶段0一键预检：解析案例 -> 材料文本化 -> 生成 result.json 骨架。
# 用法: bash run_pipeline.sh [INPUT_DIR] [WORK_DIR] [OUTPUT_DIR]
set -u
INPUT="${1:-/input}"
WORK="${2:-/app/work}"
OUTPUT="${3:-/app/output}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SKILL_DIR/scripts/inspect_case.py" "$INPUT" "$WORK"
python3 "$SKILL_DIR/scripts/extract_text.py" "$INPUT" "$WORK"
python3 "$SKILL_DIR/scripts/init_result.py" "$INPUT" "$OUTPUT"
echo "预检完成：查看 $WORK/brief.json 与 $WORK/text_manifest.json 后进入阶段1。"
