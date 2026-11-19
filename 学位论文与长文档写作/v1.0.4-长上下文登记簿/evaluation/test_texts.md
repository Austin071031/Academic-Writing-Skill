# 合成测试文本（标注：全部为合成数据，仅用于本地验证，非正式案例）

测试目录：`_test/`（输入 `_test/input/`，本版测试工作区 `_test/work5/`、
产物 `_test/output5/`；不触碰既有 work/ 与 output/）。

## 案例 A（端到端，应全过）

输入：ch1_intro.md（SSE/ASSB 定义句 +「Li6PS5Cl 电导率可达 3.2 mS/cm」结论句）、
ch2_method.md（两步烧结 450°C/520°C、EIS 定义、XRD/SEM）、facts.md（6 条事实，
其中「XRD 杂相峰强度降低约 40%」「SEM 晶界密度明显提高」前文未使用）。

预期与实际（2026-11-19 运行）：
- build：定义 3（SSE/ASSB/EIS）、结论 1（关键数值 3.2 mS/cm）、材料 6 段、
  未用 2 段（XRD/SEM 两条）——✔ 全部符合。
- brief（目标「第3章 结果与讨论」，预算 3000）：含定义/结论/未用材料提醒三类
  内容，截断 0 条——✔。
- 干净稿 overlap：verdict=PASS_WITH_REMINDERS，重复论述 0、重复结论 0、
  未定义缩写 critical 0、悬空图表 0、材料提醒 2（XRD/SEM，真阳性提醒）——✔
  critical 零误报。
- 交付：assemble → validate_output PASS（status=success）→ preview.html 生成——✔。

## 案例 B（故意注入缺陷，应检出）

缺陷稿 `work5/draft_ch3_bad.md` 注入三类缺陷：
1. 重复论述：整句照抄 ch2「样品制备采用两步烧结工艺：第一步 450°C 保温 2 h，
   第二步 520°C 保温 1 h。」→ 检出 repeated_exposition（score 1.0）✔
   （另有结论句与 ch1 句子 4-gram 重叠 0.679 一并检出）。
2. 重复结论：「测试结果表明，Li6PS5Cl 的电导率可达 3.2 mS/cm。」→ 检出
   repeated_conclusions（同主语 Li6PS5Cl + 共享关键数值 3.2 mS/cm）✔
3. 未定义缩写：「HRTEM 观察显示…」→ 检出 undefined_abbrs critical
   （前文无定义且本稿未定义）✔
4. 附加：引用无 caption 的「图3-1」→ 检出 dangling_figtab ✔
verdict=HAS_ISSUES，critical_total=5。

## 反例（零误报要求）

干净稿 `work5/draft_ch3_clean.md`：术语全部有出处（SSE/ASSB/EIS 沿用 dossier
定义；XRD/SEM 在稿内首现处补全称定义）；结论句为提升幅度的新论断（引用旧数值
3.2 mS/cm 作对比，主语不同）→ 重复论述 0、重复结论 0、critical 未定义缩写 0、
悬空图表 0——critical 零误报 ✔（材料提醒 2 条为设计内真阳性，不计误报）。

已知边界验证：「Li6PS5Cl」「B7」不被误判为未定义缩写（全大写 ≥2 字母豁免规则）✔。
