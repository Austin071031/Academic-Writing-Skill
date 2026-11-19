# 材料抽取命令清单（因果边界方向要点）

产物写入 `/app/work/`。

## 研究设计信息抽取（本方向最关键）

`pdftotext -layout /input/paper.pdf /app/work/paper.txt` 后，在方法部分检索设计关键词并记录到 `/app/work/design_notes.md`：

- 随机化：random(ized)、随机分组、随机区组；
- 干预/处理：treatment、intervention、处理组、给药；
- 纵向/横断面：longitudinal、follow-up、横断面、cohort、prospective；
- 对照设置：control、sham、placebo、对照组；
- 盲法：blinded、double-blind、盲法。

材料中找不到设计信息时，默认按观察性（级 A）定级，并在 uncertainty 说明依据。

## PDF / 图表 / 数据表

```bash
pdftotext -layout -f N -l N /input/paper.pdf /app/work/paper_pN.txt
pdftoppm -png -r 200 -f N -l N /input/paper.pdf /app/work/paper_pN
```

读图记录坐标轴、数值、误差棒与 n 到 `/app/work/figure_notes.md`。数据表用 Python stdlib `csv`；XLSX 优先 `openpyxl`（`data_only=True`）；统计输出逐行读入并记录检验名、p、效应量。

## 规则

- 按扩展名识别文件，不按文件名猜测内容。
- 设计信息、统计输出抽取失败如实写入 uncertainty，不得凭领域惯例假定实验设计。
