# USAGE.md — 调用细节与产物格式

## 1. 命令参考

### dossier_engine.py build
```bash
python3 scripts/dossier_engine.py build --chapters work/chapters.json \
  --work /app/work [--materials-regex REGEX] [--usage-threshold 0.15]
```
- 输入：parse_chapters.py 产出的 chapters.json。
- `--materials-regex`：材料文件名识别正则（默认内置 fact/note/material/材料/笔记
  等提示词）；隐藏案例材料文件名不规则时必用。
- 输出：`work/dossier.json`（机器读）、`work/dossier.md`（人读）。

dossier.json 结构：
```json
{
  "stats": {"n_definitions": 3, "n_conclusions": 1, "n_omissions": 2, "...": 0},
  "definitions": [{"term": "固态电解质", "abbr": "SSE", "en": "solid-state electrolyte",
                   "definition": "…", "first_pid": "C01-S001-P001", "chapter": "第1章 绪论"}],
  "conclusions": [{"pid": "…", "sentence": "…", "chapter": "…", "key_numbers": ["3.2 mS/cm"]}],
  "material_files": ["C03"], "manuscript_files": ["C01", "C02"],
  "material_usage": [{"material_pid": "…", "text": "…",
                      "used_by": [{"pid": "…", "score": 0.35}]}],
  "omissions": [{"pid": "…", "text": "…"}],
  "glossary_first_use": [{"token": "SSE", "kind": "abbr", "first_pid": "…",
                          "definition_pid": "…", "detached_use": false}],
  "captions": [{"kind": "figure", "number": "2-1", "pid": "…", "text": "…"}]
}
```

### dossier_engine.py brief
```bash
python3 scripts/dossier_engine.py brief --dossier work/dossier.json \
  --target-section "第3章 结果与讨论" [--budget-chars 3000] --work /app/work
```
- `--target-section` 传完整目标标题（含主题词，相关性排序才有效）；
  有大纲时取大纲条目名。
- 输出 `work/context_brief.md`：五桶（定义/结论/未用材料/已用材料/caption）
  + 末尾「截断记录」。**写作阶段只读本文件与 dossier.md，不读全文。**

### dossier_engine.py overlap
```bash
python3 scripts/dossier_engine.py overlap --draft work/draft_ch3.md \
  --chapters work/chapters.json --dossier work/dossier.json --work /app/work \
  [--overlap-threshold 0.6] [--remind-threshold 0.1]
```
- 输出 `work/overlap_report.json/.md`；`counts.critical_total` 与 `verdict`
  决定能否交付（HAS_ISSUES 必须修复复跑或降级 partial）。

## 2. work/ 下配套 JSON 格式（assemble_result.py 消费）

```json
// evidence_map.json
[{"claim": "两步烧结样品杂相峰强度下降约40%", "source": "C03-S000-P005", "type": "material"}]
// change_log.json
[{"action": "add|fix|delete", "target": "chapter_3.md", "reason": "…"}]
// uncertainty.json / exceptions.json
[{"item": "…", "reason": "…", "severity": "low|medium|high"}]
// manual_confirmations.json
[{"item": "overlap warning 内容", "decision": "不修复/已修复", "basis": "理由"}]
// stats.json
{"requests_estimated": 12, "budget_fallback": false,
 "overlap_final": "PASS_WITH_REMINDERS", "budget_chars_brief": 3000}
```

## 3. 与共享脚本的衔接

1. `init_result.py` → 骨架 result.json（防超时空手）；
2. `inspect_case.py` → inspection.json（材料/章节/大纲候选清单）；
3. `parse_chapters.py` → chapters.json（本引擎唯一上游依赖）；
4. dossier_engine build/brief/overlap（本版核心）；
5. `assemble_result.py`（汇总 work/*.json + 回填 output_contract 字段）→
   `validate_output.py`（交付闸门）→ `render_previews.py`（HTML 预览）。

## 4. 隐藏案例操作建议

- 输入文件多时分不清章节与材料：先看 inspection.json 的
  `manuscript_candidates`/`notes_candidates` 分类，再用 `--materials-regex`
  精确指定。
- 多轮写作（写多个章节）：每写完一章，把新章追加进 parse_chapters 的输入
  重建 chapters.json 与 dossier，再为下一章生成 brief——登记簿始终反映
  「截至目前的全部前文」。
- 单次响应 16384 token 限制下，brief 默认 3000 字符可安全读入；
  全文数十万字时 dossier.md 也可分节读取（定义节通常最短，优先读）。
