# 失败模式：基础 Agent（无本 Skill）在文献去重上的典型错误

以下均为真实对照实验中基础 Agent 的常见失败，本 Skill 以引擎信号 + 硬性保护 +
强制留痕逐项封堵。

## FM1 把同名不同文合并（最严重）

**表现**：两条第一作者相同、同年但主题不同的文献被合并成一条。
**后果**：参考文献表凭空少一条真实文献，引用了 A 的句子被指向 B，事实错误。
**本 Skill 封堵**：protected 档（同语种同作者同年 title_sim<0.60，或两个不同 DOI）
禁止并入候选组；apply 对违反保护对的裁决硬拒绝并记异常；判据文件反例 #5/#6
明确要求同名同姓不同研究必须 keep_separate。

## FM2 合并后不说明依据

**表现**：只输出合并后的文献表，没有合并了哪些、为什么合并的任何记录。
**后果**：结果不可核验，评审无法区分"正确合并"与"漏条/误删"。
**本 Skill 封堵**：merge_report.md 强制每组输出判据信号表（title_sim/doi_match/
year_diff/author_overlap/venue_sim/type_compatible 实测值）+ 保留字段来源 +
差异说明 + Agent rationale；merge_report.json 机读留痕；缺裁决的组不允许静默
通过（记 keep_separate(undecided) 异常）。

## FM3 丢失 DOI 等关键字段

**表现**：合并预印本与正式版后 DOI 消失；或字段互缺的互补条目合并后缺卷期/缺页码。
**后果**：参考文献表质量低于原始任一导出，违反"保持事实一致"。
**本 Skill 封堵**：字段并集补全（field_reconciliation.md §2），keep 缺失字段必从
drop 补；DOI 冲突（不同 DOI）本身触发保护不得合并；每条字段来源 rid 可审计。

## FM4 预印本信息被正式版完全覆盖

**表现**：合并后 arXiv 号丢失，无法回溯预印本。
**本 Skill 封堵**：drop 的 eprint 强制写入 keep.extra_fields.arxiv_id 并写入差异说明。

## FM5 跨语言对胡乱比较或臆造相似度

**表现**：基础 Agent 对中英文题名"目测相同"直接合并，或相反——把同译版本当成
两篇；还有的对跨语言对编造一个相似度数字。
**本 Skill 封堵**：引擎明确 comparable=false（字符 3-gram 跨语言不可比）并给出
cross_language_hint；是否同译由 Agent 依据 dedup_criteria.md 判据裁决并在
rationale 中写明依据；红线禁止臆造核验结果。

## FM6 期刊版与会议版不分辨正式层级

**表现**：合并期刊↔会议时保留了会议版（信息更少）或混填字段（期刊名配会议页码）。
**本 Skill 封堵**：keep 择优规则正式版优先（期刊>会议>预印本）；冲突字段一律以
keep 为准并把另一方取值写入差异说明，杜绝混填。

## FM7 漏裁决/跳组

**表现**：候选对较多时 Agent 只处理明显的几组，其余无声跳过。
**本 Skill 封堵**：apply 校验每个候选组必须有裁决行；缺失即 keep_separate(undecided)
并记入 exceptions.json，结果 status 可如实降级 partial。

## FM8 合并后编号映射缺失导致正文引用错位

**表现**：文献表合并了但正文编号未跟着变，出现悬空引用。
**本 Skill 封堵**：dedup_mapping.json 输出 drop→keep 的 rid/编号映射并附合并后
顺序 new_order_rids；编号匹配失败时 limits 如实说明，交由v1.0.1 的重排流程处理，
不得静默跳过。
