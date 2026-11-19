# 材料抽取命令清单（校准方向要点）

产物写入 `/app/work/`。

## 统计输出（本方向最关键材料）

逐行完整读入 `/input/` 下统计输出文件（txt/json/log/sav 导出的 csv），登记到 `/app/work/stats_extract.md`：

```
[stats_output.txt:14] t.test: control vs low-dose, t(4) = 0.61, p = 0.31, n=3/3
[stats_output.txt:17] t.test: control vs high-dose, t(4) = 7.2, p = 0.002, d = 1.8, n=3/3
```

无独立统计输出时，从论文正文/图注中检索统计叙述（"p < 0.05, one-way ANOVA"），并注明来源页码；完全没有统计信息时在 comparisons.md 顶部注明"材料无统计检验输出"。

## PDF / 图表 / 数据表

```bash
pdftotext -layout /input/paper.pdf /app/work/paper.txt
pdftotext -layout -f N -l N /input/paper.pdf /app/work/paper_pN.txt
pdftoppm -png -r 200 -f N -l N /input/paper.pdf /app/work/paper_pN
```

数据表用 Python stdlib `csv` 读入；XLSX 优先 `openpyxl`（`data_only=True`）。读图逐项记录坐标轴、数值、误差棒与样本量到 `/app/work/figure_notes.md`。

## 规则

- 按扩展名识别文件，不按文件名猜测内容。
- 抽取失败如实写入 uncertainty，不得凭领域常识补造统计量。
