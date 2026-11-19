# mindmap-pipeline-engine（一键管线式思维导图 Skill）

Agent 只写一份 `mindmap.json`，一条 `engine.py run` 命令自动完成
**结构修复 → 溯源审计 → 六格式渲染 → 结果汇总 → 发布闸门**。
相对基础 Agent 手工排版核对，本 Skill 把交付动作压缩到一次调用，且所有自动修复记入
change_log 可复核。

## 特性

- 一键管线：`engine.py run` = fix + audit + render + assemble + validate
- 结构自动修复：扇出 >7 按 kind/材料来源自动分组；深度 >6 自动上提（全程留痕）
- 溯源审计：fact quote 逐字核验、数字溯源（含百分比换算）、单元存在性、覆盖率
- 审计存在 critical 时自动如实降级 partial，防止"带病交付"
- 六格式交付：md / FreeMind mm / OPML / Mermaid / SVG / HTML（+PNG 视环境）

## 使用

见 `SKILL.md`（Agent 入口）与 `docs/USAGE.md`。仅依赖 Python3 标准库。

## 边界

- Agent 负责逻辑分类与证据挂载；引擎只修结构，不替你判断内容对错。
- 材料缺口显式标 missing/uncertain，不编造。
- 版本: v1.0.1。
