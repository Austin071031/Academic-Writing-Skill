# task-adaptive-translation v2.0.2

学术翻译与双语写作 Skill（v2 迭代·任务自适应方向，父辈 v1.0.1）：识别整篇翻译 /
译文校对 / 修订标记 / 双语写作四类任务并分支执行；校对模式把已有译文对齐回
句段坐标复用全套机检与交付管线。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
# 查看 inspection.json 的 translation_task.task_type，按分支执行：
# A 整篇翻译：parse → segment → ledger → Agent 翻译
# B 校对审校：
python3 $S/parse_manuscript.py --work $W --file /input/<原文>
python3 $S/segment_builder.py --work $W && python3 $S/number_engine.py ledger --work $W
python3 $S/align_existing_translation.py --work $W --translation-file /input/<译文>
# 公共阶段：
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "task-adaptive-translation v2.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "task-adaptive-translation v2.0.2" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、原文（±现有译文/事实底稿）。
- 输出：按分支交付纯译文/双语对照/审校标注稿 + 机检产物 + `result.json`。

## 边界

- 已有译文对齐为启发式，needs_review 映射须 Agent 复核；任务识别以 task.md 为准。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v2.0.2-任务类型自适应/`）
- 变更历史见 `CHANGELOG.md`（含 v1.0.1 评分基线）。
