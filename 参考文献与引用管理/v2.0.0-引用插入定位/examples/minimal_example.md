# minimal_example.md — 最小示例（示例，非正式案例结果）

> 本示例全部为合成数据，仅演示输入 → 调用 → 产物形态。

## 输入

稿件 `/input/manuscript.md`：

```markdown
# 示例稿件

硅的理论比容量为 4200 mAh/g。本文制备的硅碳复合材料首周效率达 88%。
```

文献库 `/input/refs.bib`：

```bibtex
@article{si, title={Silicon Anodes: A Review}, author={Smith, John},
  year={2020}, journal={Nature Energy}}
```

task.md：`按 GB/T 7714-2015 顺序编码制插入引用。`

## 调用（命令摘要）

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_manuscript.py /input/manuscript.md --work /app/work
python3 scripts/parse_library.py /input/refs.bib --work /app/work
```

Agent 写 `work/citation_decisions.jsonl`（只给量化事实句配引用；**第二句是作者新结果，不引**）：

```json
{"claim_id": "C1", "pid": "P002", "sentence": "硅的理论比容量为 4200 mAh/g", "claim_type": "quantitative_fact", "entry_ids": ["R001"], "rationale": "量化事实需来源", "position": "after_sentence", "form": "numeric"}
```

```bash
python3 scripts/place_citations.py --decisions /app/work/citation_decisions.jsonl \
  --manuscript /app/work/manuscript.json --library /app/work/library.json \
  --work /app/work --out /app/output --style gbt2015_numeric --form auto
python3 scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
  --skill "citation-placement-skill v1.0.0" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work --expect-status success
python3 scripts/render_previews.py --out /app/output --work /app/work
```

## 示意输出

`/app/output/edited_manuscript.md`：

```markdown
# 示例稿件

硅的理论比容量为 4200 mAh/g[1]。本文制备的硅碳复合材料首周效率达 88%。
```

`/app/output/references.md`：

```markdown
## 参考文献

[1] Smith, John. Silicon Anodes: A Review[J]. Nature Energy, 2020.
```

要点：标记插在论断句末（`[1]` 在句号之前）；作者新结果句未被加引用；编号 1 起连续。
