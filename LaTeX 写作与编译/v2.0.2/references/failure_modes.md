# 已知失败模式与规避（模板与复现方向）

| 失败模式 | 表现 | 规避 |
|-|-|-|
| 整段复制模板导言区 | 迁入一堆用不到的宏包，引入新冲突 | P5 按需补载；每个新增宏包记 change_log 用途 |
| 编造元数据 | 模板要 \email 材料没有就编一个 | TODO 占位 + manual_confirmations |
| dummy 内容残留 | 模板示例的假摘要/假图留在稿中 | 迁移后全文搜模板示例特征文本，删除并记 change_log |
| geometry 覆盖模板 | 手改页边距破坏期刊版式 | 版式是模板类职责；除非任务要求否则不动 |
| .cls 缺失硬迁 | 没有类文件就换 documentclass，编译必炸 | 先确认类文件在材料中；没有则可用类兜底 + uncertainty |
| 版本号编造 | BUILD_MANIFEST 写"TeX Live 2024"但没查 | 版本只来自 --version 与日志；取不到写 unknown |
| 命令记录不全 | 清单只有 "pdflatex main" 没有 bib 轮 | manifest 直接取 build_report.commands，含全部轮次 |
| 双栏跨栏错误 | 宽表在 IEEEtran 双栏溢出 | 用 table*/figure* 跨栏环境；目视 PDF 确认 |
| 引擎错配迁移 | pdflatex 模板硬套中文稿 | xelatex+ctex 兼容方案，记 uncertainty |
| 未编译验证就交付 | 迁移完没复编 | Phase 3 是硬闸门：success+converged 或逐项说明 |
