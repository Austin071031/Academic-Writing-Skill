# 引用覆盖分类口径

## 角色定义

| role | 含义 | 判定依据 |
|---|---|---|
| foundation | 奠基/机理/综述性工作 | 确立问题、术语或评价口径 |
| key | 关键工作 | 与本文方法最接近或直接支撑空白推导 |
| representative | 代表性工作 | 各路线的典型实现，分组比较对象 |
| recent | 近期进展 | 年份在库内最大年份减 2 以内 |
| context | 背景相关 | 提供背景但非必须转述 |
| other | 其他 | 无法归入以上（rationale 需说明） |

## 覆盖判据（引擎执行）

1. **分类完整性**：library.json 每条记录都有分类且 rationale ≥6 字；
2. **关键覆盖**：role ∈ {foundation, key, representative} 的条目被引用至少一次；
   漏引 → uncovered_key_works + manual_confirmations（请作者确认是否应覆盖）；
3. **近期覆盖**：recent 条目（年份 ≥ 库内最大年份-2）被引比例 ≥1/3，否则提示
   recent_coverage_low 并转人工确认；
4. **双向绑定**：被引条目每条绑定 ≥1 条论断；每条绑定（除 transition）entry_ids ≥1；
   group_overview 类 entry_ids ≥2；
5. **元数据**：被引条目的 authors/title/year/venue 缺失计数报告（不阻断，供修复文献库）。

## 与渲染层的一致性

coverage_audit 在 build_deliverables 之前运行，审计的是 Agent 登记的绑定；
build 之后再由 validate_output 做正文 [n] 与 references.md 的双向一致性复检。
两层合起来保证"引用落在具体论断上、文献表无多余无缺失"。
