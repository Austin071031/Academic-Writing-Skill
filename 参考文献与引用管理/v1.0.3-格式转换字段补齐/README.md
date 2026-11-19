# v1.0.3｜格式转换与字段补齐（ref-format-converter）

把 BibTeX / RIS / EndNote / CNKI(GB/T 文本) 等文献库导出，转换为
**GB/T 7714—2015（顺序编码制 / 著者-出版年）、APA 7、Vancouver**，并可回转导出 bibtex / ris。

## 创新点

1. **声明式格式映射表**：每个目标规范一个数据文件（`references/format_specs/*.md`），
   引擎运行时简单解析（模板、作者截断、标点、类型标识表），改数据文件即改行为，脚本零硬编码映射。
2. **字段补齐审计**：转换后逐条审计卷/期/页/DOI 等字段；缺失一律
   `not_provided`（"材料未提供，不得臆造补齐"）；唯一允许的补齐是**同题同年同类型重复条目的
   字段互补**（`copied_from_Rxxx`，来源可溯）；联网探测 5 秒超时 + 失败诚实记录 `unverified`。

## 安装

整个目录安装为 `/skills/weekly-skill`（自包含，仅依赖 Python3 标准库）。

## 快速开始

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_library.py /input/refs.bib --work /app/work
python3 scripts/convert_engine.py --library /app/work/library.json --to gbt2015_numeric \
    --outdir /app/output --work /app/work --specs-dir references/format_specs --try-online
python3 scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "ref-format-converter v4.0.0" --status success
python3 scripts/validate_output.py --out /app/output
python3 scripts/render_previews.py --out /app/output
```

完整流程见 `SKILL.md`（Phase 0-5 逐字命令）与 `docs/USAGE.md`。

## 边界

- 不做文献真伪核验、不做正文-引用匹配、不去重合并（分别属其他版本）。
- 联网补齐默认禁用；`--try-online` 仅探测并记录，不自动写值。
- 页码缩写（200-210 → 200-10）、刊名缩写等需要外部词表的改写**不做**，照录材料原值。
