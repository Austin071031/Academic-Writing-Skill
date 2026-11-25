# 术语治理与双语对齐（term governance）

## 术语表格式（/app/work/term_table.csv → 交付 /app/output/terminology_table.md）

建表时机：**润色前**，通读全文后建立，润色全程唯一依据。

```csv
concept,preferred,variants,first_use,status,note
均方根误差,均方根误差/root mean square error,RMSE;均方差,摘要S2,defined,首现已补英文全称
深度学习,深度学习/deep learning,DL;深度学習,引言S1,defined,
注意力机制,注意力机制/attention mechanism,注意力模型;attention,引言S4,candidate,候选待确认
```

- `preferred` 用 `/` 分隔中英双语首选写法（双语对齐的核心：一个概念两种语言形式
  绑定在同一行，润色时成对统一，不出现中文用 A 写法、英文用 B 写法的错位）。
- `variants` 收录源文中出现的全部写法（含错误写法），用 `;` 分隔。
- `status`：defined（有缩写定义）/ candidate（候选待确认）/ case_provided（案例自带）。
- 冲突优先级：案例自带术语表 > 领域惯例 > 频次最高 > Agent 提议（提议记入 note）。

## 双语对齐规则

1. 中英混排稿：术语表每个概念必须同时登记中文与英文形式；正文替换时成对执行。
2. 中译英稿件：英文术语以 preferred 的英文形式为唯一译法，禁止同义替换
   （mechanism/approach/scheme 不可混用）。
3. 缩写：首次出现须"全称（ABBR）"或"中文全称（English, ABBR）"；之后一律缩写。
4. 大小写与连字符按术语表（deep learning 小写；X-ray 连字符），不凭习惯。

## 回扫（润色完成后必做）

```bash
python3 /skills/weekly-skill/scripts/term_scan.py --table /app/work/term_table.csv \
    --text /app/output/polished.md --out /app/work
```

critical（同概念多写法并存）必须处置：统一为 preferred 后重跑，直至 critical=0。
处置不了的（如需保留某种写法）在 term_consistency_report 对应行下注明理由并
记入 result.json 的 manual_review_required。

## 交付

- `terminology_table.md`：术语表（含双语首选写法、变体、首现位置、状态、备注）。
- `term_consistency_report.md`：回扫结果（term_scan 输出复制到 /app/output）。
