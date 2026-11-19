# CHANGELOG

## v1.0.2（2026-11-19）
- 首版：论断强度阶梯（L0 绝对化/L1 确立/L2 初步/L3 展望）+ 因果/相关标记集 + 否定极性检测。
- `claim_engine.py extract`：源文论断句抽取（claim_id/pid/level/causality/markers/negated）。
- `claim_engine.py check`：经 alignment 段落映射 + 句级 2-gram Dice 匹配，逐条判定 kept/downgraded/upgraded/absolute_upgrade/causality_upgrade/negation_flip/missing，反向检测 new_claim；critical exit=2，报告含 rpid 定位与同级回退建议。
- 保守定级规则：「初步」与 L1 动词同句按 L2 定级；改写句无强度标记按 L1 断言处理。
- 共享核心：case 解析、源文结构化、源文-改写逐段对齐、骨架 result.json、validate 发布闸门。
- 合成测试：正例 PASS（5 条 kept）；反例 7 个 critical 覆盖升格/绝对化/相关写成因果/否定翻转/源外新结论。
