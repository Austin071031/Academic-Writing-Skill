# 最小调用示例（合成示例，仅示意接口与流程，非正式案例结果）

citation_audit.csv（节选）
```csv
ref_id,in_text,in_list,metadata_complete,missing_fields,quote_verified,secondary,verification_status,verification_path
R01,yes,yes,yes,,yes,false,verified_offline,https://doi.org/10.1000/demo01
R02,yes,yes,no,doi;volume_issue_pages,yes,false,offline_unverified,Crossref 查询: "Exercise and HbA1c" AND AUTH "Zhang"
R03,yes,no,no,all,no,false,not_in_reference_list,
R04,yes,yes,yes,,no,false,support_mismatch,"原文仅报告次要终点，正文却引其支撑主要终点"
R05,yes,yes,yes,,yes,true,secondary_citation,"正文摘录标注'as cited in R02'，建议补原文"
```

处置：R03 记 error（挂空引用，须补文献表条目或删文内引用）；R04 记 error（引用与论断不匹配）；
R02 著录缺 DOI，给出 Crossref 检索式供人工回查；R05 降级为背景引用。
