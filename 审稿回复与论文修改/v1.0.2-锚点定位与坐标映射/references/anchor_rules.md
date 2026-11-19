# 锚点定位规则（anchor_rules）

本文件是"修改定位"方向的核心规范：双坐标怎么记、回复信引文怎么写、行号怎么映射、失效锚点怎么认定与处置。anchor_engine.py 把这些规则实现为强制检查。

## 1. 双坐标规范

每处已应用的编辑（edit_report 中 status=applied 的 op）必须同时携带两侧坐标：

**基线侧（before）**

| 字段 | 含义 | 取值来源 |
|-|-|-|
| section | 章节标题 | structure.json 段所属章节；insert_* 操作落到其锚段章节 |
| para_id | 段 ID（P###） | edit_report 的 anchor_para（优先）或 para_id |
| line | 基线行号（1 起） | 在基线文件逐行搜索 anchor_quote：精确 → 归一化 → fuzzy（相似度≥0.60）逐级降级 |

基线行号找不到时，记 `锚点已由改写消除`，附 edit_report 的 method/ratio 与基线最佳相似度；该标注是**事实陈述而非失败**，但须列入 uncertainty。

**修订侧（after）**

| 字段 | 含义 |
|-|-|
| line | 修订稿行号（1 起），来自 edit_report.revised_line（new_text 前 30 字在修订稿中定位） |
| para_id | 所在段 ID；新增段为派生 ID（P005a、P005b…） |
| new_text_head30 | 新文本前 30 字摘录，供人眼快速比对 |

**新增段落无基线坐标时的标注法**：insert_after/insert_before/append_section 产生的段落在基线中不存在，基线侧坐标一律落到**锚段**（anchor_para）的章节+行号，并在 location_table.md 的基线坐标列直接显示锚段坐标；回复信中引用新增段落时用新段 ID + 修订稿行号（如"P005a，修订稿行 25"），**禁止虚构基线行号**。

## 2. 引文引用规范（回复信专用）

1. 回复信中引用修订稿文字，**必须**用引号包裹且**逐字**：中文用「」或“”，英文用 " "；同一封信内风格统一。
2. 引文 ≥8 字即进入引擎核验：空白归一化后必须是 revised_manuscript.md 的子串。写引文的方法：从修订稿复制粘贴，不要手打。
3. 引用审稿意见原文（"原意见摘录"）同样受检；引擎允许其在意见原文中命中（视为意见摘录放行），因此摘录也要逐字。
4. 短于 8 字的引文不参与核验，但定位仍应有 E# 或坐标支撑——引文是"可核对"的增强而非替代。
5. 改动了修订稿文字，必须同步改引文；否则复跑引擎必被检出（引文未找到，exit 1）。

## 3. 行号映射方法

1. **不手抄行号**。基线↔修订稿的行号对应由 difflib.SequenceMatcher 行级对齐自动得到：对基行与修订行序列做 opcode 比对，非 equal 的区段即为 change region，记录 `基线行区间 → 修订稿行区间`（1 起闭区间）。
2. op → 区域挂接：以 op 的 revised_line 落入哪个区域的修订行区间为准；无 revised_line（纯删除）时退回基线行区间。
3. 回复信中的"第 N 行"必须是**修订稿**行号，且 N ≤ 修订稿总行数；引擎按修订稿当前行数核验，旧稿行号一律越界报错。
4. 行号以 location_table.md 为唯一权威来源；Agent 写信时从该表抄坐标。

## 4. 坐标引用规范

- 段坐标：`P\d{3}` 或新增段 `P\d{3}[a-z]`（P005a）；必须在 structure.json 段集合或 edit_report 新增段集合内。
- 章节坐标：`SEC\d+`；必须在 structure.json 章节集合内。
- 操作坐标：`E\d+`；必须在 edit_report applied 集合内（failed/不存在的编号即"悬空引用"）。
- 行坐标：`第?\d+行`；范围 1…修订稿总行数。

## 5. 失效锚点定义与处置

| 失效类型 | 判定 | 处置 |
|-|-|-|
| 锚点不唯一 | 同一 quote 在基线出现 >1 次且无法靠 section 消歧 | revision_engine exit=2；加长 quote 或指定 para_id 后重跑，不让引擎猜 |
| 模糊锚点 | edit method 以 fuzzy 开头（相似度 ≥0.75 但非逐字） | 操作照常应用，但单列"⚠ 模糊锚点预警：人工复核定位"；复核结论写 manual_confirmations；连续出现时优先改用精确锚点 |
| 锚点已由改写消除 | anchor_quote 在基线逐行搜索（含归一化/fuzzy≥0.60）仍找不到 | 基线坐标标注消除说明 + method/ratio；修订侧坐标不受影响；列入 uncertainty |
| 悬空 E# | 回复信引用了未 applied 的 op 编号 | anchor_engine exit=1（E引用悬空）；修正编号或先补做编辑 |
| 引文失配 | 引号引文在修订稿与意见原文中都找不到 | anchor_engine exit=1（引文未找到）；逐字重抄 |
| 坐标失配 | P/SEC 不存在或行号越界 | anchor_engine exit=1；以 location_table.md 为准修正 |

**总原则**：定位宁可标注"已消除/待复核"，不可假装精确；任何回复信手改后重跑 anchor_engine。
