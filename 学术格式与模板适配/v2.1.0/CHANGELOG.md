# CHANGELOG

## v2.1.0（2026-11-25）—— 实测规格接通（基于 v2.0.0 增量，单方向）

改了啥（唯一主线：模板实测样式 → spec 规格组映射）：

- `extract_spec.py`：新增 `project_measured_styles`，将 measure_template 实测的
  正文/标题/题注/参考文献样式值映射进 body/headings/captions/references
  （仅补缺失键；任务文本仍优先，conflicts 登记机制不变）
- `compliance_check.py`：正文 run 抽查限定正文段落（标题/题注/参考文献/目录 run 不计入，
  消除映射激活后的误报 WARN）

没动啥：输出契约键名/结构、九阶段流水线、样式绑定与保真/合规/渲染逻辑、R1–R10 守恒规则。

回归：p1 compliance 12 PASS/3 SKIP → 23 PASS/0 WARN/2 SKIP，fidelity PASS，
契约键与填充 3/3 逐一同父辈；p2 success；p3 诚实 failed。

## v2.0.0（2026-11-23）—— 契约层加固（基于 v1.0.1 增量）

改了啥（唯一主线：弃权型缺口修复，方向不变）：

- `run_pipeline.py`：顶层崩栈 guard + 初始化即写应急 result.json（§4-4）；
  材料/模板兜底扫描补 case.json 所在目录；direction.json 读取并写入 uncertainty.notes
- `render_preview.py`：pdftotext 单次调用 form-feed 分页（预算守卫）；soffice 独立 UserInstallation
- 新增 `direction.json`（contract-hardening / baseline v1.0.1）

没动啥：

- 输出契约：result.json 顶层键、uncertainty 子键、output_contract_filled 填充逻辑——逐一同基线
- 全部 10 个守恒规则（R1–R10，见 _iteration/00_skeleton_diff.md）与 15 个白名单资产
- 流水线九阶段、样式绑定逻辑、保真/合规核验逻辑、渲染产物形态

回归：p1 正常 case 9 阶段状态 / compliance 21 PASS / fidelity PASS 三项与基线完全一致；
p2 劣化 case 由 failed 修复为 success；p3 空输入行为一致（诚实 failed）；p4 崩栈模拟合法产物落盘。

## v1.0.1（2026-11-19）

- build_result.py：output_contract 字段语义映射修复。

## v1.0.0（2026-11-19）

- 首个提交版本：九阶段流水线、纯标准库 OOXML 引擎、双核验 + 导出核验证据链。
