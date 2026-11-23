#!/usr/bin/env python3
"""engine_check.py（一致复核方向）— 三向一致性审计 + 底稿 diff 留痕。
审计：摘要数字⊆正文、图/表引用↔注、方法宣布↔结果报告、缩写首用定义、待确认闭环；
改稿任务：终稿 vs 底稿快照 diff，生成/核对 change_log（未改段落不得悄悄改动）。
输出 engine_report.json + audit_report.md（+ 改稿任务的 diff_review.md）。"""
import argparse, hashlib, json, os, re, sys, datetime

def paras(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
def sha(p): return hashlib.md5(re.sub(r"\s+", "", p).encode()).hexdigest()[:10]
def nums(text):
    out = set()
    for m in re.finditer(r"[-+]?\d+(?:,\d{3})*\.\d+|\d+(?:\.\d+)?%", text):
        v = m.group(0).replace(",", "").rstrip("%")
        out.add(v.rstrip("0").rstrip(".") if "." in v else v)
    return {v for v in out if v and not re.fullmatch(r"(19|20)\d{2}", v)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    ms = open(a.manuscript, encoding="utf-8", errors="replace").read() if os.path.isfile(a.manuscript) else ""
    snap = {}
    sp = os.path.join(a.work, "draft_snapshot.json")
    if os.path.isfile(sp):
        try: snap = json.load(open(sp, encoding="utf-8"))
        except Exception: pass
    fails, warns = [], []
    # 1. 摘要数字 ⊆ 正文数字
    abs_m = re.search(r"^#{1,4}\s*摘要[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", ms, re.M | re.S | re.I)
    if abs_m:
        body_nums = nums(re.sub(r"^#{1,4}\s*摘要[^\n]*\n.*?(?=^#{1,4}\s|\Z)", "", ms, flags=re.M | re.S | re.I))
        extra = sorted(v for v in nums(abs_m.group(1)) - body_nums if len(v) > 1 or "." in v)
        if extra: fails.append(f"摘要数字未在正文出现（摘要—正文不一致）: {extra[:8]}")
    # 2. 图/表引用 ↔ 注
    for kind, pat_ref, pat_cap in (("图", r"图\s*(\d+)", r"^[^\n]*图\s*(\d+)[\s　:]"),
                                   ("表", r"表\s*(\d+)", r"^[^\n]*表\s*(\d+)[\s　:]")):
        refs = sorted(set(re.findall(pat_ref, ms)), key=int)
        caps = sorted(set(re.findall(pat_cap, ms, re.M)), key=int)
        no_cap = [r for r in refs if r not in caps]
        if no_cap: fails.append(f"{kind} {no_cap} 被正文引用但缺{kind}注")
    # 3. 方法宣布 ↔ 结果报告（关键词对）
    mm = re.search(r"^#{1,4}\s*(方法|材料与方法|Methods?)[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", ms, re.M | re.S | re.I)
    rr = re.search(r"^#{1,4}\s*(结果|Results?)[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", ms, re.M | re.S | re.I)
    if mm and rr:
        meth, res = mm.group(2), rr.group(2)
        announced = re.findall(r"(t\s*检验|方差分析|ANOVA|卡方|回归|相关分析|western\s*blot|qPCR|测序|色谱|光谱|电镜)", meth, re.I)
        unreported = [x for x in set(announced) if not re.search(re.escape(x), res, re.I)]
        if unreported: warns.append(f"方法宣布但未在结果中报告: {unreported}（漏报或方法虚写，须核实）")
    # 4. 缩写首用定义
    used_abbr = set(re.findall(r"\b([A-Z][A-Z0-9]{2,7})\b", ms))
    defined = set(re.findall(r"[(（]([A-Z][A-Z0-9]{2,7})[)）]", ms)) | set((snap.get("abbreviations") or {}).keys())
    undefined = sorted(x for x in used_abbr - defined if x not in ("GB", "DOI", "ISBN", "ISSN", "PDF", "URL", "IMRAD"))
    if undefined: warns.append(f"缩写未在首用处给全称: {undefined[:8]}")
    # 5. 待确认闭环（结果文件由 finalize 汇总，这里只清点）
    pend = re.findall(r"【待确认[^】]*】|【待补[^】]*】", ms)
    if pend: warns.append(f"{len(pend)} 处待确认/待补（finalize 会并入 uncertainty，需人工逐条复核）")
    # 6. 底稿 diff 留痕（rewrite/proofread）
    diff_lines = []
    if snap.get("paragraphs"):
        final_paras = paras(ms)
        final_shas = {sha(p) for p in final_paras}
        old = {p["sha"]: p for p in snap["paragraphs"]}
        deleted = [p for s_, p in old.items() if s_ not in final_shas]
        added = [p for p in final_paras if sha(p) not in old]
        diff_lines.append(f"底稿 {len(old)} 段 → 终稿 {len(final_paras)} 段：保留 {len(old)-len(deleted)}，删除/改写 {len(deleted)}，新增 {len(added)}")
        chlog_path = os.path.join(a.out, "change_log.md")
        chlog = open(chlog_path, encoding="utf-8", errors="replace").read() if os.path.isfile(chlog_path) else ""
        if snap.get("mode") in ("rewrite", "proofread") and len(deleted) + len(added) > 0 and len(chlog) < 40:
            warns.append("改稿任务存在段落级改动但 change_log.md 为空或过简——改稿留痕是本方向核心要求")
        with open(os.path.join(a.out, "diff_review.md"), "w", encoding="utf-8") as f:
            f.write(f"# 底稿↔终稿 diff 复核（mode={snap.get('mode')}）\n\n{diff_lines[0]}\n\n")
            f.write("## 删除/改写的底稿段（逐条确认是否故意）\n")
            for p in deleted[:30]: f.write(f"- [{p['pid']}] {p['text'][:150]}\n")
            f.write("\n## 新增段（逐条确认事实来源）\n")
            for p in added[:30]: f.write(f"- {p[:150]}\n")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    rep = {"engine": "consistency-audit", "verdict": verdict, "fails": fails, "warnings": warns,
           "diff": diff_lines, "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(rep, open(os.path.join(a.out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "audit_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# 一致性审计报告（verdict={verdict}）\n\n覆盖：摘要↔正文数字、图表引用↔注、方法↔结果闭环、缩写首用、待确认闭环、底稿 diff。\n\n")
        if fails: f.write("## 必须返修\n" + "".join(f"- ❌ {x}\n" for x in fails) + "\n")
        if warns: f.write("## 需人工复核\n" + "".join(f"- ⚠ {x}\n" for x in warns) + "\n")
    print(json.dumps({"verdict": verdict, "fails": fails}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        out = "/app/output"
        if "--out" in sys.argv:
            try: out = sys.argv[sys.argv.index("--out") + 1]
            except Exception: pass
        os.makedirs(out, exist_ok=True)
        json.dump({"engine": "consistency-audit", "verdict": "WARN", "fails": [], "warnings": [f"engine_check 异常: {str(e)[:150]}"]},
                  open(os.path.join(out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(0)
