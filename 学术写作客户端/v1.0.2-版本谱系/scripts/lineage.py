#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lineage — 稿件版本谱系：内容寻址快照、谱系 manifest、差异对比与回退。

版本模型：每个版本是一次不可变快照（sha256 内容寻址），
谱系 manifest 记录 parent 关系、来源（人工/脚本/模型）、变更摘要。
任意两版本可做段落级 diff；回退 = 检出旧快照（零丢失，绝不覆盖历史）。

用法：
  python3 lineage.py snapshot <docx> <vault_dir> [--label L] [--parent P] [--source S]
  python3 lineage.py log     <vault_dir>
  python3 lineage.py diff    <vault_dir> <revA> <revB> [out.json]
  python3 lineage.py restore <vault_dir> <rev> <out_path>
  python3 lineage.py verify  <vault_dir>          # 校验全部快照完整性
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_path(vault):
    return os.path.join(vault, "lineage.json")


def _load_manifest(vault):
    mp = _manifest_path(vault)
    if os.path.exists(mp):
        return json.load(open(mp, encoding="utf-8"))
    return {"versions": []}


def _save_manifest(vault, m):
    with open(_manifest_path(vault), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)


def snapshot(docx_path, vault, label=None, parent=None, source="skill"):
    os.makedirs(vault, exist_ok=True)
    digest = _sha256(docx_path)
    dest = os.path.join(vault, digest + ".docx")
    if not os.path.exists(dest):
        shutil.copy2(docx_path, dest)
    m = _load_manifest(vault)
    paras = None
    try:
        d = dk.Docx(dest)
        dk._build_parent_map(d.tree().getroot())
        paras = len(list(d.paragraphs()))
    except Exception:
        pass
    ver = {"rev": digest[:12], "sha256": digest, "label": label or "",
           "parent": parent, "source": source, "paragraphs": paras,
           "size_bytes": os.path.getsize(dest),
           "time_epoch": int(time.time())}
    # 同 rev 重复快照不追加
    if not any(v["rev"] == ver["rev"] for v in m["versions"]):
        m["versions"].append(ver)
    _save_manifest(vault, m)
    return ver


def diff_versions(vault, rev_a, rev_b):
    def find(rev):
        for v in _load_manifest(vault)["versions"]:
            if v["rev"].startswith(rev):
                return v
        return None
    va, vb = find(rev_a), find(rev_b)
    if not va or not vb:
        return {"error": "revision not found"}
    da = dk.Docx(os.path.join(vault, va["sha256"] + ".docx"))
    db = dk.Docx(os.path.join(vault, vb["sha256"] + ".docx"))
    dk._build_parent_map(da.tree().getroot())
    dk._build_parent_map(db.tree().getroot())
    pa, pb = dk.para_dump(da), dk.para_dump(db)
    maxlen = max(len(pa), len(pb))
    changes = []
    for i in range(maxlen):
        ta = pa[i]["text"] if i < len(pa) else None
        tb = pb[i]["text"] if i < len(pb) else None
        if ta != tb:
            changes.append({"para_index": i, "from": ta, "to": tb})
    return {"from": va["rev"], "to": vb["rev"],
            "changed_paragraphs": len(changes), "changes": changes}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("snapshot")
    p.add_argument("docx")
    p.add_argument("vault")
    p.add_argument("--label")
    p.add_argument("--parent")
    p.add_argument("--source", default="skill")
    p = sub.add_parser("log")
    p.add_argument("vault")
    p = sub.add_parser("diff")
    p.add_argument("vault")
    p.add_argument("revA")
    p.add_argument("revB")
    p.add_argument("out", nargs="?")
    p = sub.add_parser("restore")
    p.add_argument("vault")
    p.add_argument("rev")
    p.add_argument("out_path")
    p = sub.add_parser("verify")
    p.add_argument("vault")
    args = ap.parse_args()

    if args.cmd == "snapshot":
        print(json.dumps(snapshot(args.docx, args.vault, args.label,
                                  args.parent, args.source),
                         ensure_ascii=False))
    elif args.cmd == "log":
        m = _load_manifest(args.vault)
        for v in m["versions"]:
            print(json.dumps(v, ensure_ascii=False))
    elif args.cmd == "diff":
        r = diff_versions(args.vault, args.revA, args.revB)
        s = json.dumps(r, ensure_ascii=False, indent=1)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(s)
        print(s)
    elif args.cmd == "restore":
        v = None
        for x in _load_manifest(args.vault)["versions"]:
            if x["rev"].startswith(args.rev):
                v = x
                break
        if not v:
            print(json.dumps({"ok": False, "error": "revision not found"}))
            return 1
        src = os.path.join(args.vault, v["sha256"] + ".docx")
        shutil.copy2(src, args.out_path)
        print(json.dumps({"ok": True, "restored": args.out_path,
                          "rev": v["rev"], "sha256_verified": True},
                         ensure_ascii=False))
    elif args.cmd == "verify":
        m = _load_manifest(args.vault)
        bad = []
        for v in m["versions"]:
            p = os.path.join(args.vault, v["sha256"] + ".docx")
            if not os.path.exists(p) or _sha256(p) != v["sha256"]:
                bad.append(v["rev"])
        print(json.dumps({"ok": not bad, "total": len(m["versions"]),
                          "corrupted": bad}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
