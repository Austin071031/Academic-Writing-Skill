#!/usr/bin/env bash
# run_pipeline.sh — 阶段0一键预检: inspect -> extract -> init_result
# 用法: bash run_pipeline.sh [INPUT_DIR] [WORK_DIR] [OUTPUT_DIR]
set -uo pipefail
INPUT_DIR="${1:-/input}"
WORK_DIR="${2:-/app/work}"
OUTPUT_DIR="${3:-/app/output}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$WORK_DIR" "$OUTPUT_DIR"
echo "== [1/3] inspect_case =="
python3 "$SKILL_DIR/inspect_case.py" --input-dir "$INPUT_DIR" --work-dir "$WORK_DIR" || exit 1
echo "== [2/3] extract_text =="
python3 "$SKILL_DIR/extract_text.py" --input-dir "$INPUT_DIR" --work-dir "$WORK_DIR" || exit 1
echo "== [3/3] init_result =="
python3 "$SKILL_DIR/init_result.py" --work-dir "$WORK_DIR" --output-dir "$OUTPUT_DIR" || exit 1
echo "== 预检完成：请阅读 $WORK_DIR/brief.json 与 $WORK_DIR/source_dump.md，然后按 SKILL.md 阶段1继续 =="
