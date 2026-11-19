# 典型失败模式（failure_modes.md）

按出现频率排序；每条给出症状、根因与处置。引擎已内置防线的注明「引擎防线」。

## F1 引用了不存在的文献（越界 numeric / 未匹配 key）
- 症状：bind 报 unbound，`numeric [5] 越界（文献表仅 2 条）`。
- 根因：稿件编号与文献表脱节；或文献库不完整；或 AI 生成的幻觉引用。
- 处置：Phase 3 裁决——能在文献库找到对应文献则改标记，找不到则删引用并弱化论断；
  **禁止**为消除 unbound 编造条目或把编号改小冒充命中（红线 1）。

## F2 引用了文献但结论被改写（overstated / negation_flip）
- 症状：verify-c 报 `overstated+negation_flip`，如论文「完全解决界面问题」vs 材料「仍是挑战」。
- 根因：写作时语气升级、把或然当必然、把"缓解"写成"解决"。
- 处置：对照 material_sentence 降回同级语气；误报（材料原文同为强表述）写
  manual_confirmations。引擎不自动改写（红线 2）。

## F3 论断数值在材料中不存在（unverified）
- 症状：verify-b 报 `数值 9.9 unverified`。
- 根因：笔误、单位换算错误、或臆造数据。
- 处置：改为材料值（change_log 记 before/after）或删除；保留则句尾标「（数据待核）」
  并登记 uncertainty。禁止静默保留。

## F4 数值遮蔽误判（图3-1、章节号、年份、化学式被当成事实数值）
- 症状：verify-b 把「图 3-1」「Li6PS5Cl」中的数字报 unverified。
- 引擎防线：遮蔽规则（citation_rules §2）：图表/章节/年份/引用标记/URL/紧邻字母的数字。
- 处置：仍有漏网 → manual_confirmations 说明该数值性质；不手改引擎输出。

## F5 百分比/单位换算被误报 unverified
- 症状：论文「提升 40%」材料「0.4」或「由 3.2 至 5.8」。
- 引擎防线：derived 判据含 ×/÷100 百分比换算与两值四则（±1%）。
- 处置：真实换算应判 derived；若四则组合 >2 值（如三值连乘）引擎不报，Agent 在
  evidence_map 手工补登 derived 及算式。

## F6 语气误报：材料句含「可能」但修饰的是另一分句
- 症状：论文平实转述「界面仍是挑战」被报 overstated，因材料句尾带「可能缓解」。
- 引擎防线：升格判定要求 claim ≥ L4（证明/彻底解决级）；L3「表明」不报。
- 处置：仍误报 → manual_confirmations 记录「或然词修饰对象不同」。

## F7 自有实验数据被误报漏引
- 症状：方法章「450°C 保温 2 h」无引用被报 missing_citation。
- 引擎防线：数值全部可溯源到材料（facts/笔记）的段落不报漏引。
- 处置：若材料未收该参数 → 报 missing_citation 是正确提示，Agent 裁决为
  「本实验参数，无需引用」并写 manual_confirmations。

## F8 author_year 绑定失败：「Zhang 等, 2023」「(Zhang et al., 2023)」
- 症状：bind 报 author_year 未匹配，但条目明显存在。
- 引擎防线：先剥离「等/et al」再取姓；中文含复姓表；年份忽略 a/b 后缀。
- 处置：仍不中（如第一作者其实不是该姓、年份不同）→ 按 unbound 如实报告。

## F9 样式混杂：numeric 与 author_year 同稿混用
- 症状：render_refs 的 audit 报 `style_consistent=false`。
- 处置：按任务要求统一为目标样式；编号重排只走 cite_engine renumber / trace_engine
  render_refs，不手改（红线 3）。

## F10 annotated_draft 残留越界标记导致 validate FAIL
- 症状：output 同时含 annotated_draft.md（保留原 [5]）与 references.md（仅 [1][2]），
  validate 报「正文引用了文献表中不存在的编号」。
- 根因：annotated_draft 是给作者的审阅版，刻意不改正文。
- 处置：交付修订稿（revised_*.md，已处置 [5]）为主产物；annotated_draft 若必须同交，
  则 status=partial 并在 uncertainty 说明「[5] 待作者裁决」；或由 Agent 在修订稿中
  处置完毕后将 references.md 与修订稿同交（annotated 仅留 work/）。

## F11 文献库为空或全部解析失败
- 症状：library.json count=0，bind 全 unbound。
- 处置：如实报告「文献库不可用，无法绑定」；仅交付术语表与审查报告骨架，
  status=partial；绝不编造条目。

## F12 静默降级：核验未做却声称"全部可溯源"
- 症状：result.json status=success 但 evidence_map 为空或 verify 未跑。
- 引擎防线：validate_output 对 status=success 且 evidence_map 为空直接 FAIL。
- 处置：补跑 verify 并填 evidence_map，或如实降级 partial（红线 2）。
