# grant-innovation-precision（创新点差异定位 · v2.0.0 快速主通道）

基金申请书写作 Skill，主攻"说得准"：创新点写清与具体已有工作的差别，
不依赖 首次/国际领先/填补空白 一类无法核验的修饰；事实台账 + 证据标记 +
材料外事实机检，交付可直接进入申请书的七要素章节稿与要素对照说明。
v2.0.0 单点改动：**快速主通道**——`sections_scaffold.py` 预生成七节骨架
（含按要素匹配的 FID 候选清单）+ 分阶段请求预算表，工作流 13 步压 8 步，
主通道 ≤40 请求，保证 900 秒预算内完整七节成稿。

- **安装**：本目录即技能根，整体置于 `/skills/weekly-skill` 即可被 Agent 加载；无第三方依赖（Python3 标准库；PDF 解析可选 pdftotext）。
- **快速开始**：按 `SKILL.md` 的 8 步主通道与预算表执行；最小示例见 `examples/minimal_example.md`。
- **边界**：不臆造材料外事实；材料缺失如实降级 partial 并登记 manual_confirmations；详见 SKILL.md"限制"。
- **仓库**：https://github.com/Austin071031/Academic-Writing-Skill/tree/main/基金申请书写作/v2.0.0-快速主通道

## 使用说明

### 输入

| 路径 | 说明 |
|-|-|
| `/input/case.json` | 案例元数据（case_id、output_contract 等） |
| `/input/task.md` | 写作任务要求 |
| `/input/organizer-workorder.json` | 组织方补充约束（可选；存在时优先级最高） |
| `/input/*.{md,txt,tex,docx,pdf}` | 科研材料：原论文、前期成果、指南等（格式不限） |

### 输出（/app/output）

`proposal_draft.md`（清洁章节稿）、`proposal_annotated.md`（留痕版）、
`element_mapping.md`（七要素对照说明）、`report.md`、`preview.html`、`result.json`。
中间产物（/app/work）：`inspection.json`、`materials.json`、`materials_digest.md`、
`fact_ledger.json`、`fact_ledger.md`、`innovation_seed.json`、`sections/`（骨架→成稿）、
`draft.json`、`source_audit.json`、`element_map.json`、`findings.json` 等。

### 调用步骤（8 步主通道）

1. `init_result.py` —— result.json 兜底骨架（幂等）。
2. `inspect_case.py --work W` —— 案例侦察；Agent 读 inspection.json。
3. `parse_materials.py --work W` —— 段落稳定 ID + role_guess。
4. `fact_ledger.py --work W` —— 事实台账 FID。
5. `sections_scaffold.py --work W` + `innovation_engine.py seed --work W` ——
   七节骨架（含 FID 候选清单）+ 创新点对比锚点机选。
6. **Agent 写作**：读 materials_digest.md + innovation_seed.json + 骨架候选清单，
   直接在骨架上一轮写完七节（强制〔F〕〔拟〕〔确认〕标记；厚度按骨架字数目标：
   立项依据≥600、技术路线≥450、研究基础≥400、其余≥250）。
7. `draft_builder.py` + `source_audit.py` + `elements_check.py --out O` +
   `innovation_engine.py audit` —— 组装 + 四审计一轮；Agent 当轮处置全部
   high 级发现并重跑本步清零；第二轮复核仅剩余预算 >15 才做。
8. `report_builder.py` + `assemble_result.py` + `validate_output.py`（必须 PASS）
   + `render_previews.py`。

### 证据标记语法

| 标记 | 含义 | 机检行为 |
|-|-|-|
| `〔F0001〕` | 该句事实来自台账条目 F0001 | FID 必须存在；数字/引用与台账值比对；创新点节中指向 citation/pub_mention 类的标记兼作对比锚点 |
| `〔拟〕` | 拟开展/预期内容 | 段内数字不做材料外审计；体貌须为拟态 |
| `〔确认〕` | 材料不足/冲突，需人工确认 | 登记 manual_confirmations 后放行 |

### 创新点节判定规则速查（innovation_engine.py audit）

| kind | severity | 触发条件 | 处置 |
|-|-|-|-|
| missing_section | high | 草稿无 创新点/特色与创新/创新与特色 节 | 补写该节 |
| banned_modifier | high | 命中 首次/国际领先/填补空白/国际先进/国内首创/世界领先/原创性/重大突破/国际一流/领跑 | 删除命中词，改为差异表述 + 〔F〕锚点 |
| no_baseline_anchor | medium | 条目无 citation/pub_mention 类〔F〕且无 已有工作/现有研究/现有方法/文献/传统方法/目前主流 | 从 innovation_seed.json 选锚点补对比对象 |
| no_difference_statement | medium | 条目无 不同于/区别于/相比/优于/而非/改为/突破了/克服了/解决了/避免了 | 补差异句 |
| three_dim_incomplete | medium | 全节缺 新在哪里/为什么难/凭什么做得成 任一维（「首次提出」不算新维度证据） | 按 msg 指明的缺维补写 |

### 自查方法

- `validate_output.py` 必须 PASS（8 项形态检查）。
- `report.md` 的 findings 分级统计中 high 必须为 0（或全部"已驳回"并附理由）。
- `element_mapping.md` 七要素状态应为 ok（thin/missing 需在 report 说明原因）。
- 抽查 `proposal_annotated.md` 创新点节每条：能否指出对比的已有工作及其〔F〕锚点、
  差异表述词、以及该条归属的三维覆盖。

### 失败处理

任一脚本失败：读 stderr → 修复后重跑（全部幂等；scaffold 不覆盖含〔F〕的成稿）→
无法修复则保留已有产物，`assemble_result.py --status partial` 交付并在 report.md 写明限制。
