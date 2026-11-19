---
name: ref-format-converter
description: 文献库格式转换与字段补齐审计。触发：任务要求把 BibTeX/RIS/EndNote/CNKI 等导出转换为 GB/T 7714—2015（顺序编码制或著者-出版年）、APA 7、Vancouver 等目标规范，或要求"整理参考文献格式/补齐缺失字段/统一中英文标点/回转导出 bibtex/ris"。不触发：需要联网核实文献真伪、按正文论点匹配引用、去重合并（那是v1.0.2/5的职责）。产出：converted_refs.txt、references.md、field_audit.json、convert_report.md、result.json、preview.html。
---

# v1.0.3｜格式转换与字段补齐（ref-format-converter）

核心方法：**声明式格式映射表**（references/format_specs/ 每个规范一个数据文件，引擎运行时解析，
不硬编码）+ **字段补齐审计**（缺字段逐条登记，补齐仅允许可溯源的跨条目互补）。

文中 `SKILL_DIR=/skills/weekly-skill`。所有命令逐字可执行。

## Phase 0 — 初始化与案件解析（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 动作：读 `/app/work/inspection.json`，确认 `library_candidates`（文献库文件及其嗅探格式）
与 `constraints.style_mentioned`（任务书提到的规范名）。文献库为空 → 跳到异常表第 7 行。

## Phase 1 — 解析文献库

```bash
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件1> <文献库文件2> ... --work /app/work
```

文献库文件清单从 inspection.json 的 `library_candidates[].path` 逐字抄入命令行。
Agent 动作：读 `/app/work/library.json`，抽查 2-3 条记录的 entry_type / language /
field_presence 是否与原文相符；发现解析异常（issues 非空）写入 `/app/work/exceptions.json`。

## Phase 2 — 目标风格判定（Agent 判断，规则如下）

读 `/input/task.md` 与 inspection.json 的 constraints，按**第一条命中**执行：

1. 提到 `GB/T 7714` / `国标` / `顺序编码` → `gbt2015_numeric`
2. 提到 `著者-出版年` / `author-year`（且属 GB/T 语境）→ `gbt2015_author`
3. 提到 `APA` → `apa7`
4. 提到 `Vancouver` / `温哥华` / `ICMJE` / `IEEE 数字` → `vancouver`
5. 要求"导出回 bibtex / ris" → `bibtex` / `ris`
6. 均未提及 → `gbt2015_numeric`（默认，并在 uncertainty.json 记录"任务未指明规范，按默认"）

中英文混排文献库**无需特殊选择**：转换引擎按每条记录的 `language` 分别处理标点
（英文条目半角、中文条目全角），规则见 `references/punctuation_rules.md`。

## Phase 3 — 转换 + 字段审计（一次命令完成）

```bash
python3 /skills/weekly-skill/scripts/convert_engine.py --library /app/work/library.json \
    --to <Phase 2 判定的目标> --outdir /app/output --work /app/work \
    --specs-dir /skills/weekly-skill/references/format_specs --try-online
```

产物（/app/output）：`converted_refs.txt`、`references.md`（+references.json）、
`field_audit.json`、`convert_report.md`、`report.md`。
引擎行为：调用 cite_engine render/convert 生成目标格式；类型标识读
`gbt_type_tags.md`；作者名 `Smith, John`→`Smith J`；标点按语种规范化；
同题同年同类型重复条目字段互补记 `copied_from_Rxxx`；其余缺字段记 `not_provided`；
`--try-online` 以 5 秒超时探测 Crossref，失败诚实记录 `unverified`，**绝不自动补值**。

Agent 动作：读 `/app/output/field_audit.json` 与 `convert_report.md`；
对 `fields_dropped_in_render` 非空的条目人工复核并写入
`/app/work/manual_confirmations.json`（格式：`[{"item":"...","note":"...","rids":[...]}]`）。

## Phase 4 — 审查与不确定性登记

Agent 写两个文件（若无可写空数组 `[]`）：

- `/app/work/uncertainty.json` — 如：`[{"item":"target_style","note":"任务未指明，默认 gbt2015_numeric"}]`
- `/app/work/manual_confirmations.json` — 追加需人工确认的条目（疑似字段丢失、
  姓名形不确定、中文条目含小数点被全角化等）。

判据：`field_audit.summary.field_retention_rate < 0.95` 时必须在 uncertainty.json 说明原因。

## Phase 5 — 汇总、校验、预览（固定收尾，不得省略）

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
    --case /input/case.json --skill "ref-format-converter v4.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

validate FAIL 或存在未决 `not_provided` 关键字段（year/title 缺失）时，把 `--status success`
改为 `partial` 重跑 assemble 再校验。

## 三条红线

1. **不臆造文献与元数据**：缺卷/期/页/DOI 一律 `not_provided` 并标注"材料未提供，不得臆造补齐"；
   唯一允许的补齐是同题同年同类型重复条目的字段互补（`copied_from_Rxxx`，来源可溯）。
2. **不臆造核验结果**：联网探测必须 try + 5 秒超时；失败即 `unverified` 记录 exceptions；
   不得把未验证的数据写进条目。
3. **不改编号/字段不走引擎**：所有转换、作者截断、标点规范化必须经 convert_engine/cite_engine
   完成；Agent 只判定目标风格与审查审计，不手写条目、不手改输出文件。

## 异常处置表

| 异常 | 处置 |
|---|---|
| 字段缺失（卷/期/页/DOI） | field_audit 记 `not_provided`，convert_report 第 4 节列出；不补齐 |
| DOI 解析失败 / 联网探测失败 | 5s 超时捕获 → exceptions.json 记 `unverified`；继续离线流程 |
| 条目歧义（同题不同年/不同类型） | 拒绝跨条目互补，双方均记 `not_provided`，写 manual_confirmations |
| 编号/样式冲突 | 本版本不改编号；发现正文编号问题仅写 uncertainty，交给v1.0.1 |
| 不支持的稿件/文献库格式 | parse_library 降级 numbered_plain 并在 issues 记录；Agent 写 exceptions.json |
| 文件损坏/无法解码 | parse_library 跳过并记 issue；Agent 写 exceptions.json，status 降 partial |
| 文献库为空 | convert_engine 退出码 1；assemble 用 `--status partial`，result 说明无输入 |
| 超时风险 | 见下"预算兜底" |

## 预算兜底

若模型请求已过半仍未完成 Phase 3：立即以当前 library.json 跑一次 convert_engine
（不加 `--try-online`），随后直接执行 Phase 5 并以 `--status partial` 交付；
未完成的审查动作写入 exceptions.json（`"budget_fallback": true`）。
