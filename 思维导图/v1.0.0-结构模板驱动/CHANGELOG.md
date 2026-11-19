# CHANGELOG

## v1.0.0 (2026-11-19)

- 首个版本：结构模板驱动的思维导图生成。
- 五类材料模板自动识别（论文/综述/实验方案/项目计划/会议纪要，计分制分类）。
- 槽位骨架 + 逐槽位填写清单（slot_checklist.md）。
- 溯源审计：fact quote 逐字核验、数字溯源（含百分比换算）、单元存在性、覆盖率。
- 六格式渲染：md / FreeMind mm / OPML / Mermaid / SVG / HTML，PNG 视环境可用性。
- 运行时骨架：init_result 防超时空手、assemble_result 回填 output_contract、
  validate_output 发布闸门、异常诚实降级。
