# 边界判据（boundary_audit 规则说明，可复核）

## 1. 数字溯源（三层匹配 + 容差）

- 目标句：摘要/结论全部句 + 讨论章末段句；源章：方法/实验/结果/讨论。
- 数字 token 由 `scanutil.NUM_IN_CONCL` 抽取（含 %/％/倍/×）。**剔除**：年份（19xx/20xx 无单位）、编号（图1/表2/[3]/式4/第3节，按前文语境判定）。
- 三层匹配（按序裁决，逐条 verdict 写入 boundary_audit.json）：
  1. **ok**：token 去空白后在源章逐字命中；
  2. **format_diff**：数值相等但格式不同（含 %×100 换算，如 0.873 vs 87.3%）→ low 级"需人工确认"，建议统一表述格式；
  3. **approx**：与同单位源数字最小相对差 ≤5%（`APPROX_TOL`）**且满足舍入一致性**（一方按另一方小数位四舍五入后相等，如 65.2→65）→ medium「疑似四舍五入/笔误」；
  4. **stray**：以上皆不满足 → high「无源数字」。相对差在容差内但无法由舍入得到（如 87.3→91.0）仍判 stray——容差只豁免舍入，不豁免篡改。
- 阈值依据：5% 足以覆盖常规舍入与抄录抖动；舍入一致性约束防止"数值接近但语义不同"被豁免。所有相对差与匹配源写入溯源表供复核。

## 2. 摘要-结论一致性

- 摘要句 × 结论句两两比对：内容词 Jaccard ≥0.4（`ECHO_JACCARD`）视为同语境句对。
- 同语境句对的数字集合（含 %×100 等值换算）不一致 → high「摘要与结论同语境数字不一致」，定位在结论句，证据列出两侧数字与差集。
- 依据：摘要与结论必须逐字同源；任何舍入须在两处同步。

## 3. 因果表述三档

- 结论/摘要中含 `CAUSAL_CUES`（导致/提升/improve…）的句子逐句裁决：
  - **supported**：方法/实验章命中 `DESIGN_CUES`（对照/随机/消融/baseline…）→ 不报；
  - **overreach**：无设计词但正文命中 `CORRELATION_CUES`（相关/关联/correlation）→ high，动作 narrow：降级为关联表述；
  - **unverifiable**：两者都无 → medium「需人工确认」，动作 qualify。
- 已知盲区：设计描述非常规措辞时 supported 会漏判为 unverifiable（置信度已下调）。

## 4. 绝对化表述

- 目标句命中 `ABSOLUTE_CUES`（所有/任何/完全/总是/never…）→ medium，动作 qualify：限定适用范围。
- 若同句命中推广范围词（见 §5），绝对化不再重复报（由推广超界条目覆盖）。

## 5. 推广范围比对

- 结论/摘要出现范围词（所有体系/任何体系/通用/普适/广泛适用/universal/generally applicable…）时：
  - 枚举方法/实验章出现的具体体系/材料/数据集线索（`ENTITY_RE`：体系/材料/电池/负极/正极/数据集/模型/催化剂/合金 的前置名词，≤8 条）；
  - 范围词无对应枚举支撑 → high「结论推广范围超出实验条件」，动作 qualify：限定为已测条件；
  - 未检出方法/实验章 → 仍报，注明"无法核验"，置信度下调。

## 6. 限制说明充分性

- `LIMITATION_CUES`（局限/不足/未来工作/limitation…）全文命中位置与长度审计，四态：
  - **missing**：零命中 → medium「缺少局限性说明」，动作 add_limitation；
  - **misplaced**：仅命中致谢/附录/参考文献 → medium，动作 move 至讨论末/结论前；
  - **insufficient**：仅一句且无量化边界（句中无数字）→ low，动作 add 补量化边界；
  - **adequate**：其余 → 不报。

## 7. 编辑动作约束

每个 finding 的动作 op ∈ {move, merge, split, narrow, qualify, add, add_transition, add_limitation, reorder}；instruction 必须给出"改成什么数值/限定到什么范围/移到哪"，不允许"建议注意表述"这类不可执行表述。
