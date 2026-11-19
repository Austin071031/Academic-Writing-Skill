# 材料抽取命令清单（证据对照方向要点）

产物写入 `/app/work/`。

## 参考文献列表抽取（本方向最关键）

```bash
# 论文全文
pdftotext -layout /input/paper.pdf /app/work/paper.txt

# 定位参考文献起始页后逐页抽取
pdftotext -layout -f N -l N /input/paper.pdf /app/work/paper_pN.txt
```

人工（Agent）从参考文献节逐条切分，生成 `/app/work/references.txt`（每条一行/一块，原始文本保留），并整理 `/app/work/reference_keys.json`：

```json
[
  {"key": "Zhang", "year": "2020", "raw": "Zhang, Y., Li, X. ..."},
  {"key": "Smith", "year": "2019", "raw": "..."}
]
```

注意：作者姓名中的连字符（O'Brien）、变音字符（Müller）保留原样；同年同姓多条全部登记。

## 正文图表定位

```bash
pdftoppm -png -r 200 -f N -l N /input/paper.pdf /app/work/paper_pN
```

建立 `/app/work/data_anchors.md`：每条观察一行（D 编号 + 图/表 + 关键数值），供讨论段【数据：…】锚引用。

## 数据表与统计输出

Python stdlib `csv` 读 CSV/TSV；XLSX 优先 `openpyxl`（`data_only=True`）；统计输出逐行读入。

## 规则

- 按扩展名识别文件，不按文件名猜测内容。
- 文献列表抽取不完整（缺条目）时，宁可缩小引用范围也不保留无法核验的引用。
