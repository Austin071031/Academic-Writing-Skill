#!/usr/bin/env python3
"""v5_build_manifest.py — 可重复构建清单：引擎/宏包版本、源码哈希、精确编译命令。

用法:
  python3 v5_build_manifest.py [--project /app/work/project] [--work /app/work]
                               [--engine auto] [--main main.tex]

输出:
  work/build_manifest.json  — 机读清单
  work/BUILD_MANIFEST.md    — 人读复现说明（环境、命令、轮次、版本、哈希、已知差异点）
版本信息来自 `<engine> --version` 与编译日志中的 "Package: <name> <date> <ver>" 行；
取不到版本就写 "unknown" 并说明来源缺失，不编造版本号。仅标准库。
"""
import argparse, hashlib, json, os, platform, re, subprocess, sys, datetime


def sha256_of(path, limit=2 * 1024 * 1024):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(limit))
        return h.hexdigest()[:16]
    except OSError:
        return None


def tool_version(cmd):
    try:
        p = subprocess.run([cmd, "--version"], timeout=15, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        first = p.stdout.decode("utf-8", "replace").splitlines()
        return first[0].strip() if first else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return None


def parse_log_packages(log_path):
    pkgs = {}
    if not log_path or not os.path.exists(log_path):
        return pkgs
    txt = open(log_path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"Package:\s+(\S+)\s+([0-9]{4}/[0-9]{2}/[0-9]{2}[^\s]*)\s*(.*)", txt):
        pkgs[m.group(1)] = (m.group(2) + " " + m.group(3)).strip()[:80]
    for m in re.finditer(r"Document Class:\s+(\S+)\s+(\S[^\n]*)", txt):
        pkgs["class:" + m.group(1)] = m.group(2).strip()[:80]
    return pkgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--engine", default=None)
    ap.add_argument("--main", default=None)
    args = ap.parse_args()

    insp = {}
    try:
        insp = json.load(open(os.path.join(args.work, "inspection.json"), encoding="utf-8"))
    except Exception:
        pass
    build = {}
    try:
        build = json.load(open(os.path.join(args.work, "build_report.json"), encoding="utf-8"))
    except Exception:
        pass
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"
    engine = args.engine or build.get("engine") or (insp.get("tex_project") or {}).get("engine")

    files = {}
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.startswith(".") or fn.endswith((".aux", ".log", ".out", ".toc", ".pdf",
                                                  ".bak", ".synctex.gz")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, project)
            files[rel] = {"sha256_16": sha256_of(p), "size": os.path.getsize(p)}

    versions = {}
    for tool in filter(None, {engine, "bibtex", "biber", "latexmk"}):
        v = tool_version(tool)
        if v:
            versions[tool] = v
    log_pkgs = parse_log_packages(build.get("log"))

    manifest = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {"os": platform.platform(), "python": platform.python_version()},
        "engine": engine,
        "tool_versions": versions,
        "package_versions_from_log": log_pkgs,
        "package_versions_note": "取自最近一次编译日志；空表表示日志不可得或格式不含版本行",
        "main": main_rel,
        "source_files": files,
        "commands": build.get("commands", []),
        "passes": build.get("passes", []),
        "build_success": build.get("success"),
        "converged": build.get("converged"),
    }
    json.dump(manifest, open(os.path.join(args.work, "build_manifest.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=2)

    md = ["# 构建清单（BUILD MANIFEST）", "",
          f"- 生成时间（UTC）: {manifest['generated_at']}",
          f"- 主文件: `{main_rel}`　引擎: `{engine}`",
          f"- 编译成功: {build.get('success')}　交叉引用收敛: {build.get('converged')}",
          "", "## 环境", f"- OS: {manifest['platform']['os']}"]
    for t, v in versions.items():
        md.append(f"- {t}: {v}")
    md += ["", "## 复现命令（按序执行）", "```sh"]
    md += manifest["commands"] or ["（无记录——请先运行 tex_build.py）"]
    md += ["```", "", "## 宏包/文档类版本（来自编译日志）"]
    if log_pkgs:
        for k, v in sorted(log_pkgs.items()):
            md.append(f"- {k}: {v}")
    else:
        md.append("- （日志中未解析到版本行；以 TeX Live 发行版整体版本为准）")
    md += ["", "## 源码文件哈希（sha256 前 16 位）"]
    for rel, meta in sorted(files.items()):
        md.append(f"- `{rel}`　{meta['sha256_16']}　{meta['size']}B")
    md += ["", "## 复现注意",
           "- 同一 TeX Live 年度版本与相同命令序列应得到一致 PDF；宏包版本不同可能导致"
           "分页与排版差异，属可解释差异而非内容差异。",
           "- 若使用 latexmk：`latexmk -pdf`（或 `-xelatex`）等价于上列命令序列的自动化。"]
    open(os.path.join(args.work, "BUILD_MANIFEST.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"[manifest] 引擎={engine} 工具版本={len(versions)} 宏包版本={len(log_pkgs)} "
          f"源文件={len(files)} 命令={len(manifest['commands'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
