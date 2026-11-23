# §2.4 评测契约（判死依据）

出处：Runtime contract（表 2 同页）+ 基线 v1.0.1 代码实读。§0-8 = 否 → 键名/结构一律不改。

| 项 | 契约 | 出处 |
|-|-|-|
| Skill 安装路径 | `/skills/weekly-skill` | "installs the actual Skill under /skills/weekly-skill" |
| 输入 | `/input/case.json` + `/input/task.md`；PDF 无预抽取层 | Runtime contract |
| 工作区 | `/app/work` | 同上 |
| 交付目录 | `/app/output`；可编辑源文件 + result.json | 同上 |
| result.json | 含 `case_id` + case 原 `output_contract` 全部字段；诚实 status/sources/uncertainty/change records | 同上 |
| 预览 | Office 产物须真实渲染 PDF/PNG | "real rendered PDF/PNG previews" |
| 预算 | 64 模型请求 / 900 秒 / 16384 token 每响应 | Runtime contract |
| 资源限制 | ≤50 个 UTF-8 文本文件、单个 ≤500KB、总 ≤2MB、无符号链接 | Runtime contract |
| 降级 | partial 须写明限制；不伪造软件状态/数据 | Runtime contract |

基线 v1.0.1 自测暴露的**弃权型风险**（契约层，真跑证据见 04_baseline_diagnosis.md）：

- C1 `run_pipeline.py` 顶层崩栈（导入失败/路径错）时无任何 result.json 落盘 → 违 §4-4
- C2 result.json 仅在末阶段生成，中断即无合法产物 → 违 "Save honest partial deliverables early"
- C3 `s_convert` 兜底扫描目录未含 case.json 所在目录（非标准挂载时找不到材料，代理 case p2 实测复现）
- C4 `toc_fill` 逐页 pdftotext（页数×1 进程），长文档压 900s 预算风险；单次 timeout=60s
- C5 soffice 未指定 UserInstallation，HOME 只读/并发时 LibreOffice 可能起不来
- C6 无 direction.json（跨题资产 L4 未用，§4-11）
