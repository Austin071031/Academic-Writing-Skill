#!/usr/bin/env bash
# run.sh — 两段式韧性管线。用法: bash run.sh pre|post [--input D] [--work D] [--out D]
# pre: 预检 + scripts/engine_pre.py（材料处理）；post: scripts/engine_check.py + 收尾。失败不中断保底。
set -u
PHASE="${1:-all}"; shift || true
INPUT="/input"; WORK="/app/work"; OUT="/app/output"
while [ $# -gt 0 ]; do case "$1" in --input) INPUT="$2"; shift 2;; --work) WORK="$2"; shift 2;; --out) OUT="$2"; shift 2;; *) shift;; esac; done
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$WORK" "$OUT" "$WORK/sections"
log() { echo "[run] $*"; echo "- $*" >> "$OUT/run_log.md" 2>/dev/null || true; }
step() { local n="$1"; shift; log "STAGE $n"; "$@" >> "$OUT/run_log.md" 2>&1 && log "OK $n" || log "FAIL $n（已留痕，继续）"; }

case "$PHASE" in
  pre)
    step inspect python3 "$SKILL_DIR/scripts/inspect_case.py" --input "$INPUT" --work "$WORK" --out "$OUT"
    [ -f "$SKILL_DIR/scripts/engine_pre.py" ] && step engine_pre python3 "$SKILL_DIR/scripts/engine_pre.py" --input "$INPUT" --work "$WORK" --out "$OUT"
    log "PRE 完成 → 读 $WORK/brief.json 与引擎产物，按 SKILL.md 写稿"
    ;;
  post)
    [ -f "$SKILL_DIR/scripts/engine_check.py" ] && step engine_check python3 "$SKILL_DIR/scripts/engine_check.py" --manuscript "$OUT/manuscript.md" --work "$WORK" --out "$OUT"
    ER=""; [ -f "$OUT/engine_report.json" ] && ER="--engine-report $OUT/engine_report.json"
    step finalize python3 "$SKILL_DIR/scripts/finalize.py" --work "$WORK" --out "$OUT" $ER
    log "POST 完成 → 读 $OUT/validation.md"
    ;;
  all) "$0" pre --input "$INPUT" --work "$WORK" --out "$OUT"; "$0" post --input "$INPUT" --work "$WORK" --out "$OUT";;
  *) echo "usage: run.sh pre|post|all [--input D] [--work D] [--out D]"; exit 2;;
esac
exit 0
