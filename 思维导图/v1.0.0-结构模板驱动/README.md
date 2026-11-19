# mindmap-template-studio（结构模板驱动的思维导图 Skill）

从科研材料（论文/综述/实验方案/项目计划/会议纪要）生成**可编辑、可溯源、带预览**的思维导图。
先由脚本识别材料类型并生成结构骨架（槽位模板），Agent 逐槽位填充真实内容，脚本再完成
溯源审计与六格式渲染。

## 特性

- 五类材料模板（论文 IMRaD / 综述 / 实验方案 / 项目计划 / 会议纪要）+ 通用模板
- 逐节点证据溯源：fact 证据 quote 逐字核验、节点数字溯源核验（脚本强制）
- 四种可编辑源（Markdown 大纲 / FreeMind .mm / OPML / Mermaid）+ SVG/PNG/HTML 预览
- 审计报告 + 证据映射 + 变更日志随 result.json 交付，诚实降级机制

## 安装与调用

本目录即 Skill 本体（安装为 `/skills/weekly-skill`）。Agent 加载后按 `SKILL.md` 的
Phase 0-5 执行即可；详见 `docs/USAGE.md`。运行仅依赖 Python3 标准库，PDF 解析依赖
环境中的 pdftotext（缺失时诚实降级）。

## 目录

```
SKILL.md            工作流与契约（Agent 入口）
docs/USAGE.md       完整调用步骤与自查方法
references/         模板库与规则、失败模式
examples/           最小调用示例（示意，非正式案例结果）
evaluation/         自查评分表与合成测试文本
scripts/            全部机械劳动脚本（纯标准库）
```

## 边界

- 不生成材料中不存在的内容；材料缺口显式标 missing。
- 思维导图节点规模建议 ≤60（深度≤6、扇出≤9）；超出请先合并再交付。
- 版本: v1.0.0（见 CHANGELOG.md）。
