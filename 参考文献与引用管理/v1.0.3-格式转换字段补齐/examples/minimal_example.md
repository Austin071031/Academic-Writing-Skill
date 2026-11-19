# 最小示例（示例，非正式案例结果）

## 输入

`input.bib`（合成）：

```bibtex
@article{a1,
  title = {Silicon Anodes: A Review},
  author = {Smith, John and Lee, Ken and Brown, Amy and Clark, Zoe},
  year = {2020}, journal = {Nature Energy}, volume = {5}, number = {3},
  pages = {200--210}, doi = {10.1038/s41560-020-0555-5}
}
@article{a2,
  title = {锂离子电池硅负极研究进展},
  author = {张三 and 李四 and 王五 and 赵六},
  year = {2021}, journal = {储能科学与技术}, volume = {10}, number = {4}
}
```

## 调用

```bash
python3 scripts/parse_library.py input.bib --work work
python3 scripts/convert_engine.py --library work/library.json --to gbt2015_numeric \
    --outdir output --work work --specs-dir references/format_specs
```

## 示意输出（示例，非正式案例结果）

`output/converted_refs.txt`：

```text
[1] Smith J, Lee K, Brown A, et al. Silicon Anodes: A Review[J]. Nature Energy, 2020, 5(3): 200-210. DOI: 10.1038/s41560-020-0555-5.

[2] 张三，李四，王五，等．锂离子电池硅负极研究进展[J]．储能科学与技术，2021，10（4）．
```

`output/field_audit.json`（摘录）：

```json
{"rid": "R002", "missing_fields": ["pages", "doi"],
 "fills": [{"field": "pages", "action": "not_provided", "source_rid": null,
            "note": "材料未提供，不得臆造补齐"},
           {"field": "doi", "action": "not_provided", "source_rid": null,
            "note": "材料未提供，不得臆造补齐"}]}
```

要点：4 位作者按规范截断为前 3 + `et al` / `等`；英文条目半角、中文条目全角；
缺页码/DOI 如实登记，不臆造。
