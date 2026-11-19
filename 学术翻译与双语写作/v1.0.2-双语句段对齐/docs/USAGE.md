# 使用与方法说明 — bilingual-alignment-guard v1.0.2

## 完整调用步骤

| 步骤 | 命令 / 动作 | 输入 → 输出 | 说明 |
|-|-|-|-|
| 1 | `init_result.py` | → result.json 骨架 | 防超时空手 |
| 2 | `inspect_case.py --work $W` | /input → inspection.json | 方向/形态/材料 |
| 3 | `parse_manuscript.py --work $W` | 稿件 → structure.json | 稳定 ID |
| 4 | `segment_builder.py --work $W` | → segments.json | 句段六分类 |
| 5 | `align_engine.py plan --work $W` | → alignment_plan.json | 有序句段表 + 结构不变量 |
| 6 | Agent 分批翻译 | → translations.jsonl | 严格逐 seg_id 一条译文 |
| 7 | `assemble_translation.py` | → translation_full.md / bilingual.md | 缺译标记+溯源 |
| 8 | `align_engine.py audit --work $W --out $O` | → alignment.json / align_audit.json + findings | 覆盖/未知 ID/长度/结构锚点 |
| 9 | Agent 复核修订 | → 追加修订 → 重跑 7、8 | 缺译清零/疑似裁决/结构修复 |
| 10 | report_builder → assemble_result → validate_output → render_previews | → /app/output | 报告、契约、闸门、预览 |

## 关键方法

1. **句段六分类**：heading / body（句子级）/ caption（图表题注整段）/ footnote /
   formula（不译）/ reference（不译），分类决定翻译与核对策略。
2. **结构不变量**：译前登记图表编号集合（Figure 1 / 表 2 …）、脚注标记、公式块数、
   参考文献条目数；译后在交付物上重集合并比对，编号跨语言映射（Figure N↔图N）按
   数字归一。
3. **逐句段状态机**：aligned / missing / suspect_length / kept_original，
   alignment.json 可机读驱动后编辑界面。
4. **双语对照稿**：段落级阅读单元 + 句段级定位坐标 〔PID〕，逐段修改不影响其他段。

## 适用场景与限制

- 适用：投稿翻译对照审校、学位论文双语稿、需要逐段回溯的翻译流程。
- 限制：词级对齐不在范围；图片文字不可读部分如实标注。

## 失败处理与自查

- 自查：`validate_output.py` PASS；`align_audit.json` missing=0（否则 partial）；
  图表编号集合一致；`stats.coverage`=1.0。
- 常见失败：译文 seg_id 笔误（unknown_seg_id）；把两个句段合成一条译文
  （另一句段缺译被检出——按 SKILL 红线的合译约定处理）。

## 最小示例

见 `examples/minimal_example.md`（合成，标注“示例”）。
