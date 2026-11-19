# USAGE｜完整调用步骤（v1.0.2 研究空白推导链）

执行序列与 v1.0.0 相同，差异：Phase 3 登记 gap_chain.json；Phase 4 首跑 gap_chain.py。

```bash
S=/skills/weekly-skill/scripts
# Phase 0-1 同共享管线（init/inspect/parse_*/extract_facts）
# Agent 写作：evidence_map.json → gap_chain.json → draft_intro.md（空白段与链一致）
#   → draft_rl.md → claim_bindings.jsonl
python3 $S/gap_chain.py --work /app/work --out /app/output
python3 $S/build_deliverables.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "research-gap-derivation v1.0.2" --status success
python3 $S/validate_output.py --out /app/output --expect-status success
python3 $S/render_previews.py --out /app/output
```

## 输出

gap_derivation.md（逐条：前提摘录→缺口→本文对应→校验结果）、introduction.md、related_work.md、
references.md、evidence_map.json、build_report.json、version_report.json、result.json、preview.html。

## 自查要点

- version_report.json：n_gaps ≥1；每条 issues 空；number_leaks 空；verdict=pass。
- gap_derivation.md 的"遮住缺口句、仅凭前提能否推出"自检。
- build_report.json：锚点全解析、绑定 ≥90%、四要素全 true。

## 失败处理

number_leaks：删除泄漏数字或为其补前提；前提不可溯源：改引现有条目或补 manuscript_loc；
材料不足：gaps 置空 + uncertainty 说明 + status=partial。全部脚本幂等。
