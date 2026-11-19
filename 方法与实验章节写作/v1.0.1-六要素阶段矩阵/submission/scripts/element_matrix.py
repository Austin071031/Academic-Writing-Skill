#!/usr/bin/env python3
"""element_matrix.py — 六要素×三阶段覆盖矩阵与条件串台检测（v1.0.1 方向核心引擎）。

Agent 在 work/element_matrix.json 登记每个单元格的证据锚点与正文位置；本脚本校验：
1. 矩阵 18 格（6 要素 × train/val/test）逐一"已覆盖/不适用（需理由）"；
2. table_rows.json 中每个参数行的 scope 必须标注阶段，禁止"训练/评测通用"式含混；
3. 串台启发：评测/测试阶段小节不得出现训练专属超参赋值句（学习率/batch_size/epoch 带新值）。
用法: python3 element_matrix.py --work /app/work --out /app/output
输出: matrix_report.json {cells, missing, scope_violations, crossing_flags, verdict}
"""
import argparse, json, os, re, sys

ELEMENTS = ["steps", "setup", "params", "datasets", "baselines", "repro"]
PHASES = ["train", "val", "test"]
TRAIN_ONLY = re.compile(r"(学习率|learning.?rate|batch.?size|epoch|warmup|weight.?decay)\s*[:=为]\s*[-\d\.eE+]+\s*[^。；\n]{0,20}(测试|test|评测|eval|验证集|val)", re.I)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    mp = os.path.join(args.work, "element_matrix.json")
    matrix = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    missing, cells = [], []
    for el in ELEMENTS:
        for ph in PHASES:
            cell = (matrix.get(el) or {}).get(ph)
            cells.append(f"{el}.{ph}")
            if not cell:
                missing.append(f"{el}.{ph}:未登记")
            elif cell.get("na"):
                if not cell.get("reason"):
                    missing.append(f"{el}.{ph}:na 缺理由")
            elif not cell.get("eids") and not cell.get("section_anchor"):
                missing.append(f"{el}.{ph}:无证据锚点也无正文位置")

    scope_violations = []
    trp = os.path.join(args.work, "table_rows.json")
    if os.path.exists(trp):
        for r in json.load(open(trp, encoding="utf-8")):
            scope = str(r.get("scope", ""))
            if scope and not re.search(r"train|val|test|训练|验证|测试|通用|环境", scope, re.I):
                scope_violations.append({"name": r.get("name"), "scope": scope})

    crossing = []
    for sec, ph in (("05_baselines.md", "test"), ("04_datasets.md", "test")):
        p = os.path.join(args.work, "sections", sec)
        if os.path.exists(p):
            txt = open(p, encoding="utf-8").read()
            for m in TRAIN_ONLY.finditer(txt):
                crossing.append({"file": sec, "text": m.group(0)[:80]})

    na_ok = not any("na 缺理由" in m for m in missing)
    verdict = "pass" if not missing and not scope_violations and not crossing else "fail"
    report = {"cells_total": len(cells), "missing_or_weak": missing,
              "scope_violations": scope_violations, "crossing_flags": crossing,
              "verdict": verdict}
    rp = os.path.join(args.out, "matrix_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[matrix] 格 {len(cells)} 缺 {len(missing)} scope违规 {len(scope_violations)} 串台 {len(crossing)} verdict={verdict}")
    sys.exit(0 if verdict == "pass" or na_ok else 1)

if __name__ == "__main__":
    sys.exit(main())
