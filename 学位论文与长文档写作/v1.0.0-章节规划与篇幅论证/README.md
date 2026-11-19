# longdoc-chapter-planning（学位论文与长文档写作 · 章节规划方向 v1.0.0）

## 用途
依据大纲与材料做章节规划：每节的论证任务、证据来源、篇幅分配，并校验新写章节
是否符合编号连续、必备要素、预算偏差与数字可溯源性。解决「把材料堆成通顺文字」
而非「按提纲立论」的问题（题面「立得住」）。

## 安装与调用
平台将本目录安装为 `/skills/weekly-skill` 后由 Agent 按 `SKILL.md` 阶段流程执行。
本地试用：`python3 scripts/inspect_case.py --case case.json --task task.md --input-dir . --work work`，
随后按 SKILL.md Phase 1-5 依次执行。

## 依赖
Python 3.8+ 标准库；docx/pdf 材料分别用 zipfile 解析与 pdftotext 降级（pdftotext 缺失时如实记录）。

## 快速开始（最小流程）
1. `init_result.py` + `inspect_case.py` → 2. `parse_chapters.py` → 3. `outline_engine.py plan` →
4. Agent 按 `chapter_plan.md` 写章节 → 5. `outline_engine.py check` → 6. `assemble_result.py` +
   `validate_output.py` + `render_previews.py`。

## 边界与已知限制
- 覆盖映射为字符 2-gram Jaccard 启发式（阈值 0.06），语义近义但未字面重合的材料可能漏配，Agent 应人工复核 `coverage` 列表。
- 大纲「约N字」预算缺失时只做绝对字数报告，不做偏差判定。
- 不支持图片中的数据（pdf 提取后无图）；图表数据须在材料文本中给出。
- 数字派生核验只覆盖四则运算与百分比换算（±1% 容差），容差只豁免舍入，不豁免篡改。
