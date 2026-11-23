#!/usr/bin/env python3
"""claims_check.py — 主张矩阵机读复核：回译验证循环的落地闸门。

用法: python3 claims_check.py [--work-dir /app/work]

检查:
  1. 每个 decision=modify 的关键句（源标记 key=true）必须有 claims 字段，
     且 reason 含"回译一致"标记（阶段3 的回译结论），否则 critical。
  2. claims 的 numbers/units/citations/pointers 格与原文机读抽取逐格比对，
     不一致 critical（可交 resolutions.jsonl 处置）。
  3. claims.hedging 的档位（强/中/弱）与原文限定词档位一致性核对。
输出: claims_report.json / claims_report.md；exit 1 表示存在 critical。
"""
import argparse, glob, json, os, re, sys
from collections import Counter

UNITS = r"%|°C|℃|nm|μm|µm|um|mm|cm|m|km|mg|g|kg|mL|L|mol|s|ms|μs|min|h|Hz|kHz|MHz|eV|keV|MeV|V|mV|kV|W|J|kJ|rpm|dB|ppb|ppm"
RE_NUM = re.compile(rf"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:\\?\s*(?:{UNITS}))?")
RE_CITE = re.compile(r"\[[0-9]+(?:\s*[-–,，]\s*[0-9]+)*\]|\\cite[tp]?\*?(?:\[[^\]]*\])?\{[^}]*\}")
RE_PTR = re.compile(r"(?:图|表|插图|算法|式|公式|Figure|Fig\.?|Table|Tab\.?|Algorithm|Eq\.?|"
                    r"Equation|Section|Sec\.?)\s*(?:[0-9]+(?:\.[0-9]+)?)")
TIER = {"强": 0, "中": 1, "弱": 2}
RE_TIER = re.compile(r"（(强|中|弱)档")


def machine_extract(text):
    cites = sorted(RE_CITE.findall(text))
    # 数字抽取前先剔除引用片段，避免 [2] 中的 2 被误计为数值
    masked = RE_CITE.sub(" ", text)
    return {"numbers": sorted(RE_NUM.findall(masked)), "citations": cites,
            "pointers": sorted(RE_PTR.findall(text))}


def diff(a, b):
    ca, cb = Counter(a), Counter(b)
    return sorted((ca - cb).elements()), sorted((cb - ca).elements())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    args = ap.parse_args()
    wd = args.work_dir

    src, key_ids = {}, {}
    for seg in json.load(open(os.path.join(wd, "source_segments.json"), encoding="utf-8")):
        if seg.get("kind") in ("heading", "math", "fence"):
            continue
        sents, keys = seg.get("sentences") or [], seg.get("keys") or []
        for i, s in enumerate(sents, 1):
            sid = f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"]
            src[sid] = s
            key_ids[sid] = keys[i - 1] if i - 1 < len(keys) else False

    resolutions = set()
    rp = os.path.join(wd, "resolutions.jsonl")
    if os.path.exists(rp):
        for line in open(rp, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    resolutions.add((r.get("flag_id"), r.get("kind")))
                except json.JSONDecodeError:
                    pass

    flags, n_mod, n_key_mod, n_bt = [], 0, 0, 0
    seen = set()
    for p in sorted(glob.glob(os.path.join(wd, "polish_chunks", "*.jsonl"))):
        for ln, line in enumerate(open(p, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            tag = f"{os.path.basename(p)}:{ln}"
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                flags.append({"level": "critical", "kind": "parse", "id": tag,
                              "issue": "chunk 行不是合法 JSON"})
                continue
            sid = e.get("id")
            if not sid:
                flags.append({"level": "critical", "kind": "schema", "id": tag, "issue": "缺 id"})
                continue
            seen.add(sid)
            if e.get("decision") != "modify":
                continue
            n_mod += 1
            is_key = key_ids.get(sid, False)
            reason = e.get("reason", "")
            back_translated = "回译一致" in reason or "回译通过" in reason
            if is_key:
                n_key_mod += 1
                if not back_translated:
                    flags.append({"level": "critical", "kind": "backtranslation", "id": sid,
                                  "issue": "关键句 modify 但未标注回译结论（reason 需含“回译一致”）"})
                else:
                    n_bt += 1
            # claims 矩阵逐格复核
            claims = e.get("claims")
            orig = e.get("original") or src.get(sid, "")
            mo = machine_extract(orig)
            if is_key and claims is None:
                flags.append({"level": "critical", "kind": "claims", "id": sid,
                              "issue": "关键句 modify 缺 claims 主张矩阵"})
                continue
            if claims:
                for field in ("numbers", "citations", "pointers"):
                    stated = re.findall(r"\d+(?:\.\d+)?\\?\s*(?:" + UNITS + r")?|\[[^\]]+\]|"
                                        r"(?:图|表|Figure|Fig\.?|Table|Eq\.?)\s*\d+",
                                        str(claims.get(field, "")))
                    r_, a_ = diff(mo[field], [s for s in stated if s in mo[field] or s])
                    stated_set = Counter(s for s in stated)
                    machine_set = Counter(mo[field])
                    if stated_set != machine_set and (sid, f"claims_{field}") not in resolutions:
                        flags.append({"level": "critical", "kind": f"claims_{field}", "id": sid,
                                      "issue": f"claims.{field} 与原文机读不一致: "
                                               f"机读={mo[field][:6]} 矩阵={list(stated)[:6]}"})
                ht = claims.get("hedging", "")
                m = RE_TIER.search(str(ht))
                if m:
                    low = orig.lower()
                    tier_now = None
                    for t, lex in (("强", ["证明", "证实", "必然", "肯定", "毫无疑问",
                                          "prove", "confirm", "definitively", "establish", "must"]),
                                   ("中", ["表明", "显示", "说明", "揭示", "suggest", "indicate",
                                          "show", "demonstrate", "reveal", "support",
                                          "consistent with"]),
                                   ("弱", ["可能", "或许", "有望", "提示", "初步", "约", "大致",
                                          "may", "might", "could", "possibly", "potentially",
                                          "likely", "appear", "seem", "tend", "preliminary",
                                          "approximately", "roughly", "partially"])):
                        if any(w in low for w in lex):
                            tier_now = t
                            break
                    if tier_now and m.group(1) != tier_now and (sid, "claims_hedging") not in resolutions:
                        flags.append({"level": "critical", "kind": "claims_hedging", "id": sid,
                                      "issue": f"claims.hedging 记为{m.group(1)}档，原文实为{tier_now}档"})

    coverage = sorted(set(src) - seen)
    rep = {"source_sentences": len(src), "logged": len(seen),
           "coverage_ratio": round((len(src) - len(coverage)) / max(len(src), 1), 4),
           "modify": n_mod, "key_modify": n_key_mod, "backtranslated_ok": n_bt,
           "unlogged_ids": coverage[:100],
           "flags": [f for f in flags if (f.get("id"), f["kind"]) not in resolutions],
           "critical": sum(1 for f in flags
                          if f["level"] == "critical" and (f.get("id"), f["kind"]) not in resolutions)}
    json.dump(rep, open(os.path.join(wd, "claims_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(wd, "claims_report.md"), "w", encoding="utf-8") as f:
        f.write("# 主张矩阵复核报告（claims_check.py）\n\n")
        f.write(f"源句 {rep['source_sentences']}，已记录 {rep['logged']}，覆盖率 "
                f"{rep['coverage_ratio']:.1%}；modify {n_mod}（关键句 {n_key_mod}，回译通过 {n_bt}）。\n\n")
        for x in rep["flags"]:
            f.write(f"- **[{x['level']}/{x['kind']}]** `{x.get('id')}` {x['issue']}\n")
        if not rep["flags"]:
            f.write("- 全部通过：关键句回译留痕齐备，claims 矩阵与机读一致。\n")
    print(f"[claims_check] modify={n_mod} key_modify={n_key_mod} bt_ok={n_bt} "
          f"coverage={rep['coverage_ratio']:.1%} critical={rep['critical']}")
    return 1 if rep["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
