#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""题面指令原子化与成稿落实审计（v2.0.0 增量）。
把 task.md/case.json 中的原子约束拆成机读清单（/app/work/instruction_checklist.json），
并在成稿生成后逐条审计（/app/output/draft_audit.json）：
  硬约束（error 级）：篇幅下限、语言；
  软约束（warning 级）：必含项关键词覆盖、体裁结构（读 references/genre_profiles.md）。
体裁档案路径取自 direction.json 的 genre_profiles 字段（参数真被读取）。
用法: python3 instruction_audit.py [INPUT] [WORK] [OUTPUT] [SKILL_DIR]
"""
import json, os, re, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "/app/output"
SKILL = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_genre_profiles(path):
    profiles, cur = {}, None
    if not os.path.exists(path):
        return profiles
    for line in open(path, encoding="utf-8"):
        line = line.rstrip()
        m = re.match(r"^##\s+(.+)", line)
        if m:
            cur = m.group(1).strip()
            profiles[cur] = {"required_keywords": [], "structure": ""}
            continue
        if cur and line.startswith("required_keywords:"):
            groups = [g.strip() for g in line.split(":", 1)[1].split(",") if g.strip()]
            profiles[cur]["required_keywords"] = [[w.strip() for w in g.split("|")] for g in groups]
        elif cur and line.startswith("structure:"):
            profiles[cur]["structure"] = line.split(":", 1)[1].strip()
    return profiles

task = ""
for p in (os.path.join(INPUT, "task.md"), os.path.join(INPUT, "case.json")):
    if os.path.exists(p):
        task += "\n" + open(p, encoding="utf-8", errors="replace").read()

instructions = []
for m in re.finditer(r"(不少于|至少|不低于|不超过|至多)\s*(\d+)\s*(字|词|words?|characters?)", task, re.I):
    kind = "min_words" if m.group(1) in ("不少于", "至少", "不低于") else "max_words"
    instructions.append({"id": "I_len_%d" % len(instructions), "type": kind,
                         "value": int(m.group(2)), "unit": "chars" if "字" in m.group(0) else "words",
                         "text": m.group(0), "required": True})
m = re.search(r"受众[为是][:：]?\s*([^\s，。；（）]+)", task) or re.search(r"面向([^\s，。；（）]+)", task)
if m:
    instructions.append({"id": "I_audience", "type": "audience", "value": m.group(1),
                         "text": m.group(0), "required": False})
genre = None
m = re.search(r"体裁[:：]\s*([^\s，。（）\n]{2,12})", task)
if m:
    genre = m.group(1).strip()
    instructions.append({"id": "I_genre", "type": "genre", "value": genre, "text": m.group(0), "required": False})
for m in re.finditer(r"(须包含|须含|需包含|必须包含|须列出|需列出|应包含|须涵盖)([^，,。；\n]{2,80})", task):
    body = m.group(2).strip("，,。 ")
    for it in re.split(r"[、，,]|(?:\s*(?:和|与|及)\s*)", body):
        it = it.strip()
        if it:
            instructions.append({"id": "I_req_%d" % len(instructions), "type": "required_item",
                                 "value": it, "text": m.group(1) + it, "required": True})
if re.search(r"中英双语|双语", task):
    instructions.append({"id": "I_lang", "type": "language", "value": "bilingual", "text": "双语", "required": True})
elif re.search(r"英文(摘要|写作|撰写|成稿)", task):
    instructions.append({"id": "I_lang", "type": "language", "value": "en", "text": "英文", "required": True})
elif re.search(r"中文", task):
    instructions.append({"id": "I_lang", "type": "language", "value": "zh", "text": "中文", "required": False})

dp = os.path.join(OUTPUT, "draft.md")
draft = open(dp, encoding="utf-8").read() if os.path.exists(dp) else ""
cjk = len(re.findall(r"[\u4e00-\u9fff]", draft))
words = len(re.findall(r"[A-Za-z]+", draft))
nons = len(re.sub(r"\s", "", draft))

report = {"genre": genre, "draft_present": bool(draft), "instructions": [], "genre_checks": []}
for ins in instructions:
    passed, detail = None, ""
    if not draft:
        detail = "draft.md 尚未生成"
    elif ins["type"] == "min_words":
        n = nons if ins["unit"] == "chars" else words
        passed = n >= ins["value"]
        detail = "实际 %d / 要求 ≥%d" % (n, ins["value"])
    elif ins["type"] == "max_words":
        n = nons if ins["unit"] == "chars" else words
        passed = n <= ins["value"]
        detail = "实际 %d / 要求 ≤%d" % (n, ins["value"])
    elif ins["type"] == "required_item":
        keys = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", ins["value"])
        variants = []
        for k in keys:
            variants.append(k)
            k2 = re.sub(r"(数据|表述|情况|问题|效果|指标|信息|内容|分析|讨论|建议|结果|记录)$", "", k)
            if len(k2) >= 2 and k2 != k:
                variants.append(k2)
        hit = [k for k in variants if k in draft]
        passed = bool(hit) if keys else None
        detail = "必含项关键词命中: %s" % ("、".join(hit) if hit else "无（疑似未覆盖）")
    elif ins["type"] == "language":
        if ins["value"] == "zh":
            passed = cjk > words
        elif ins["value"] == "en":
            passed = words > cjk * 2
        else:
            passed = cjk > 10 and words > 10
        detail = "CJK %d / EN %d" % (cjk, words)
    else:
        detail = "由体裁档案与写作决策保障"
    report["instructions"].append(dict(ins, passed=passed, detail=detail))

dcfg = {}
dj = os.path.join(SKILL, "direction.json")
if os.path.exists(dj):
    try:
        dcfg = json.load(open(dj, encoding="utf-8"))
    except Exception:
        pass
profiles = load_genre_profiles(os.path.join(SKILL, dcfg.get("genre_profiles", "references/genre_profiles.md")))
if genre and genre in profiles and draft:
    for group in profiles[genre]["required_keywords"]:
        hit = any(w in draft for w in group)
        report["genre_checks"].append({"check": "关键词组 " + "|".join(group), "passed": hit,
                                       "detail": "命中" if hit else "未命中"})
    report["genre_structure"] = profiles[genre]["structure"]
elif genre and genre not in profiles:
    report["genre_checks"].append({"check": "体裁档案", "passed": None,
                                   "detail": "体裁 %r 无档案，按通用结构处理" % genre})

os.makedirs(WORK, exist_ok=True)
with open(os.path.join(WORK, "instruction_checklist.json"), "w", encoding="utf-8") as f:
    json.dump({"instructions": instructions, "genre": genre, "source": "task.md+case.json"}, f,
              ensure_ascii=False, indent=1)
if draft:
    with open(os.path.join(OUTPUT, "draft_audit.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
print(json.dumps({"instructions": len(instructions), "genre": genre,
                  "genre_profile_hit": genre in profiles if genre else None,
                  "audited": bool(draft)}, ensure_ascii=False))
