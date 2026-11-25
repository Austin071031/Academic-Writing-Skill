# CHANGELOG

## v2.1.1（2026-11-25）—— 行距直改清除（基于 v2.0.0 增量，单方向）

改了啥（唯一主线：正文段落行距直改清除）：

- `adapt_docx.py` restyle_body：正文段落 `w:spacing` 的 `w:line`/`w:lineRule`
  直改属性一律清除（段前段后保留；带 numPr/分节符/含图或公式段落跳过），
  使样式绑定的行距真实渲染；每处清除逐条登记 changelog

没动啥：输出契约键名/结构、其余八阶段、文本内容零改动（fidelity 不受影响）。

回归：p1 清除 5 处 line=240 直改、适配后残留 w:line=0；compliance 与 fidelity
与父辈逐项持平；p2 success；p3 诚实 failed。

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
