# 材料抽取命令清单

产物统一写入 `/app/work/`。

## PDF

```bash
pdftotext -layout /input/paper.pdf /app/work/paper.txt      # 全文
pdftotext -layout -f N -l N /input/paper.pdf /app/work/paper_pN.txt   # 单页（定位图注/统计输出行号）
pdftoppm -png -r 200 -f N -l N /input/paper.pdf /app/work/paper_pN    # 渲染图页供读图
pdfinfo /input/paper.pdf                                     # 页数
```

读图时逐项记录：面板标签、坐标轴（物理量、单位、刻度、是否对数/截断）、每组数值与误差棒端点、图例、样本量标注。记录到 `/app/work/figure_notes.md`。

## 数据表（CSV/TSV/TXT）

Python stdlib `csv` 读入，先打印前 5 行确认表头与分隔符；缺失值（空串/NA/NaN）统一记为 null。

## XLSX

优先 `openpyxl`（`load_workbook(..., data_only=True)`）；不可用时用 libreoffice 转 CSV 或从论文 PDF 抽取。

## 统计输出

逐行完整读入：检验名、统计量、自由度、精确 p、效应量、CI、n、多重比较校正方法。

## 参考文献

从论文末尾或单独文件抽取全部条目到 `/app/work/references.txt`；讨论段引用只能出自该列表。

## 注意事项

- 按扩展名识别文件类型，不按文件名猜测内容（runtime contract）。
- 抽取失败（加密 PDF、损坏图片）时如实记录到 uncertainty，不得凭标签编造。
