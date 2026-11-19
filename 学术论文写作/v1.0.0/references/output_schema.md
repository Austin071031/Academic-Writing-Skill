# result.json 与 /app/output 布局约定

## result.json 结构（assemble_result.py 自动生成，可按需增补）
顶层固定字段：

| 字段 | 内容 |
|-|-|
| `case_id` | 与 /input/case.json 一致（必须） |
| `status` | `success`（manuscript 存在且一致性 PASS/WARN）/ `partial`（manuscript 存在但核验 FAIL 或部分产物缺失）/ `failed`（无 manuscript） |
| `generated_utc` | 生成时间 |
| `deliverables` | 产物路径字典（只列真实存在的文件） |
| `sources` | 材料索引位置、facts/bibliography 计数、证据映射说明 |
| `consistency_verdict` | PASS / WARN / FAIL |
| `uncertainty` | 待确认、材料缺口、降级说明的完整列表 |
| `change_log` | 改写留痕条目（来自 change_log.md） |
| `run_log` | 运行日志路径 |
| `stage` | `final`（骨架阶段为 `inspect_complete`） |

随后是 case.json `output_contract` 中的**每个原始字段**（assemble_result 按字段名语义映射填充：
manuscript/evidence/uncertainty/change_log/consistency/preview/summary 等类别；
无法识别的字段填 summary 结构化说明，绝不省略字段、绝不填假内容）。

## /app/output 布局
```
/app/output/
├── result.json               # 契约结果（先骨架后终版）
├── manuscript.md             # 终稿（可编辑，章节层级/图注/引用完整）
├── manuscript.docx           # 可编辑版（pandoc 或 python-docx 生成；不可得时如实缺省）
├── manuscript.pdf            # 渲染预览（LibreOffice/pandoc；不可得时如实缺省）
├── preview/page-*.png        # PDF 前若干页 PNG
├── evidence_map.md           # 论断/数字/引用 → 来源锚点映射表
├── evidence_map.json         # （自 /app/work 同步，如存在）
├── consistency_report.md/.json  # 机读核验报告
├── change_log.md             # 修改记录（改稿/校对任务必填）
├── preview_manifest.json     # 渲染各步状态（含 unavailable 原因）
├── validation.md             # 交付终检结果
└── run_log.md                # 全程运行日志
```

## /app/work 中间产物（复核依据，随运行保留）
```
/app/work/
├── brief.json                # 预检：任务类型/必备章节/字数/引用格式/材料清单/ISSUE
├── material_index.json       # 材料索引（含每段锚点）
├── materials_digest.md       # 限长材料摘要
├── facts.json / facts_digest.md   # 事实底稿
├── bibliography.json         # 文献库
├── text/Mxx.txt              # 各材料提取全文（锚点定位依据）
├── outline.json              # 章节方案
├── sections/NN-slug.md       # 分章草稿
└── evidence_map.json         # 证据映射（写作时同步维护）
```

## status 判定红线
- 一致性 FAIL 时不允许 `success`；manuscript 缺失时不允许 `partial` 以上。
- 任何渲染产物不可得：对应字段写 unavailable + 原因，不伪造文件路径。
- 失败时 result.json 必须包含：失败阶段、已完成的保底产物、人工接管位置。
