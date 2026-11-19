# 使用与方法说明 — translation-terminology-lock v1.0.0

## 完整调用步骤

| 步骤 | 命令 / 动作 | 输入 → 输出 | 说明 |
|-|-|-|-|
| 1 | `init_result.py` | case.json → output/result.json 骨架 | 防超时空手，幂等 |
| 2 | `inspect_case.py --work $W` | /input → work/inspection.json | 翻译方向（en2zh/zh2en）、交付形态、材料哈希、稿件候选排序 |
| 3 | `parse_manuscript.py --work $W [--file 路径]` | 稿件 → work/structure.json | 章节/段落/句子稳定 ID；md/tex/txt/docx/pdf |
| 4 | `segment_builder.py --work $W` | structure.json → work/segments.json + source_for_translation.md | 句段分类（heading/body/caption/footnote/formula/reference）+ 受保护片段预抽取 |
| 5 | `term_engine.py seed --work $W` | segments.json → work/glossary_seed.json | 三类候选：缩写定义对、大写复合词（≥2 次）、高频名词短语（≥3 次） |
| 6 | Agent 审定 | glossary_seed.json → work/glossary.json | 锁定译名 + rationale；删噪声；学科歧义写 discipline_note |
| 7 | Agent 分批翻译 | source_for_translation.md → work/translations.jsonl | 每行 `{"seg_id":…,"translation":…}`；追加式，可分批多次写 |
| 8 | `assemble_translation.py --work $W --out $O` | segments + translations → translation_full.md / bilingual.md / stats / evidence_map / change_log | 缺译自动标记并计 uncertainty；重跑自动 diff 记 change_log |
| 9 | `term_engine.py audit --work $W` | glossary + translations → term_audit.json + findings.json | 逐句段核对锁定译名；缩写首现全称检查 |
| 10 | Agent 复核修订 | term_audit → translations.jsonl 追加修订 → 重跑 8、9 | 删误报/补漏报/修译文 |
| 11 | `report_builder.py` → `assemble_result.py` → `validate_output.py` → `render_previews.py` | work → /app/output | 报告、契约组装、发布闸门、HTML 预览 |

## 关键方法

1. **句段级翻译单元**：全文切成带稳定 ID 的句段（与原文结构模型同坐标），译文按 ID 回收，
   因此任何缺译、串段、术语漂移都可定位到 `SEC/P-s` 坐标。
2. **术语三类候选**：缩写定义对（`full name (ABBR)`）几乎必为术语；大写复合词与高频
   名词短语为候选，由 Agent 按学科知识取舍——脚本不臆断术语边界。
3. **锁定-核对闭环**：glossary.json 是唯一事实源；audit 对每个术语统计
   出现次数/合规次数/违规句段，违规定位到句段并给出修订指令。
4. **增量安全**：translations.jsonl 后写覆盖先写，任何阶段中断都可从已有译文组装
   诚实 partial 结果。

## 适用场景与限制

- 适用：术语密集的整篇论文/学位论文章节翻译（英译中、中译英）、需交付双语对照的场景。
- 限制：候选抽取依赖词形与频次；无标点长段、扫描版 PDF（无文本层）会降级，
  降级在 inspection/uncertainty 中如实记录。

## 失败处理与自查

- 自查：`validate_output.py` 必须 PASS；`term_audit.json` 的 `summary.violations` 应为 0
  （或剩余项均在 findings.json 标“已驳回”并附理由）；`stats.json` 的 `coverage` 应为 1.0，
  否则 status 必须是 partial。
- 常见失败：译文 JSONL 行格式错误（assemble 会跳过并在 sources 计数偏低）；
  seg_id 笔误（assemble 记入 unknown_seg_id）；glossary.json 未生成（audit 退回 seed 并告警）。

## 最小示例

见 `examples/minimal_example.md`（合成稿件 + 合成译文，标注“示例”）。
