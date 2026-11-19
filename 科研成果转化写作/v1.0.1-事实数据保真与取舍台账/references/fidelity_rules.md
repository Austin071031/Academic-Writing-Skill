# 事实保真判据表（与 fidelity_engine.py 常量一致）

## 等价等级（正向：源文事实 → 改写稿）

| 判定 | 定义 | 容差/示例 | 报告 |
|-|-|-|-|
| verbatim | 数值严格相等，单位原样或等价写法 | `EPS_EXACT=1e-9`；5 nm ≡ 5纳米 ≡ 5 nm；85.3% ≡ 85.3％ ≡ 85.3 % | 标记 verbatim |
| derived·百分比↔小数 | 百分数写成小数或反之 | 85.3% = 0.853；62.1% = 0.621 | 写换算式 `85.3% = 0.853` |
| derived·四舍五入 | 少写小数位或取整 | `REL_TOL=0.01`（±1%）；73.4% ≈ 73% | 写 `73.4% ≈ 73%（四舍五入/±1% 容差）` |
| derived·单位换算 | 同量纲不同量级 | 5 nm = 0.005 μm；85 Ω = 0.085 kΩ；换算表：nm/μm/mm/cm/km、Ω/kΩ/MΩ、mV/V/kV、mg/g/kg、μL/mL/L（含中文别名纳米/微米/欧姆/千欧/毫伏/克/千克/毫升/升…） | 写 `5 nm = 0.005 μm（单位换算）` |
| derived·端点重算 | 百分比事实可由同段"由 A U 降至 B U"重算 | 73.4% = (320-85)/320；要求改写稿同时保留 A 与 B | 写 `73.4% = (320-85)/320（由端点重算）` |
| missing | 源文有、改写稿没有 | severity：该段（pid）含 compare/conclusion 事实 → **critical**；否则 warn | 列出 pid 与 raw |
| altered | 同量纲但不同值（疑似篡改） | 源文 85.3% 改写写成 89%；severity 同 missing 规则 | 同时报 unverified（89% 源外） |

## 反向判定（改写稿 → 源文）

| 判定 | 定义 | severity |
|-|-|-|
| ok | token 可 verbatim/derived 匹配任一源文事实，或裸数出现在源文原文中 | — |
| unverified | 改写稿中"数值+单位/百分比"在源文无对应（疑似源外新事实） | **critical**，必须删除或由作者确认 |

## 图表引用

- 改写稿引用的图/表编号必须存在于源文 figure_ref/table_ref：否则 critical（figure_ref_unknown / table_ref_unknown）。
- 源文被引图表在改写稿中消失：warn（figure_ref_dropped / table_ref_dropped），须在取舍台账说明。

## 遮蔽规则（防误报，不作数据事实）

- 年份：19xx/20xx 四位数（如 2023）。
- 紧贴字母的数字：化学式/材料式（LiNi0.8、Li6PS5Cl）、倍率/牌号（0.5C、NCM811）、版本号（v2.1）、章节号（第 3 节）。
- 遮蔽是启发式：被遮蔽项若构成实质性新事实（如改写新引入的年份声称），仍须人工确认并记入 manual_confirmations。

## 取舍台账（ledger）判据

| 校验 | 规则 |
|-|-|
| 覆盖性 | 每个含 number/percent/sample/compare/conclusion 事实的源文段落必须有决定，否则 missing_decision（列出缺失 pid） |
| 动作合法 | action ∈ {保留, 压缩, 删除}，否则 invalid_action |
| 理由充分 | reason 必填；删除须 ≥`MIN_REASON_CHARS=4` 字且不得为敷衍词（无/无理由/不详/略…），否则 unreasoned_action |
| 文件缺失/格式错误 | decisions_file_missing 或 jsonl_parse_error，均列出缺失/出错 pid |
| 丢弃清单 | 删除段落自动列出被丢弃事实清单（type:raw） |
