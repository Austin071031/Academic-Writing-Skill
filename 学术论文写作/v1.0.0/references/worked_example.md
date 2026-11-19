# 最小调用示例（合成示例，非正式测试案例）

> 以下输入与输出为说明接口而**人工合成的示例**，不代表平台正式案例，不得当作预制答案。

## 示例输入
```
/input/case.json:
{"case_id": "DEMO-SYNTH-01",
 "output_contract": ["case_id", "status", "manuscript", "evidence_map", "uncertainty", "change_log"],
 "constraints": {"language": "zh", "citation_style": "gbt7714", "word_target": 800}}
/input/task.md:
  依据提供的实验数据与参考文献列表，撰写论文"结果"章节初稿（约 800 字），
  需包含图注，数值与单位须与数据一致，引用采用 GB/T 7714 顺序编码制。
/input/results.csv          （两组实验数据）
/input/refs.txt             （3 条参考文献，含 DOI）
/input/notes.md             （实验记录）
```

## 调用方式
```bash
# 第 1 段：全自动预处理
bash /skills/weekly-skill/scripts/run_pipeline.sh pre
# → /app/work/brief.json（modes=[generate]、required_sections 含 results/figures/references）
# → /app/work/material_index.json、materials_digest.md
# → /app/work/facts.json（CSV 行值+列统计、notes.md 含数值句子）、bibliography.json（3 条）
# → /app/output/result.json 已有 partial 骨架

# 第 2 段：Agent 读 facts_digest.md 与 materials_digest.md，写 /app/work/sections/01-results.md，
#         同步维护 /app/work/evidence_map.json，然后：
cat /app/work/sections/*.md > /app/output/manuscript.md

# 第 3 段：核验+渲染+组装+终检
bash /skills/weekly-skill/scripts/run_pipeline.sh post
```

## 示意输出（示例）
```
/app/output/
├── result.json            # status=success；output_contract 6 字段齐全；
│                          # uncertainty 含 "refs.txt 第 2 条缺卷期页（仅提示）"
├── manuscript.md          # 结果节初稿：数值均出自 results.csv；图 1 图注完整；引用 [1]-[3]
├── manuscript.docx / manuscript.pdf / preview/page-1.png
├── evidence_map.md        # 12 条映射：9 条 number→M01#rowN，3 条 citation→R001-R003
├── consistency_report.md  # verdict=PASS（numbers 41/41 有出处；citations 无悬空）
├── change_log.md          # "参考文献按首次引用顺序重排"
└── validation.md          # overall=PASS
```

## 异常变体演示（示例）
- 删除 /input/results.csv 后重跑：facts.json 仅剩文本事实，结果节相应数值位标【待确认】，
  result.json status=partial，uncertainty 列出缺口——演示"材料不足不补造"。
- 在 manuscript.md 中手写一个材料中没有的数字 `97.5%` 后重跑 post：
  consistency verdict=FAIL，报告列出该数字无出处，validate 阻止 status=success。
