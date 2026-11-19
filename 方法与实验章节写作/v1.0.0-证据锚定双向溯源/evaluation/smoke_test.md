# 本地冒烟记录（合成材料）

材料：合成 paper.pdf（3 页方法/数据/基线陈述）、config.yaml（learning_rate 3e-4、batch 32、
epochs 10、seed 42、hidden 768、layers 12）、train.log（seed=42、实际 lr 0.0003、acc=0.913）、
train.py（argparse 默认 lr 1e-3，与配置不同，构成取舍场景）、data_card.md（SynthBench v1.2、
8:1:1 划分、基线与指标）。

预期行为（已验证）：

1. inspect_case 分类 pdf/config/log/code/doc 正确，PDF 按页文本化（===== PAGE k =====）。
2. extract_evidence 产出候选 19 条，learning_rate 三值（配置 3e-4 / 日志 0.0003 / 代码 1e-3）
   进入 value_index 供取舍。
3. 写作后 build 装配章节与三附录；audit 对"环境 Python 3.11 + PyTorch 2.1"这类无来源声明
   给出 forward_leaks（verdict=fail），删除后 pass——证明泄漏检查有效。
4. validate_output PASS；render_previews 产出 PDF 预览（有 pandoc 时）。
5. result.json 含 case_id、output_contract 注入字段（chapter_path/verification）、
   uncertainty（基线数值缺口）与 manual_confirmations。
