# 关系标注规则（v1.0.2）

## 七类关系的判定

| relation | 判定线索（材料语言） | 反例（不该连） |
|-|-|-|
| causes 导致 | "导致/使得/因此/源于/归因于" | 仅先后出现 |
| depends_on 依赖 | "前提是/依赖于/需要先有" | 仅是同主题 |
| precedes 先于 | 明确时间序、步骤编号 | 并列步骤 |
| contrasts 对比 | "相比/而/相比之下/优于" | 无比较对象的罗列 |
| conflicts 冲突 | 结论互斥、数字矛盾 | 表述不同但数值一致 |
| supports 支持 | "表明/证实/佐证/据此" | 证据与结论主题无关 |
| cites 引用/出自 | 明确引用、出自某文献线索 | 笼统"有研究" |

## 方向规则

- 有向：causes（因→果）、depends_on（依赖方→被依赖方）、precedes（先→后）、
  supports（证据→结论）、cites（引用方→来源）。
- 无向：contrasts、conflicts。
- 同一对节点出现双向有向边 = 必有一错（引擎判 critical）。

## 证据规则

- 边的 evidence 指向**支撑这个关系本身**的单元（而非仅支撑端点的单元）。
- 找不到关系级证据的边：删除，或 note 写"推断"且两端标 uncertain。
- 数字冲突候选必须由人（Agent）核实：同数值不同写法（500℃ vs 五百摄氏度）不算冲突。

## 密度参考

- 论文论证链：结果→结论的 supports 边应有；引言问题→结果的呼应可用 supports/cites。
- 实验方案：步骤链 precedes、判定标准 depends_on 变量设计。
- 项目计划：任务 depends_on、里程碑 precedes。
- 会议纪要：分歧观点 conflicts、待办 depends_on 议题。
- 经验下限：边数 ≥ 节点数 / 8；低于此值引擎会在 refine 层提示。
