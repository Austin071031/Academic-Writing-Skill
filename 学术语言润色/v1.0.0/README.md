# academic-language-polisher（学术语言润色 Skill）

术语表驱动 + 限定强度守恒 + 逐句留痕的学术语言精修流水线。交付改得对、说得像、
没改坏、讲得清的润色结果：润色后完整文本、逐句修改清单（原文/改文/类型/理由）、
术语表、原文—改文对照、审校报告与结构化 result.json。

## 仓库结构

```
SKILL.md                  # Skill 本体：触发条件、执行流程、铁律、异常处置
scripts/                  # 确定性脚本（仅 Python 3.8+ 标准库，PDF/预览依赖自动降级）
  run_pipeline.sh         #   阶段0一键预检
  inspect_case.py         #   case.json/task.md 解析、材料盘点、编码与约束识别
  extract_text.py         #   多格式文本提取 + 带稳定 ID 的分句
  terminology.py          #   术语表构建（build）与全篇一致性回扫（check）
  guard_check.py          #   数值/引用/指向/限定强度/否定/因果 守恒检查
  assemble.py             #   产物组装（全文、对照、清单、报告、result.json）
  render_previews.py      #   HTML/PDF/PNG 预览（无 CJK 字体时诚实降级）
  init_result.py          #   result.json 诚实骨架（尽早落盘）
  validate_output.py      #   发布闸门：契约/覆盖/闭环终检
references/               # 编辑策略、文体指南、限定词表、术语治理、异常处置、走查示例
examples/minimal_example.md  # 最小调用示例（示意输出标注为示例）
docs/USAGE.md             # 完整使用说明（复用方法、限制、自查清单）
evaluation/               # 可复用评分表 + 合成测试文本（埋点与期望行为）
CHANGELOG.md              # 版本记录
```

## 设计要点

- **最小编辑原则**：只改需要改的，正确但平淡的句子保持原样（keep 也留痕）。
- **不许动清单**：数值、单位、统计量、引用编号、图表指向、限定强度、否定范围、
  因果/相关性质——由 guard_check.py 机械复核，critical 必须改正或在 resolutions.jsonl 记录处置。
- **术语表驱动**：build 抽取缩写定义与高频候选，check 全篇回扫变体漂移与缩写首现。
- **诚实降级**：材料缺口、编码异常、无法提取、未决项全部写入 result.json 的
  uncertainty / manual_review_required；validate 非零退出不得宣告完成。

## 快速验证（本地）

```bash
bash scripts/run_pipeline.sh /input /app/work /app/output
# 按 SKILL.md 阶段1-7 执行
```

评测环境：Skill 安装于 /skills/weekly-skill，输入 /input/case.json + task.md + 材料，
产物落 /app/output（含 result.json，保留 case_id 与 output_contract 全字段）。
