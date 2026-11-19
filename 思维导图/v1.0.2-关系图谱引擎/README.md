# concept-relation-mapper（关系图谱式思维导图 Skill）

从科研材料生成"层级树 + 类型化关系图"双层思维导图，主打**连得对**：
每条关系边限定七类词表（causes/depends_on/contrasts/precedes/cites/supports/conflicts）
且必须挂证据；引擎机检方向冲突、数字矛盾候选与缺失关系建议，并渲染独立的关系图
（relations.mmd / relations.svg / relations.md）。

## 特性

- 七类关系词表 + 方向语义约束（双向有向冲突判 critical）
- 数字冲突候选检出（同主体不同数字）与缺失关系建议（共享证据但无边）
- 双层审计：节点证据层（quote 逐字/数字溯源）+ 关系层
- 交付：层级导图六格式 + 关系图三格式 + evidence_map + audit_report + result.json

## 使用

见 `SKILL.md` 与 `docs/USAGE.md`。仅依赖 Python3 标准库。

## 边界

- 无关系信息的纯罗列材料会退化为层级导图（边数少的提示会出现在审计中）。
- 推断边必须 note 标"推断"且端点 uncertain；禁止无依据连边。
- 版本: v1.0.2。
