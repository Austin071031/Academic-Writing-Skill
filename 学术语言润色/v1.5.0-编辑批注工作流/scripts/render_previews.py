#!/usr/bin/env python3
"""render_previews.py — 生成可检视预览：HTML 必出；PDF/PNG 仅在找到可用字体时生成。

用法: python3 render_previews.py [--output-dir /app/output]

有 CJK 文本却无 CJK 字体时，PDF/PNG 会缺字，此时只产出 HTML 并在报告中如实说明，
不生成缺字预览冒充成功。matplotlib 为可选依赖，缺失时自动降级。
"""
import argparse, json, os, re, shutil, subprocess, sys

CJK_RE = re.compile(r"[一-鿿぀-ヿ가-힯]")


def find_cjk_font():
    """用 fc-list 找 CJK 字体；返回字体路径或 None。"""
    if not shutil.which("fc-list"):
        return None
    try:
        r = subprocess.run(["fc-list", ":lang=zh", "file"], capture_output=True, timeout=30)
        for line in r.stdout.decode("utf-8", errors="replace").splitlines():
            path = line.split(":")[0].strip()
            if path and os.path.exists(path):
                return path
    except Exception:
        pass
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/arphic/uming.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()
    outdir = args.output_dir

    md_path = os.path.join(outdir, "polished_full.md")
    if not os.path.exists(md_path):
        print("[render_previews] polished_full.md 不存在，跳过预览生成")
        return 0
    text = open(md_path, encoding="utf-8").read()
    has_cjk = bool(CJK_RE.search(text))

    note = {"html": ["diff.html", "polished_full.html"], "pdf": None, "png": None}
    font = find_cjk_font()
    if has_cjk and font is None:
        note["font_warning"] = ("环境无 CJK 字体，PDF/PNG 预览会缺字，仅生成 HTML 预览"
                                "（HTML 由浏览器自带字体渲染，不受影响）")
    else:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib import font_manager
            from matplotlib.backends.backend_pdf import PdfPages
            if font:
                font_manager.fontManager.addfont(font)
                fam = font_manager.FontProperties(fname=font).get_name()
                plt.rcParams["font.family"] = fam
            plt.rcParams["axes.unicode_minus"] = False

            lines, page = [], []
            for para in text.split("\n"):
                while len(para) > 72:
                    page.append(para[:72])
                    para = para[72:]
                page.append(para)
                page.append("")
            pages = [page[i:i + 38] for i in range(0, len(page), 38)] or [[]]
            pdf_path = os.path.join(outdir, "preview_polished.pdf")
            with PdfPages(pdf_path) as pdf:
                for i, pg in enumerate(pages[:6]):
                    fig = plt.figure(figsize=(8.27, 11.69))
                    fig.text(0.08, 0.96, f"润色后全文预览 第 {i+1}/{min(len(pages),6)} 页",
                             fontsize=10, va="top")
                    fig.text(0.08, 0.92, "\n".join(pg), fontsize=10, va="top", wrap=True)
                    pdf.savefig(fig)
                    plt.close(fig)
            note["pdf"] = "preview_polished.pdf"
            if shutil.which("pdftoppm"):
                subprocess.run(["pdftoppm", "-png", "-f", "1", "-singlefile",
                                pdf_path, os.path.join(outdir, "preview_polished")],
                               capture_output=True, timeout=60)
                if os.path.exists(os.path.join(outdir, "preview_polished.png")):
                    note["png"] = "preview_polished.png"
        except Exception as e:
            note["font_warning"] = f"PDF/PNG 预览生成失败（{e}），保留 HTML 预览"

    rep_p = os.path.join(outdir, "preview_report.json")
    json.dump(note, open(rep_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[render_previews] {json.dumps(note, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
