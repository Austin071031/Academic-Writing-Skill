# 任务类型自适应方法（task adaptation）

## 四类任务识别（inspect_case）

| task_type | task.md 特征 | 材料特征 | 管线分支 |
|-|-|-|-|
| full_translation | 翻译/translate/译（默认） | 单一原文稿件 | A：句段切分→Agent 翻译 |
| proofread_translation | 校对/审校/后编辑/proofread/现有译文 | 原文 + 译文双文件（文件名含 译文/zh/en/translation 等） | B：已有译文对齐→审校 |
| revise_tracked | 修订/修改标记/track changes | 原文（±译文） | B + tracked 交付 |
| bilingual_writing | 撰写/写作 双语/摘要 | 材料为事实底稿 | C：句段骨架约束写作 |

材料角色判定：manuscript_candidates 按文件名启发式分为 source_manuscript 与
existing_translation；校对类任务未识别到译文文件时 inspection.issues 提示，
Agent 用 `--translation-file` 显式指定（优先于启发式）。

## 已有译文对齐算法（align_existing_translation.py）

1. 译文按同一套中英混排句切分拆分（含小数/缩写保护）。
2. 按源文句段顺序消耗译文句子：期望值 = 源句段长度 × 语言比
   （英→中约 1 词:1.9 字；中→英约 1 字:0.6 词），累计译文句至期望值 0.75–1.6 倍区间。
3. 比例异常（<0.45 或 >2.2）或单段消耗 >2 句 → needs_review，交 Agent 人工确认。
4. 映射结果直接写 translations.jsonl —— 后续机检、双语对照、缺译统计与
   翻译模式完全一致，**审校修订复用同一修订闭环**（追加同 seg_id 新译文）。

## 分支交付差异

- 分支 B/tracked：Agent 修订全部经 change_log 自动 diff 留痕（修订痕迹）；
  ⚠ 标注稿（机检问题句段三联对照）即为审校产物。
- 分支 C：双语新写内容必须逐句段挂到材料依据（evidence_map 的 source 字段），
  无源内容走 manual_confirmations。

## 为什么这能提分

固定案例集包含多种任务形态时，单一“整篇翻译”管线在非翻译案例上任务完成度
直接归零；自适应分支使每种任务都产出形态正确的交付物（修订标记稿/双语写作），
共用同一套可核验机制（句段坐标、数字比对、溯源）。
