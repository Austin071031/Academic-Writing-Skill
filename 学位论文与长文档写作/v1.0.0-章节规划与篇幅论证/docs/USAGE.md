# 使用说明（USAGE）

## 输入与输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件（章节稿 md/txt/tex/docx/pdf；
  大纲 md/txt/tex；事实材料 md/txt；文献库 bib/ris/enw/ciw/csv/json）。
- 中间产物（`/app/work`）：`inspection.json`（输入清单）、`chapters.json`（分章段落）、
  `outline.json`（大纲条目树）、`chapter_plan.{json,md}`（规划）、`coverage_report.md`（缺口与重复）、
  `chapter_check.json`（校验结果）、`evidence_map.json` / `change_log.json` /
  `uncertainty.json` / `manual_confirmations.json` / `exceptions.json` / `stats.json`。
- 交付（`/app/output`）：`chapter_plan.md`、`coverage_report.md`、章节稿 `chapter_<N>.md`、
  `result.json`（含 output_contract 全部字段）、`preview.html`（可选 `preview.pdf`）。

## evidence_map.json 格式

```json
[{"claim_id": "CL01", "pid": "C03-S001-P002", "sentence": "最高电导率达到 5.8 mS/cm",
  "source": "materials/facts.md:批次B7记录", "support": "verbatim",
  "verification": "outline_engine check: verbatim"}]
```
每条事实、每个数字、每条引用一行；`support` ∈ verbatim/derived/partial/unverified。

## change_log.json 格式

```json
[{"op": "insert", "location": "chapter_3.md#3.2", "before": "", "after": "新增小节 3.2 电导率测试",
  "reason": "按大纲 O04 要素「电导率测试」补全", "evidence": "chapter_plan.json#O04"}]
```

## 自查方法（评分前自检）

1. `validate_output.py --out /app/output --work /app/work` 必须 PASS。
2. `result.json` 中 `output_contract` 声明的字段全部存在；`status` 与实际相符。
3. `chapter_check.json` 无 `issues`；`warnings` 均有处置记录（修复 / manual_confirmations）。
4. 随机抽 3 个数值：能在材料原文找到（verbatim）或有 derived 推导链。
5. `chapter_plan.md` 每节都有「论证任务 + 证据来源」；`no_material_yet` 条目均有
   uncertainty 登记。

## 完整调用序列（参考）

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_chapters.py $(ls /input/chapters/*.md /input/materials/*.md) --work /app/work
python3 scripts/parse_library.py /input/materials/refs.bib --work /app/work
python3 scripts/outline_engine.py plan --chapters /app/work/chapters.json --outline /input/outline.md --work /app/work
# Agent 撰写章节 → /app/work/draft_ch3.md
cat /input/materials/facts.md > /app/work/materials_all.txt
python3 scripts/outline_engine.py check --chapter /app/work/draft_ch3.md \
  --chapters /app/work/chapters.json --plan /app/work/chapter_plan.json \
  --materials /app/work/materials_all.txt --work /app/work
cp /app/work/chapter_plan.md /app/work/coverage_report.md /app/output/
cp /app/work/draft_ch3.md /app/output/chapter_3.md
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-chapter-planning v1.0.0" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work
python3 scripts/render_previews.py --out /app/output
```

## 篇幅与规模上限

- 单文件 200 KB 以上将截断读取前 200 KB（inspect）；`parse_chapters.py` 全量读取，
  单稿超过 5 MB 时建议按文件分开调用并在 exceptions 记录。
- 数字溯源候选值上限：材料中不重复数值超过 500 个时派生校验退化为 verbatim-only（性能保护，记入 stats）。
