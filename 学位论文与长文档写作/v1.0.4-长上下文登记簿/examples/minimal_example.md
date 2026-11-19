# 最小调用示例（示例，非正式案例结果）

## 输入（合成）
- `case.json`：{"case_id":"W16-longdoc-synth", "output_contract":{result, main_document,
  evidence_map, change_log, uncertainty, stats}}
- `task.md`：依据大纲与材料撰写第3章「结果与讨论」，保持术语、编号与前文一致
- 章节稿：`ch1_intro.md`（含 SSE/ASSB 定义与「Li6PS5Cl 电导率可达 3.2 mS/cm」结论句）、
  `ch2_method.md`（两步烧结工艺、EIS/XRD/SEM）
- 材料：`facts.md`（6 条事实，其中 XRD 杂相降低 40%、SEM 晶界密度提高两条前文未使用）

## 调用与示意输出（示例，非正式案例结果）

```bash
python3 scripts/dossier_engine.py build --chapters work/chapters.json --work work
# [dossier build] 定义=3 结论=1 材料=6(未用2) 术语=10(脱节候选0) caption=0

python3 scripts/dossier_engine.py brief --dossier work/dossier.json \
  --target-section "第3章 结果与讨论" --budget-chars 3000 --work work
# [dossier brief] 目标「第3章 结果与讨论」预算 3000 字，截断 0 条
```

`work/context_brief.md` 节选：

```
## 前文相关定义（引用术语必须沿用这些写法）
- **固态电解质**（SSE）：固态电解质（solid-state electrolyte, SSE）（首现 C01-S001-P001，第1章 绪论）
## 前文已下结论（不得当作新结论重复宣称）
- （C01-S001-P002，第1章 绪论）已有研究表明，Li6PS5Cl 的电导率可达 3.2 mS/cm [1]。　关键数值：3.2 mS/cm
## 未用材料提醒（与本节相关的应尽量纳入，避免遗漏）
- （C03-S000-P005）- XRD 显示两步烧结样品杂相峰强度降低约 40%
```

Agent 只读 brief 写完 `work/draft_ch3.md` 后复核：

```bash
python3 scripts/dossier_engine.py overlap --draft work/draft_ch3.md \
  --chapters work/chapters.json --dossier work/dossier.json --work work
# 干净稿：[dossier overlap] verdict=PASS_WITH_REMINDERS 重复论述=0 重复结论=0
#         未定义缩写=0(critical 0) 悬空图表=0 材料提醒=2
# 缺陷稿：[dossier overlap] verdict=HAS_ISSUES 重复论述=2 重复结论=1
#         未定义缩写=1(critical 1) 悬空图表=1 材料提醒=1
```

`result.json` 示例（节选）：
```json
{"case_id":"W16-longdoc-synth","status":"success","skill":"longdoc-dossier v1.0.4",
 "outputs":{"chapter_3":"chapter_3.md","context_brief":"context_brief.md",
            "dossier":"dossier.md","overlap_report":"overlap_report.md"}}
```
