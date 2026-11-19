# 论证链判据（chain_audit 规则说明，可复核）

## 1. 论断抽取

提示词正则（`scanutil.CLAIM_CUES`）：表明/证明/说明/显示/可见/意味着/导致/使得/因此/显著优于/大幅/shows that/demonstrate/indicate/therefore…。命中句即论断候选，并按线索词分类（一句可多类）：

| 论断类型 | 线索 |
|-|-|
| 比较论断 | 优于/超过/高于/显著（提高｜提升｜降低｜改善）/higher than/better than/outperform |
| 因果论断 | `CAUSAL_CUES`：导致/使得/提高了/降低了/驱动/造成/cause/lead to/improve/reduce… |
| 概括论断 | 表明/说明/可见/意味着/indicate/suggest/shows that/reveal |
| 绝对论断 | `ABSOLUTE_CUES`：所有/任何/完全/必然/总是/all/never/completely… |

参考文献与致谢章节跳过（`SKIP_ROLES`）。

## 2. 论据锚点

每句、每段各记录锚点类型集合：

- `cite`：`EVIDENCE_CITES` —— [n] 编号、（作者， 年份）、(Author, 2020)、`\cite{…}`；
- `figtab_xref`：`EVIDENCE_FIGTAB` —— 图n/表n/Fig./Table/公式/附录、`\ref{}`、第n章/Section n（章节交叉引用并入此类）；
- `number`：`EVIDENCE_NUMBER` —— 带单位数字（87.3%、4200 mAh/g、200 MPa…）。

## 3. 论断—论据支撑分档

- **strong**：论断句本身或所在段有任一锚点；
- **weak**：句/段无锚点，但相邻段（±1，按全文段落序）有锚点——论据存在但未指回，需补交叉引用；
- **none**：窗口内无任何锚点 → 「论证链断裂」finding（high，op=narrow/add）。

窗口取"句+段+相邻段"的依据：学术写作中论据通常与论断同段出现，跨段引用必须显式指回；全部锚点明细写入 chain_audit.json 供逐条复核。

## 4. 逻辑跳跃

论断句内容词集合（中文二字组+英文实词，`scanutil.terms`）在其前 3 段的并集中覆盖率过低：新词数 ≥4 且新词比例 ≥0.6（`TH.jump_new_ratio`），且句/段无论据锚点 → 「逻辑跳跃」（medium，op=add_transition）。前文不足 2 段时不判定（引言首次提出概念属正常）。

## 5. 循环论证近似判定

两条论断句（不同段落）的字符 3-gram 集合 Jaccard ≥0.7（`TH.circ_jaccard`），**且两处都无锚点** → 「疑似循环论证」（medium，confidence=0.55≤0.6，依据中注明"近似判定，需人工确认"）。有任一处带锚点则不报——锚点的存在说明至少一端指向了外部证据。

## 6. 论据强度匹配

因果论断或绝对论断的论据必须强于相关性观察：

- 所在段落无 `DESIGN_CUES`（对照组/控制变量/随机/消融/ablation/baseline/交叉验证）；
- 且段落只含 `CORRELATION_CUES`（相关/关联/正相关/correlated…），**或**仅有单点数据（段落恰 1 处带单位数字、无其他锚点类型）；

→ 「论据强度不足」（high，op=qualify：降级为相关性表述或补对照/消融）。

## 7. 比较无对象

含显性比较词（优于/超过/高于/higher than/better than…）的论断句中，同时满足：无 [n] 引用、无拉丁字母专名（`[A-Z][A-Za-z0-9]{2,}`，如 BERT/LiFePO4）、无"基线/baseline" → 「比较论断缺少比较对象或对象无出处」（medium，op=add）。单字母符号（如"Y 工艺"）不计入专名。

## 8. 编辑动作约束与总量

每个 finding 的动作 op ∈ {move, merge, split, narrow, qualify, add, add_transition, add_limitation, reorder}；instruction 必须可执行（"补表X交叉引用""降级为'与…相关'"），不允许"建议重写本节"。findings 总量 ≤15 条（断裂≤8、跳跃≤4、循环≤4、强度≤5、比较≤4）。
