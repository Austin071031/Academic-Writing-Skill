# 使用与方法说明 — citation-semantic-boundary v1.0.4

## 完整调用步骤

| 步骤 | 命令 / 动作 | 输入 → 输出 | 说明 |
|-|-|-|-|
| 1 | `init_result.py` | → result.json 骨架 | 防超时空手 |
| 2 | `inspect_case.py --work $W` | /input → inspection.json | 方向/形态/材料 |
| 3 | `parse_manuscript.py --work $W` | 稿件 → structure.json | 稳定 ID |
| 4 | `segment_builder.py --work $W` | → segments.json | 句段分类；参考文献逐条拆分 |
| 5 | `boundary_engine.py index --work $W` | → citation_index.json | 逐句段引用标记+六类语气标记+文献条目 |
| 6 | Agent 分批翻译 | → translations.jsonl | 引用原样、语气等强、禁止增译 |
| 7 | `assemble_translation.py` | → translation_full.md / bilingual.md | 缺译标记+溯源 |
| 8 | `boundary_engine.py audit --work $W` | → boundary_audit.json / audit_annotated.md + findings | 引用多重集比对+语气迁移+增译数字 |
| 9 | Agent 复核修订 | → 追加修订 → 重跑 7、8 | 处置 findings；可扩展词表重跑 |
| 10 | report_builder → assemble_result → validate_output → render_previews | → /app/output | 报告、契约、闸门、预览 |

## 关键方法

1. **引用三形态归一**：数字型 `[1]`/`[2-4]`、括号著者-年型 `(Zhang et al., 2023)`、
   叙述型 `Zhang et al. (2022)`；归一时全角转半角、去空白、小写，
   多重集（multiset）逐句段比对——缺失与新增都报。
2. **六类语气索引**：possibility/suggestion/approximation/limitation/negation/certainty
   双向词表；源有译无 → 强度丢失（否定=高，其余=中）；源无 certainty 而译文有 → 语气升格（高）。
3. **参考文献条目指纹**：条目按 [n] 逐条拆分登记首 60 字符指纹，译后交付物逐条回查。
4. **⚠ 标注稿**：问题句段原文/译文/机检意见三联对照，供作者快速复核。

## 适用场景与限制

- 适用：引用密集论文翻译、双语写作审校、学位论文翻译合规检查。
- 限制：句式承担的否定/限定可能误报（复核兜底，词表可扩展）；引文-论断语义
  相关性不在范围。

## 失败处理与自查

- 自查：`validate_output.py` PASS；`boundary_audit.summary.citation_fidelity`=1.0
  且 reference_entries_missing=0；高严重度清零；`stats.coverage`=1.0 否则 partial。
- 常见失败：译文把 (Zhang et al., 2023) 意译成“张等人（2023）”——违反红线 1，
  必须恢复原文形态；全角括号（Zhang et al., 2023）允许。

## 最小示例

见 `examples/minimal_example.md`（合成，标注“示例”）。
