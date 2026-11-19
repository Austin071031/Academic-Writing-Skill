# spec.json 规格字典与检查项语义

`spec.json` 是流水线的单一事实源：measure（模板实测）与 extract（任务文本/cls/pdf 抽取）合并产物，文本要求优先于模板实测，冲突登记在 `conflicts`。所有可修改项都允许在 `adapt` 前人工（Agent）修订后重跑。

## 顶层结构

```jsonc
{
  "source": "模板路径（实测时）",
  "page":      { /* 页面设置 */ },
  "body":      { /* 正文 */ },
  "headings":  { /* 标题层级 */ },
  "captions":  { /* 图表题注 */ },
  "tables":    { /* 表格 */ },
  "references":{ /* 参考文献 */ },
  "header_footer": { /* 页眉页脚 */ },
  "toc":       { /* 目录 */ },
  "styles":    { /* 实测样式表（measure 阶段） */ },
  "numbering": { /* 实测编号表（measure 阶段） */ },
  "conflicts": [ {"path": "body.size_pt", "measured": 12.0, "textual": 10.5, "resolution": "textual_wins"} ],
  "unresolved": ["page.margin_top_mm", "..."],   // 缺项，须人工补齐或留空并说明
  "_unresolved_hints": ["任务文本中无法解析的要求句"]
}
```

## page

| 键 | 含义 | 例 |
|---|---|---|
| `paper` | 纸张 | "A4" / "Letter" |
| `width_mm`, `height_mm` | 页面实测尺寸 | 210.0, 297.0 |
| `orient` | 方向 | "portrait" |
| `margin_top_mm`…`margin_right_mm` | 页边距（毫米） | 25.0 |
| `header_mm`, `footer_mm` | 页眉/页脚距边 | 15.0, 17.5 |
| `columns` | 分栏 | 1 / 2 |

## body

| 键 | 含义 | 例 |
|---|---|---|
| `size_pt` | 字号（磅；中文字号换算见下） | 12.0（小四） |
| `fonts.ascii` / `fonts.eastAsia` | 西文/中文字体 | "Times New Roman" / "宋体" |
| `line_spacing` | 多倍行距（倍数） | 1.5 |
| `line_spacing_pt` + `line_rule` | 固定值行距 | 20.0 + "atLeast" |
| `align` | 对齐 | "both" |

中文字号→磅：小三 15、四号 14、小四 12、五号 10.5、小五 9（完整表见 extract_spec.py 的 CN_SIZE）。

## headings

| 键 | 含义 |
|---|---|
| `numbering` | `"decimal_multilevel"`（1/1.1/1.1.1）/ `"chinese_chapter"`（第X章/N.N）/ `"none"` |
| `h1`…`h4` | `{ "size_pt", "bold", "align", "fonts": {"ascii","eastAsia"} }`；缺省用内置学术默认（一级三号居中黑体等） |

## captions / tables / references / header_footer / toc

| 键 | 含义 |
|---|---|
| `captions.size_pt` | 题注字号（默认五号 10.5） |
| `captions.figure_position` / `table_position` | "below" / "above"（结构性核验） |
| `tables.three_line` | 三线表（默认 true；顶/底 1.5pt、表头下 0.75pt、表头跨页重复、表格居中、无竖线） |
| `references.style` | gb_t_7714 / ieee / apa / …（不做条目重排，仅样式统一） |
| `references.size_pt` / `references.hanging_indent` | 字号 / 悬挂缩进 |
| `header_footer.page_number` / `page_number_position` / `page_number_align` | 页码域、页脚/页眉、对齐 |
| `toc.required` | 需要目录时插入 TOC 域并两遍渲染回填真页码 |

## 检查项清单（checklist.md）语义

measure 阶段把实测值渲染为 `- [ ] 项 = 值` 的核对清单；compliance 阶段按同一字典逐项核验 adapted docx，输出 PASS/FAIL/SKIP 与实测值——`SKIP` 表示任务未要求（不算缺陷），`FAIL` 必须先修 spec 再重跑，不得留下静默失败。

## 修改 spec 的正确姿势

1. 只改 `/app/work/spec.json`（它是输入，不是证据）；
2. 重跑 `--stages adapt,fidelity,compliance,render,result`（不要带 `spec`，否则被重新生成覆盖）；
3. 修改来源（任务文本哪一句）可写进 `uncertainty.notes`。
