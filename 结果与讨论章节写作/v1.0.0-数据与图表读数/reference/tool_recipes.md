# 材料抽取命令清单

按扩展名选择对应方法。所有抽取产物写入 `/app/work/`，命名规则：`{原名}.txt`、`{原名}_p{页码}.png`。

## PDF

```bash
# 全文抽取（保留版面，便于定位表格）
pdftotext -layout /input/paper.pdf /app/work/paper.txt

# 逐页抽取（定位图注、统计输出行号）
pdftotext -layout -f 3 -l 3 /input/paper.pdf /app/work/paper_p3.txt

# 渲染含图页面（读图必备）
pdftoppm -png -r 200 -f 3 -l 3 /input/paper.pdf /app/work/paper_p3

# PDF 信息（页数、版本）
pdfinfo /input/paper.pdf
```

读图时把渲染出的 PNG 作为图像读入，逐项记录坐标轴刻度、单位、每根柱/每个点的数值、误差棒端点、图例、面板标签；记录到 `/app/work/figure_notes.md`，一图一节。

## CSV / TSV / TXT 数据

```python
import csv
with open(path, newline='', encoding='utf-8-sig') as f:
    rows = list(csv.reader(f))
# 先打印前 5 行确认表头与分隔符，再全量读入台账
```

注意：分隔符可能是逗号、制表符或分号；表头可能跨行；缺失值可能是空串、`NA`、`NaN`——读入时统一记为 null 并在台账 n 中如实扣除。

## XLSX

```python
try:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            print(row)
except ImportError:
    # 退化方案：用 libreoffice 转 csv 或 pdftotext 从论文 PDF 抽表
```

## 统计输出（txt/json/log）

逐行完整读入，不要抽样。记录：检验名、统计量符号与数值、自由度、精确 p、效应量、置信区间、样本量、多重比较校正方法。

## 图像（png/jpg/tiff）

直接用视觉能力读图；若图像模糊或截断，先尝试更高分辨率来源（PDF 内嵌图通常比截图清晰）。EPS 先用 `pdftoppm` 或 Python `PIL`（若可用）转 PNG。

## 参考文献列表

从论文末尾或单独 bib/txt 抽取全部条目，存 `/app/work/references.txt`，供讨论段引用核对（引用必须出自此列表，不得虚构）。
