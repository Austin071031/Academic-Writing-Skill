#!/usr/bin/env python3
"""extract_evidence.py — 从文本化材料中抽取方法/实验要素候选，生成证据台账草稿。

用法: python3 extract_evidence.py [--work /app/work]
输入: work/inspection.json（inspect_case.py 产物）与 work/text/*.pages.txt
输出: work/evidence_candidates.jsonl —— 每行 {eid, source, locator, kind, name, value, quote}
      work/value_index.json —— name -> {value: [eid,...]}（供跨源一致性比对）
只依赖标准库；抽取是"候选"，采信与否由 Agent 依据 references/ 规则裁决。
"""
import json, os, re, sys, argparse

PATTERNS = [
    ("seed", re.compile(r"\b(seed|random_state|random-state|randomseed)\b\s*[:=]?\s*(\d{1,10})", re.I)),
    ("hyperparam", re.compile(r"\b(learning_rate|lr|batch_size|batchsize|epochs?|max_steps?|warmup_steps?|weight_decay|dropout|hidden_size|num_layers|max_seq_len|context_length|temperature|top_p|beta[12]?|epsilon|grad_clip|clip_grad|momentum|n_estimators|max_depth)\b\s*(?:[:=]|set\s+to)\s*([-\d\.eE+]+)", re.I)),
    ("code_default", re.compile(r"add_argument\(\s*\"--([\w\-]+)\"[^)]*?default\s*=\s*([-\d\.eE]+)", re.I)),
    ("code_assign", re.compile(r"^\s*([A-Za-z_][\w\-]{2,30})\s*=\s*([-\d\.eE+]{1,20})\s*(#.*)?$")),
    ("size", re.compile(r"(\d+(?:\.\d+)?)\s*(%|GB|MB|TB|ms|s|min|h|epochs?|k|M|B|Hz|W|V|K|°C|g|mg|mL|L|nm|μm|um|mm|cm|m)\b")),
    ("split", re.compile(r"\b(train|training|val|valid|validation|dev|test|testset)\b[\w\s\-]*[:=]\s*(\d+(?:\.\d+)?)\s*(%)?", re.I)),
    ("dataset", re.compile(r"\b(dataset|datasets|corpus|benchmark|数据集)\b\s*[:=]?\s*[\"']?([\w\-\./ ]{2,60}?)[\"']?[\s,;\)\n]", re.I)),
    ("hardware", re.compile(r"\b(A100|H100|V100|A10|A40|T4|P100|RTX\s?\d{4}|Tesla\s?\w+|TPU\s?v?\d*|GPU|CPU)\b\s*([x×]\s*\d+|\d+\s*张|\d+\s*cards?)?", re.I)),
    ("version", re.compile(r"\b(python|cuda|cudnn|pytorch|torch|tensorflow|numpy|scipy|scikit-learn|sklearn|transformers|accelerate|deepspeed|vllm)\b\s*[=:]?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", re.I)),
    ("requirement", re.compile(r"^\s*([a-zA-Z0-9_\-]+)\s*==\s*([0-9][0-9a-zA-Z\.\-]*)", re.M)),
    ("url", re.compile(r"(https?://[^\s\"'）)]+|doi:\s*10\.\d{4,9}/[^\s\"'）)]+|10\.\d{4,9}/[A-Za-z0-9_\.;/()\-]+)")),
    ("env_var", re.compile(r"\b(CUDA_VISIBLE_DEVICES|WORLD_SIZE|RANK|MASTER_(ADDR|PORT))\b\s*=\s*(\S+)")),
    ("command", re.compile(r"^\s*\$\s*(.+)$|^\s*(python3?|torchrun|accelerate|bash|sh)\s+([^\n]{5,200})$", re.M)),
]

PAGE_MARK = re.compile(r"^===== PAGE (\d+) =====$", re.M)

def locator_for(lines, i):
    page = None
    for j in range(i, -1, -1):
        m = PAGE_MARK.match(lines[j])
        if m:
            page = int(m.group(1))
            break
    if page is not None:
        return f"p.{page} 行{i+1}"
    return f"行{i+1}"

def scan_text(source, text, out, vindex, counter, code_like=False):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if len(line) > 400:
            continue
        for kind, pat in PATTERNS:
            if not code_like and kind in ("code_default", "code_assign"):
                continue
            for m in pat.finditer(line):
                if kind == "size":
                    name, value = "数量", m.group(1) + m.group(2)
                elif kind == "command":
                    name, value = "命令", (m.group(1) or (m.group(2) + " " + (m.group(3) or ""))).strip()
                elif kind == "url":
                    name, value = "链接", m.group(1)
                elif kind == "env_var":
                    name, value = m.group(1), m.group(3)
                elif kind == "hardware":
                    name, value = m.group(1), (m.group(2) or "").strip()
                elif kind == "requirement":
                    name, value = m.group(1), m.group(2)
                else:
                    name, value = m.group(1), m.group(2)
                value = str(value).strip().strip(",;\"'")
                if not value:
                    continue
                eid = f"E{counter[0]:04d}"
                counter[0] += 1
                quote = line.strip()[:220]
                rec = {"eid": eid, "source": source, "locator": locator_for(lines, i),
                       "kind": kind, "name": name, "value": value, "quote": quote}
                out.append(rec)
                vindex.setdefault(name.lower(), {}).setdefault(value, []).append(eid)

def read_any(path, limit=400000):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(limit)
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    insp_path = os.path.join(args.work, "inspection.json")
    if not os.path.exists(insp_path):
        print("[extract] 缺 inspection.json，请先运行 inspect_case.py", file=sys.stderr)
        sys.exit(1)
    with open(insp_path, encoding="utf-8") as f:
        insp = json.load(f)

    records, vindex = [], {}
    counter = [1]
    # PDF 文本（论文正文：方法/实验章节事实）
    for pdf in insp.get("materials", {}).get("pdf", []):
        if pdf.get("textified") and pdf.get("text_path"):
            t = read_any(pdf["text_path"])
            if t:
                scan_text(os.path.basename(pdf["rel"]), t, records, vindex, counter)
    # 配置 / 日志 / 代码 / 文档（code/config 启用赋值与 argparse 默认抽取）
    for cls in ("config", "log", "code", "doc"):
        for m in insp.get("materials", {}).get(cls, []):
            t = read_any(m["path"])
            if t:
                scan_text(os.path.basename(m["rel"]), t, records, vindex, counter,
                          code_like=(cls in ("code", "config")))

    out1 = os.path.join(args.work, "evidence_candidates.jsonl")
    with open(out1, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out2 = os.path.join(args.work, "value_index.json")
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(vindex, f, ensure_ascii=False, indent=1)
    multi = {k: v for k, v in vindex.items() if len(v) >= 2}
    print(f"[extract] 候选 {len(records)} 条 -> {out1}; 同名多值参数 {len(multi)} 个 -> {out2}")

if __name__ == "__main__":
    sys.exit(main())
