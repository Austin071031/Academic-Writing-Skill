#!/usr/bin/env python3
"""engine_pre.py（一致复核方向）— 任务分型与底稿登记。
识别 generate/rewrite/proofread 任务；改稿/校对任务快照底稿（draft_snapshot.json：逐段哈希+原文），
供成稿后 diff 留痕。同时建立术语基线（缩写与定义）。"""
import argparse, hashlib, json, os, re, subprocess, sys

def extract(path, ext, dst):
    try:
        if ext == ".pdf":
            r = subprocess.run(["pdftotext", "-layout", path, dst], capture_output=True, timeout=120)
            return r.returncode == 0 and os.path.isfile(dst)
        if ext in (".docx", ".doc"):
            r = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", path], capture_output=True, timeout=60)
            if r.returncode == 0:
                open(dst, "w", encoding="utf-8").write(r.stdout.decode("utf-8", "replace")); return True
            import zipfile
            xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
            ls = [t for t in ("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in xml.split("</w:p>")) if t.strip()]
            open(dst, "w", encoding="utf-8").write("\n".join(ls)); return bool(ls)
        if ext in (".txt", ".md", ".json", ".bib", ".csv", ".tsv"):
            open(dst, "w", encoding="utf-8").write(open(path, encoding="utf-8", errors="replace").read(500000)); return True
    except Exception:
        return False
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input"); ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    brief = {}
    bp = os.path.join(a.work, "brief.json")
    if os.path.isfile(bp):
        try: brief = json.load(open(bp, encoding="utf-8"))
        except Exception: pass
    task = (brief.get("task_excerpt") or "").lower()
    mode = "generate"
    if re.search(r"校对|核验|核查|proofread|check|verify", task): mode = "proofread"
    elif re.search(r"改写|修改|润色|修订|底稿|rewrite|revise|polish", task): mode = "rewrite"
    # 底稿识别：文件名含 draft/底稿/原稿/manuscript，或任务明确提到且只有一份 md/docx/txt 主体文档
    draft_path, draft_rel = None, None
    for m in brief.get("materials", []):
        base = os.path.basename(m.get("rel", "")).lower()
        if re.search(r"draft|底稿|原稿|manuscript|paper", base) and m.get("ext") in (".md", ".txt", ".docx", ".doc"):
            draft_path, draft_rel = m["path"], m["rel"]; break
    tdir = os.path.join(a.work, "text"); os.makedirs(tdir, exist_ok=True)
    snap = {"mode": mode, "draft_rel": draft_rel, "paragraphs": []}
    if draft_path:
        tp = os.path.join(tdir, "DRAFT.txt")
        if extract(draft_path, os.path.splitext(draft_path)[1].lower(), tp):
            paras = [p.strip() for p in re.split(r"\n\s*\n", open(tp, encoding="utf-8", errors="replace").read()) if p.strip()]
            snap["paragraphs"] = [{"pid": f"P{i+1:03d}", "sha": hashlib.md5(re.sub(r"\s+", "", p).encode()).hexdigest()[:10],
                                   "text": p[:500]} for i, p in enumerate(paras[:300])]
    else:
        # 全部材料文本化，供数字/术语语料
        for i, m in enumerate(brief.get("materials", [])):
            mid = f"M{i+1:02d}"
            extract(m["path"], m.get("ext", ""), os.path.join(tdir, f"{mid}.txt"))
    abbr = {}
    for fn in os.listdir(tdir):
        try: text = open(os.path.join(tdir, fn), encoding="utf-8", errors="replace").read()
        except Exception: continue
        for m in re.finditer(r"([\w一-鿿][\w一-鿿 ]{1,18}?)[(（]([A-Z][A-Z0-9]{1,7})[)）]", text):
            abbr.setdefault(m.group(2), m.group(1).strip())
    snap["abbreviations"] = abbr
    json.dump(snap, open(os.path.join(a.work, "draft_snapshot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.work, "task_profile.md"), "w", encoding="utf-8") as f:
        f.write(f"# 任务分型\n\n- 模式: **{mode}**（{'底稿已快照，成稿后做逐段 diff 留痕' if snap['paragraphs'] else '无底稿快照：generate 任务或未识别到底稿文件'}）\n")
        f.write(f"- 底稿: {draft_rel or '未识别'}\n- 术语基线（材料中的缩写定义）: {json.dumps(abbr, ensure_ascii=False)[:400]}\n")
        if mode != "generate" and not snap["paragraphs"]:
            f.write("\n> 注意：任务疑似改稿/校对但未找到底稿文件——在 uncertainty 说明，按 generate 处理或请人工确认底稿是哪份材料。\n")
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## engine_pre profile mode={mode} draft={draft_rel} paras={len(snap['paragraphs'])} abbr={len(abbr)}\n")
    print(json.dumps({"ok": True, "mode": mode, "draft": draft_rel, "paragraphs": len(snap["paragraphs"])}, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
