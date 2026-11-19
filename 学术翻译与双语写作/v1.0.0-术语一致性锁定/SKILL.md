---
name: translation-terminology-lock
description: 学术翻译技能（主攻“术语一致性·术语稳”）。把整篇外文学术稿件按句段切分后翻译，先从原文机选术语候选（缩写定义、大写复合词、高频名词短语），由 Agent 审定并锁定全篇唯一译名形成术语表，译文句段级落地后由脚本逐句段核对：源句段含术语而译文未用锁定译名、缩写首现未给全称、跨章节译名漂移，全部定位到句段并给出修订指令。适用于英译中/中译英的整篇论文翻译、双语对照稿制作，尤其术语密集的材料/化学/物理/生物医学稿件；不适用于无正文段落的纯数据文件（如实降级）。输入 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 translation_full.md（纯译文）、bilingual.md（双语对照）、glossary.json（锁定术语表）、term_audit.json（术语核对表）、report.md、result.json。
---

# 术语一致性锁定 · 学术翻译 Skill

## 用途与适用条件

对一篇**完整学术稿件**执行句段级翻译，主攻题面“术语稳”：同一术语在摘要、正文、图表题注、附录中保持同一译法，而不是每次出现重新意译。机制：脚本先做术语候选抽取与译后逐句段核对（机械劳动秒级），Agent 只做两件事——**审定锁定术语表**与**翻译句段**。

适用：英译中、中译英整篇翻译与双语对照稿。不适用：纯数据/无正文段落文件（按材料缺口如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件材料；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**翻译按批次写入 translations.jsonl（追加式），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线）、`references/`（术语方法）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造术语译名**：译名只能来自 ①材料内定义 ②学科惯例（在 rationale 写明）③task.md 指定；拿不准的列入 manual_confirmations，不得编造“权威译法”。
2. **不静默跳过句段**：未译句段由脚本以【缺译】标记并计入 uncertainty，禁止从交付物中删除源句段。
3. **数字/引用/公式原样**：segments.json 标注的受保护片段（数字+单位、引用标记、公式、URL/DOI）逐字符保留；术语修订只动术语，不顺手改数。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

# 1) 兜底骨架（防超时空手；幂等）
python3 $S/init_result.py

# 2) 案例侦察：case_id、翻译方向（en2zh/zh2en）、交付形态、材料清单
python3 $S/inspect_case.py --work $W
cat $W/inspection.json        # 重点看 translation_task 与 issues

# 3) 结构解析：章节/段落/句子稳定 ID（SEC1 / P001 / P001-s2）
python3 $S/parse_manuscript.py --work $W

# 4) 句段切分 + 受保护片段预抽取（数字/引用/公式/缩写定义）
python3 $S/segment_builder.py --work $W

# 5) 术语候选机选：缩写定义对、大写复合词、高频名词短语
python3 $S/term_engine.py seed --work $W
cat $W/glossary_seed.json
```

**第 6 步（Agent 核心判断①：审定术语表）**。打开 `work/glossary_seed.json`，逐条审定后另存为 `work/glossary.json`：
- 为每个候选给出 `locked_translation`（全篇唯一译名）并将 `locked` 置 true；`rationale` 写明依据（材料内定义/学科惯例/task.md 指定）。
- 非术语的噪声候选（普通词组）整行删除。
- 同一英文词在不同学科译名不同（如 cell：电池/细胞；deposition：沉积/淀积）：按本稿学科锁定一种，在 `discipline_note` 说明；确需并存译法的填入 `declared_variants`。
- 材料内已有译名定义（如中英对照稿）优先采用材料译名。

**第 7 步（Agent 核心判断②：分批翻译）**。打开 `work/source_for_translation.md`，逐行翻译（格式 `<seg_id>\t<源文> 〔保留: …〕`）：
- 每批 20–40 个句段，追加写入 `work/translations.jsonl`，每行一个 JSON：`{"seg_id":"P001-s1","translation":"译文"}`。
- 含术语的句段必须使用 glossary.json 的锁定译名；〔保留:…〕列出的片段逐字符保留。
- `〔不译·原样保留〕` 行（公式、参考文献条目）不译、不删。
- **预算兜底**：若模型请求已用 40 次仍未译完，立即跳到第 8 步，剩余句段按缺译交付 partial。

```bash
# 8) 组装交付物（纯译文 + 双语对照 + 覆盖率 + 逐句段溯源）
python3 $S/assemble_translation.py --work $W --out $O

# 9) 术语机检：锁定译名逐句段核对 + 缩写首现检查
python3 $S/term_engine.py audit --work $W
cat $W/term_audit.json        # 重点看 violations
```

**第 10 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 segments.json 原文复核 term_audit 每条 violation；确属误报（如该句段术语是引用标题内文字）在 findings.json 将该条 status 改为“已驳回”并写明理由。
2. **补漏报**：通读译文，发现脚本未捕获的术语漂移（同一英文术语的不同中文写法），在 glossary.json 补 `declared_variants` 或追加 finding。
3. **修订**：对成立的违规，把修订后译文**追加**到 translations.jsonl（同 seg_id 后写覆盖先写），然后重跑第 8、9 步确认清零。assemble_translation 会自动把译文差异记入 change_log。

```bash
# 11) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus terminology --skill "translation-terminology-lock v1.0.0"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "translation-terminology-lock v1.0.0" --status success   # 有缺译/未处置异常用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；status≤partial |
| 术语表冲突（Agent 与材料译名不一致） | 以材料为准，写入 manual_confirmations 请作者确认 |
| glossary.json 缺失（Agent 未审定） | 引擎退回 seed 并告警；术语审计置信度下调，uncertainty 标注 |
| 语向与材料不符（task 说英译中但材料是中文） | 以材料语言为准并在 uncertainty 说明 |
| 超长稿件（待译句段 >600） | 按第 7 步分批；预算过半优先摘要/正文主体，附录类句段允许缺译 partial |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` | 纯译文：标题层级、段落顺序、图表题注、脚注、公式、参考文献原位保留 |
| `bilingual.md` | 双语对照：逐段原文段+译文段，段首稳定 ID 可回查 |
| `glossary.json` | 审定锁定术语表（term/缩写/锁定译名/依据/学科说明），可复用资产 |
| `term_audit.json` | 术语核对表：逐术语出现次数、合规次数、违规句段定位 |
| `report.md` / `edit_plan.json` / `findings.json` | 质量报告与机读修订清单 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map（逐句段溯源）、change_log、uncertainty |

## 关键方法（详见 references/）

- `references/terminology_method.md`：术语候选三类来源、锁定原则、学科歧义处置、首现全称规则。
- `references/failure_modes.md`：机检误报来源与复核要点（词形变化、标题内术语、跨学科同形词）。
- `references/worked_example.md`：完整标注示例（合成稿件，非正式案例）。

## 限制

- 术语候选基于词形与频次统计，低频术语（全篇出现 1-2 次且无缩写定义）可能不入候选；Agent 可在 glossary.json 手工补充。
- 机检核对锁定译名的**出现**，不能判断译名本身的学科正确性——译名质量由第 6 步 Agent 审定保证。
- 译名变体识别依赖 declared_variants 登记；未登记的隐性变体靠第 10 步人工复核兜底。
