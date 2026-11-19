# 最小示例（示例，非正式案例结果）

> 本文件演示 v1.0.1 引擎在合成文本上的端到端行为。输入为合成文本，
> 输出为真实引擎产物摘录，但**不代表任何正式评测案例的结果**。

## 合成输入（负例：三种写法混用 + 悬空引用）

`ch1.md`：

```markdown
# 第1章 绪论

固态电解质（solid-state electrolyte, SSE）是全固态电池的核心材料。本文研究硫化物基固态电解质的离子电导率。

已有研究表明，SSE 的电导率可达 3.2 mS/cm。结果如图3-1所示，数据汇总见表2-1。

solid-state electrolyte 的界面稳定性仍是关键挑战。
```

`ch2.md`：

```markdown
# 第2章 实验方法

采用交流阻抗谱测量 solid state electrolyte 的离子电导率。

图2-1 样品制备流程示意图。

表2-1 不同批次的电导率汇总。
```

## Phase 2：scan 输出

```text
[scan] 术语候选 3 条 | dangling 1 / unreferenced 1 / 编号问题 0 | 矛盾候选 1 对
[scan][WARN] 存在悬空交叉引用，validate_output 将 FAIL
```

xref_audit.json（摘录）：

```json
{"dangling": [{"raw": "图3-1", "pid": "C01-S001-P002", "kind": "figure", "target": "3-1"}],
 "unreferenced": [{"raw": "图2-1", "pid": "C02-S001-P002", "kind": "figure", "target": "2-1"}],
 "numbering": []}
```

术语候选（摘录）：

```json
[{"term": "固态电解质", "definition": "solid-state electrolyte", "abbr": "SSE",
  "definition_pid": "C01-S001-P001", "count": 6, "source": "abbr_definition"}]
```

## Phase 3：Agent 审定 → glossary_review.json

```json
[{"canonical": "固态电解质",
  "variants": ["SSE", "solid-state electrolyte", "solid state electrolyte"],
  "definition_pid": "C01-S001-P001", "keep": true}]
```

## Phase 3：glossary 输出（consistency_report.md 摘录）

```markdown
## 固态电解质（出现 6 次，异写率 50%）
- [C01-S001-P002] 写作「SSE」：…已有研究表明，SSE 的电导率可达 3.2 mS/cm…
- [C01-S001-P003] 写作「solid-state electrolyte」：…界面稳定性仍是关键挑战…
- [C02-S001-P001] 写作「solid state electrolyte」：…采用交流阻抗谱测量…
```

定义处（C01-S001-P001 括号内三种形式）按学术惯例豁免，不计异写。

## Phase 4：impact 输出（impact_report.md 摘录）

```markdown
# 影响面分析：固态电解质
受影响段落 6 个：
- **C01-S001-P001** — 引用术语（命中写法: 固态电解质/solid-state electrolyte/SSE）
- **C01-S001-P002** — 引用术语（命中写法: SSE）
- **C01-S001-P003** — 引用术语（命中写法: solid-state electrolyte）
- **C01-S001-P004** — 引用术语（命中写法: 固态电解质）
- **C02-S001-P001** — 引用术语（命中写法: solid state electrolyte）
- **C03-S001-P001** — 引用术语（命中写法: 固态电解质）
```

## 反例对照（写法统一 + 引用有定义）

同样的两章但全文统一写"固态电解质"、"图2-1/表2-1"引用与定义对应时：

```text
[scan] 术语候选 3 条 | dangling 0 / unreferenced 0 / 编号问题 0 | 矛盾候选 0 对
[glossary] 术语表 1 条 | 异写 0 处 | 冲突 0 处
```

零误报：dangling=0、异写=0。
