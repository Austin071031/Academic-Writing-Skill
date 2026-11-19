# 已知失败模式与规避（failure modes）

| 失败模式 | 表现 | 规避 |
|-|-|-|
| 逐条硬修级联错误 | 修了 30 条错误，复编后还有 40 条 | 只修根因；log_report 的 cascade 标记是为你省请求数的 |
| 超时无产出 | 预算耗尽，/app/output 为空 | Phase 0 必须最先跑 init_result.py；每阶段落盘中间结果 |
| 整文件重写 | 一次响应重写整个 main.tex，token 超限且引入新错 | 行号定位的精确替换；单次响应改动 ≤5 处 |
| 删内容凑编译 | 注释掉报错段落/图引用使编译通过 | 内容删除必须有任务依据并记 change_log+uncertainty；占位用 TODO 文件 |
| 伪收敛 | 只看 PDF 产出就宣称成功 | success 必须同时满足末轮 0 错误；converged 由 needs_rerun 判定，二者分开报告 |
| 静默替代模板 | .cls 缺失直接换 article 且不说明 | 记 uncertainty（版式不保真）+ change_log（替代理由） |
| 编造 bib 字段 | 补条目时填了查不到的 DOI/页码 | 字段以材料为唯一来源；查不到留空 |
| 引擎误判 | 中文稿用 pdflatex 反复修 Unicode 错误 | inspection/tex_build 已自动识别 CJK→xelatex；相信根因假设 |
| 修改 /input | 直接改输入材料 | 只改 /app/work/project（inspect_case 已暂存副本） |
| overfull 放任 | 编译通过但行超出版心 | Phase 4 核对 log_report.overfull_hbox_gt20pt，超宽表格按 P5 思路处理 |
| bib 工具未跑 | 参考文献为空却不知原因 | build_report.passes 检查 bib 轮；必要时 --bib bibtex/biber 显式指定 |
| 占位符遗留 | TODO/?? 留在交付稿中 | Phase 4 source_check.placeholders 必须为 0 或逐条登记 |
