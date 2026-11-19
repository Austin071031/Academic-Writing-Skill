#!/usr/bin/env bash
# run_pipeline.sh — 韧性流水线入口。
#   bash run_pipeline.sh pre  [--input /input --work /app/work --out /app/output]
#   bash run_pipeline.sh post [--input /input --work /app/work --out /app/output]
# pre：预检 → 材料索引 → 事实底稿（全自动，约 1–2 分钟），并立即建立 result.json 保底骨架。
# post：一致性核验 → 证据映射落盘 → 渲染预览 → 组装 result.json → 终检。
# 任何阶段失败都不中断后续保底动作；失败信息写 run_log.md。
set -u
PHASE="${1:-all}"; shift || true
INPUT="/input"; WORK="/app/work"; OUT="/app/output"
while [ $# -gt 0 ]; do
  case "$1" in
    --input) INPUT="$2"; shift 2;;
    --work)  WORK="$2";  shift 2;;
    --out)   OUT="$2";   shift 2;;
    *) shift;;
  esac
done
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$WORK" "$OUT" "$WORK/sections"
log() { echo "[pipeline] $*"; echo "- $*" >> "$OUT/run_log.md" 2>/dev/null || true; }
step() { # step <名称> <命令...>
  local name="$1"; shift
  log "STAGE $name 开始 $(date -u +%H:%M:%S)"
  if "$@" >> "$OUT/run_log.md" 2>&1; then
    log "STAGE $name 完成"
  else
    log "STAGE $name 失败（已留痕，继续保底流程）"
  fi
}

case "$PHASE" in
  pre)
    step inspect  python3 "$SKILL_DIR/scripts/inspect_case.py"        --input "$INPUT" --work "$WORK" --out "$OUT"
    step index    python3 "$SKILL_DIR/scripts/build_material_index.py" --input "$INPUT" --work "$WORK" --out "$OUT"
    step facts    python3 "$SKILL_DIR/scripts/extract_facts.py"        --input "$INPUT" --work "$WORK" --out "$OUT"
    log "PRE 完成：读 $WORK/brief.json 与 $WORK/materials_digest.md，然后按 SKILL.md 第 2 步分章写作"
    ;;
  post)
    # 证据映射：work 下的 evidence_map.json 转成 output 下可读的 md
    if [ -f "$WORK/evidence_map.json" ] && [ ! -f "$OUT/evidence_map.md" ]; then
      python3 - "$WORK/evidence_map.json" "$OUT/evidence_map.md" <<'EOF' || log "evidence_map 转换失败"
import json,sys
src,dst=sys.argv[1],sys.argv[2]
try:
    data=json.load(open(src,encoding="utf-8"))
    entries=data if isinstance(data,list) else data.get("entries",[])
    with open(dst,"w",encoding="utf-8") as f:
        f.write("# 证据映射表（论断/数字/引用 → 来源锚点）\n\n")
        f.write("| # | 稿件内容 | 类型 | 来源 |\n|---|---|---|---|\n")
        for i,e in enumerate(entries,1):
            f.write(f"| {i} | {str(e.get('claim',''))[:80]} | {e.get('type','')} | {e.get('source','')} |\n")
except Exception as ex:
    sys.stderr.write(str(ex)); sys.exit(1)
EOF
    fi
    step consistency python3 "$SKILL_DIR/scripts/check_consistency.py" --manuscript "$OUT/manuscript.md" --work "$WORK" --out "$OUT"
    step render      python3 "$SKILL_DIR/scripts/render_preview.py"    --manuscript "$OUT/manuscript.md" --out "$OUT"
    step assemble    python3 "$SKILL_DIR/scripts/assemble_result.py"   --input "$INPUT" --work "$WORK" --out "$OUT"
    step validate    python3 "$SKILL_DIR/scripts/validate_output.py"   --work "$WORK" --out "$OUT"
    log "POST 完成：读 $OUT/validation.md；有 FAIL 项则修复后重跑 post"
    ;;
  all)
    "$0" pre  --input "$INPUT" --work "$WORK" --out "$OUT"
    "$0" post --input "$INPUT" --work "$WORK" --out "$OUT"
    ;;
  *) echo "usage: run_pipeline.sh pre|post|all [--input D] [--work D] [--out D]"; exit 2;;
esac
exit 0
