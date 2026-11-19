# 最小调用示例（示例，非正式案例结果）

## 输入
- task.md：请将给定论文材料改写为面向公众的科普文章，篇幅控制在 800 字以内；论断强度必须与源文一致。
- source_paper.md：含"循环测试表明…85.3%""初步表明该方法可推广…""阻抗与厚度密切相关""该策略有望为工程化提供路径"等论断的论文节选（合成）。

## 调用
```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --work /app/work
python3 /skills/weekly-skill/scripts/parse_source.py /input/source_paper.md --work /app/work
python3 /skills/weekly-skill/scripts/claim_engine.py extract --source /app/work/source.json --work /app/work
# Agent 依据 source_claims.json 撰写 /app/work/rewrite_draft.md
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/claim_engine.py check --rewrite /app/work/rewrite_draft.md --work /app/work
```

## 示意输出（示例）
- source_claims.json：论断 5 条（L1×3、L2×1、L3×1；相关性论断 1 条；否定论断 1 条）。
- 正例改写稿（"测试表明…85.3%""初步结果提示…""该方法有望用于更多体系"）：
  claim_report.json verdict=**PASS**，5 条全 kept，exit=0。
- 反例改写稿（"证明了…所有体系""将彻底解决""厚度导致阻抗变化"＋源外新结论句）：
  verdict=**FAIL**，7 个 critical（upgraded×2、absolute_upgrade×2、causality_upgrade、negation_flip、new_claim），exit=2；
  每条带 rpid 定位与"回退到源文同级措辞"建议，修复后重跑至 exit=0 方可交付。
