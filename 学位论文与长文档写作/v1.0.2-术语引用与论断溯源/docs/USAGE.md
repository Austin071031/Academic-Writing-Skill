# USAGE — longdoc-citation-trace v1.0.2

## 运行环境

- 安装目录 `/skills/weekly-skill`（本目录），输入 `/input`，工作目录 `/app/work`，产物 `/app/output`。
- 全部脚本仅依赖 Python3 标准库；无网络、无第三方包。
- 预算：64 次模型请求 / 900 秒；兜底见 SKILL.md §3。

## 标准流程（与 SKILL.md Phase 对应）

```bash
S=/skills/weekly-skill/scripts
# Phase 0
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
# Phase 1
python3 $S/parse_chapters.py <稿件...> --work /app/work
python3 $S/parse_library.py <文献库...> --work /app/work
cat <事实材料...> > /app/work/materials_all.txt
# Phase 2
python3 $S/trace_engine.py bind   --chapters /app/work/chapters.json --library /app/work/library.json --work /app/work
python3 $S/trace_engine.py verify --chapters /app/work/chapters.json --library /app/work/library.json \
        --materials /app/work/materials_all.txt --work /app/work
# Phase 3（Agent 裁决 + 修订稿 + 批注稿）
python3 $S/trace_engine.py annotate --chapter <原稿件> --audit /app/work/citation_audit.json --work /app/work
# Phase 4（对修订稿复核清零 + 渲染文献表）
python3 $S/parse_chapters.py /app/work/revised_*.md --work /app/work --out-name chapters_revised.json
python3 $S/trace_engine.py verify --chapters /app/work/chapters_revised.json --library /app/work/library.json \
        --materials /app/work/materials_all.txt --work /app/work
python3 $S/trace_engine.py render_refs --library /app/work/library.json --style gbt2015_numeric --work /app/work
# Phase 5
cp /app/work/revised_*.md /app/work/citation_audit.md /app/work/references.md /app/output/
python3 $S/assemble_result.py --work /app/work --out /app/output --skill "longdoc-citation-trace v1.0.2" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
python3 $S/render_previews.py --out /app/output
```

## trace_engine 子命令

| 子命令 | 输入 | 输出 | 退出码 |
|-|-|-|-|
| `bind` | chapters.json + library.json | work/claim_bindings.json | 1=有 unbound |
| `verify` | + materials 合并文本 | work/citation_audit.json / .md（并刷新 claim_bindings.json） | 1=有 unbound |
| `render_refs` | library.json [+ order.json] | work/references.md / references_audit.json / order.json | 1=编号交叉核对失败 |
| `annotate` | 稿件 + citation_audit.json | work/annotated_draft.md | 0 |

## 中间产物格式

### claim_bindings.json
```json
{"claims": [{"claim_id": "CLM001", "pid": "C01-S001-P002",
             "sentence": "已有研究表明……可达 3.2 mS/cm [1]。",
             "cite_marks": [{"raw": "[1]", "style": "numeric", "nums": [1], "span": [24, 27]}],
             "entry_ids": ["R001"], "unresolved": [], "n_marks": 1, "status": "bound"}],
 "stats": {"n_claims": 1, "bound": 1, "partially_bound": 0, "unbound": 0, "n_records": 2}}
```

### citation_audit.json（四节）
- `unbound[]`：critical 引用存在性问题（含 partially_bound 的未命中部分）；
- `numeric[]`：`{value, verdict: verbatim|derived|unverified, evidence, sentence, pid}`；
- `tone[]`：`{issue: overstated|negation_flip|overstated+negation_flip, claim_tone_level,
  material_tone_level, material_sentence}`——候选，供 Agent 裁决；
- `missing_citation[]`：`{pid, sentence, unverified_numbers, candidates: top3}`。

### evidence_map.json（Agent 填写，status=success 时不得为空）
```json
[{"claim_id": "CLM001", "pid": "C01-S001-P002", "sentence": "……可达 3.2 mS/cm [1]",
  "source": "materials/facts.md", "support": "verbatim",
  "verification": "trace_engine verify: verbatim（绑定 R001）"}]
```

### change_log.json
```json
[{"op": "replace", "location": "ch1#P001", "before": "可达 9.9 mS/cm [5]",
  "after": "可达 3.2 mS/cm [1]", "reason": "verify: [5] 越界 unbound + 9.9 unverified",
  "tool": "agent-adjudicated"}]
```

### uncertainty.json / manual_confirmations.json / exceptions.json
- uncertainty：`{"item": "……", "reason": "……", "needs": "作者确认"}`；
- manual_confirmations：误报豁免说明（引擎候选被 Agent 判定为误报时必填理由）；
- exceptions：解析降级、材料缺失等异常记录。

## 术语与缩写统一检查清单（Agent）

1. 列出现稿全部缩写及首次出现位置；首次处须「全称（英文, 缩写）」；
2. 同一概念多种中文写法 → 选定一种，全文替换并记 change_log；
3. 替换只动写法，不动数值与论断含义；替换后重跑 verify 确认零新增问题。
