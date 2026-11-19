#!/usr/bin/env python3
"""build_material_index.py — 材料索引：提取 /input 各材料为带锚点文本段。

产出（--work 下）：
  material_index.json   每个材料：id、路径、类型、段数、锚点规则、可读状态
  materials_digest.md   限长摘要（默认总预算 48KB），供 Agent 优先阅读
  text/<mat_id>.txt     每个材料的完整提取文本（锚点定位的依据）
锚点规则：PDF/文本 → p<页>.l<行> 或 l<行>；CSV/TSV → sheet!<行号>；DOCX → para<段号>。
仅用标准库 + 系统 pdftotext（缺失时该 PDF 标 unreadable）。任何单材料失败不影响其余。
"""
import argparse, json, os, re, subprocess, sys, datetime, csv

DIGEST_BUDGET = 48000        # digest 总字符预算
PER_MATERIAL_CAP = 6000      # 单材料 digest 上限
SEG_CAP = 400                # 单材料最多索引段数

def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, b"", str(e).encode()

def extract_pdf(path, txt_path):
    rc, _out, err = run(["pdftotext", "-layout", path, txt_path], timeout=120)
    if rc != 0 or not os.path.isfile(txt_path):
        rc2, _o2, err2 = run(["pdftotext", path, txt_path], timeout=120)
        if rc2 != 0 or not os.path.isfile(txt_path):
            return False, (err or err2).decode("utf-8", "replace")[:200]
    return True, ""

def extract_docx(path):
    """返回段落列表；pandoc 优先，其次 python-docx，最后裸 XML 正则。"""
    rc, out, _e = run(["pandoc", "-t", "plain", "--wrap=none", path], timeout=60)
    if rc == 0 and out:
        return [l for l in out.decode("utf-8", "replace").splitlines()]
    try:
        import docx  # python-docx
        d = docx.Document(path)
        return [p.text for p in d.paragraphs]
    except Exception:
        pass
    try:
        import zipfile
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        paras = re.split(r"</w:p>", xml)
        lines = []
        for p in paras:
            txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
            if txt.strip():
                lines.append(txt)
        return lines
    except Exception:
        return []

def index_text_lines(lines, mat_id, page_aware):
    """把文本行切块为带锚点段落。page_aware 时按 \f 分页。"""
    segs, buf, start_line, page, line_no = [], [], None, 1, 0
    def flush(end_line):
        if buf:
            txt = "\n".join(buf).strip()
            if txt:
                loc = f"p{page}.l{start_line}-{end_line}" if page_aware else f"l{start_line}-{end_line}"
                segs.append({"seg_id": f"{mat_id}#{loc}", "locator": loc,
                             "page": page if page_aware else None,
                             "text": txt[:2000]})
    for raw in lines:
        if page_aware and "\f" in raw:
            parts = raw.split("\f")
            for j, part in enumerate(parts):
                if j > 0:
                    flush(line_no); buf.clear(); start_line = None
                    page += 1; line_no = 0
                line_no += 1
                if part.strip():
                    if start_line is None: start_line = line_no
                    buf.append(part)
                    if sum(len(x) for x in buf) > 1200:
                        flush(line_no); buf.clear(); start_line = None
            if len(segs) >= SEG_CAP: break
            continue
        line_no += 1
        if raw.strip():
            if start_line is None: start_line = line_no
            buf.append(raw)
            if sum(len(x) for x in buf) > 1200:
                flush(line_no); buf.clear(); start_line = None
        else:
            flush(line_no); buf.clear(); start_line = None
        if len(segs) >= SEG_CAP: break
    flush(line_no)
    return segs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    text_dir = os.path.join(args.work, "text")
    os.makedirs(text_dir, exist_ok=True)

    brief_path = os.path.join(args.work, "brief.json")
    brief = {}
    if os.path.isfile(brief_path):
        try:
            brief = json.load(open(brief_path, encoding="utf-8"))
        except Exception:
            brief = {}
    materials = brief.get("materials") or []
    if not materials:  # brief 缺失时自行扫描
        for root, _d, files in os.walk(args.input):
            for fn in sorted(files):
                if fn.lower() in ("case.json", "task.md"):
                    continue
                p = os.path.join(root, fn)
                materials.append({"path": p, "rel": os.path.relpath(p, args.input),
                                  "ext": os.path.splitext(fn)[1].lower(),
                                  "size": os.path.getsize(p) if os.path.isfile(p) else -1})

    index, digest_parts, used = [], [], 0
    for i, m in enumerate(materials):
        mat_id = f"M{i+1:02d}"
        ext, path = m.get("ext", ""), m.get("path", "")
        entry = {"material_id": mat_id, "path": m.get("rel", path), "abs_path": path,
                 "ext": ext, "size": m.get("size", -1),
                 "status": "ok", "n_segments": 0, "anchor_rule": "", "note": ""}
        segs = []
        try:
            if ext == ".pdf":
                txt_path = os.path.join(text_dir, f"{mat_id}.txt")
                ok, err = extract_pdf(path, txt_path)
                if not ok:
                    entry.update(status="unreadable", note=f"pdftotext 失败: {err}")
                else:
                    lines = open(txt_path, encoding="utf-8", errors="replace").read().splitlines()
                    segs = index_text_lines(lines, mat_id, page_aware=True)
                    entry["anchor_rule"] = "p<页>.l<起行>-<止行>"
            elif ext in (".txt", ".md", ".bib", ".ris", ".json"):
                lines = open(path, encoding="utf-8", errors="replace").read(500000).splitlines()
                with open(os.path.join(text_dir, f"{mat_id}.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                segs = index_text_lines(lines, mat_id, page_aware=False)
                entry["anchor_rule"] = "l<起行>-<止行>"
            elif ext in (".csv", ".tsv"):
                delim = "\t" if ext == ".tsv" else ","
                rows = []
                with open(path, encoding="utf-8", errors="replace", newline="") as f:
                    for r in csv.reader(f, delimiter=delim):
                        rows.append(r)
                        if len(rows) > 5000: break
                with open(os.path.join(text_dir, f"{mat_id}.txt"), "w", encoding="utf-8") as f:
                    for j, r in enumerate(rows, 1):
                        f.write(f"row{j}: " + " | ".join(r) + "\n")
                for j, r in enumerate(rows, 1):
                    segs.append({"seg_id": f"{mat_id}#row{j}", "locator": f"row{j}",
                                 "page": None, "text": " | ".join(r)[:2000]})
                    if len(segs) >= SEG_CAP: break
                entry["anchor_rule"] = "row<行号>（第 1 行为表头）"
            elif ext in (".docx", ".doc"):
                lines = extract_docx(path)
                if not lines:
                    entry.update(status="unreadable", note="docx 文本提取失败")
                else:
                    with open(os.path.join(text_dir, f"{mat_id}.txt"), "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    segs = index_text_lines(lines, mat_id, page_aware=False)
                    entry["anchor_rule"] = "l<起行>-<止行>（docx 提取段落）"
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                entry.update(status="image", note="图片材料：正文引用其内容前需人工/OCR 看图确认，不得臆测图中数值")
            elif ext in (".xlsx", ".xls"):
                entry.update(status="unreadable",
                             note="Excel 材料：请用 python3(openpyxl/pandas) 或 libreoffice --convert-to csv 转出后重跑索引")
            else:
                entry.update(status="skipped", note="未支持的类型")
        except Exception as e:
            entry.update(status="error", note=str(e)[:200])
        entry["n_segments"] = len(segs)
        index.append({"entry": entry, "segments": segs})

        # digest
        if entry["status"] == "ok" and segs:
            head = f"\n### {mat_id} `{entry['path']}`（{len(segs)} 段，锚点 {entry['anchor_rule']}）\n"
            body, bcap = [], PER_MATERIAL_CAP
            for s in segs:
                line = f"[{s['seg_id']}] {s['text'][:300]}\n"
                if sum(len(x) for x in body) + len(line) > bcap:
                    body.append(f"...（其余 {len(segs)-len(body)} 段见 /app/work/text/{mat_id}.txt）\n")
                    break
                body.append(line)
            part = head + "".join(body)
            if used + len(part) > DIGEST_BUDGET:
                part = head + "（digest 预算耗尽，全文见 /app/work/text/ 下对应文件）\n"
            digest_parts.append(part)
            used += len(part)
        else:
            digest_parts.append(f"\n### {mat_id} `{entry['path']}` — {entry['status']}: {entry['note']}\n")

    out_index = [{"material_id": x["entry"]["material_id"], **{k: v for k, v in x["entry"].items() if k != "material_id"},
                  "segments": x["segments"]} for x in index]
    with open(os.path.join(args.work, "material_index.json"), "w", encoding="utf-8") as f:
        json.dump(out_index, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "materials_digest.md"), "w", encoding="utf-8") as f:
        f.write(f"# 材料摘要（自动生成 {datetime.datetime.utcnow().isoformat()}Z）\n")
        f.write("锚点格式见各材料行；引用事实时记录 seg_id。全文在 /app/work/text/<Mxx>.txt。\n")
        f.write("".join(digest_parts))

    log = os.path.join(args.out, "run_log.md")
    try:
        with open(log, "a", encoding="utf-8") as f:
            ok = sum(1 for x in out_index if x["status"] == "ok")
            f.write(f"\n## build_material_index {datetime.datetime.utcnow().isoformat()}Z\n")
            f.write(f"- materials={len(out_index)}, ok={ok}, "
                    f"unreadable={sum(1 for x in out_index if x['status'] in ('unreadable','error'))}\n")
            for x in out_index:
                if x["status"] != "ok":
                    f.write(f"- {x['material_id']} {x['path']}: {x['status']} {x['note']}\n")
    except Exception:
        pass
    print(json.dumps({"ok": True, "materials": len(out_index),
                      "statuses": {x["material_id"]: x["status"] for x in out_index}},
                     ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
