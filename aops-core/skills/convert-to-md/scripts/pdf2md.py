#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import tempfile
import sys


def have(cmd):
    return shutil.which(cmd) is not None


def run(cmd, **kw):
    r = subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description="PDF → Markdown via pdfminer.six + Pandoc")
    ap.add_argument("pdf")
    ap.add_argument("md", nargs="?", help="Output .md (default: input.md)")
    ap.add_argument("--pandoc-format", default="gfm")
    args = ap.parse_args()

    pdf = args.pdf
    if not os.path.exists(pdf):
        sys.exit(f"Input not found: {pdf}")
    md = args.md or os.path.splitext(pdf)[0] + ".md"

    pdf2txt = "pdf2txt.py"
    if not have(pdf2txt):
        if have("pdf2txt"):
            pdf2txt = "pdf2txt"
        else:
            sys.exit("pdf2txt.py not found (install pdfminer.six)")

    if not have("pandoc"):
        sys.exit("pandoc not found")

    with tempfile.TemporaryDirectory() as td:
        layout_html = os.path.join(td, "layout.html")
        simple_html = os.path.join(td, "simple.html")
        layout_md = os.path.join(td, "layout.md")
        simple_md = os.path.join(td, "simple.md")

        # Two passes with different LAParams sensitivities
        with open(layout_html, "w") as f:
            subprocess.run(
                [pdf2txt, "-t", "html", "-A", "-S", pdf],
                check=True,
                text=True,
                stdout=f,
            )
        with open(simple_html, "w") as f:
            subprocess.run(
                [pdf2txt, "-t", "html", "-S", pdf],
                check=True,
                text=True,
                stdout=f,
            )

        # Light page split heuristics
        for f in (layout_html, simple_html):
            with open(f, "r", encoding="utf-8") as r:
                h = r.read()
            out = []
            first = True
            for line in h.splitlines():
                if 'class="page"' in line and not first:
                    out.append("<hr/>")
                if 'class="page"' in line:
                    first = False
                out.append(line)
            with open(f, "w", encoding="utf-8") as w:
                w.write("\n".join(out))

        # Heuristic: strip raw HTML for markdown outputs to avoid div soup from pdfminer
        pandoc_fmt = args.pandoc_format
        if (
            any(x in pandoc_fmt for x in ("gfm", "markdown", "commonmark"))
            and "raw_html" not in pandoc_fmt
        ):
            pandoc_fmt += "-raw_html"

        subprocess.run(
            [
                "pandoc",
                "--from=html",
                f"--to={pandoc_fmt}",
                "--wrap=none",
                "-o",
                layout_md,
                layout_html,
            ],
            check=True,
        )
        subprocess.run(
            [
                "pandoc",
                "--from=html",
                f"--to={pandoc_fmt}",
                "--wrap=none",
                "-o",
                simple_md,
                simple_html,
            ],
            check=True,
        )

        def density(p):
            with open(p, "r", encoding="utf-8") as r:
                return len("".join(r.read().split()))

        best = layout_md if density(layout_md) >= density(simple_md) else simple_md
        shutil.copyfile(best, md)

    print(f"✅ Wrote {md}")


if __name__ == "__main__":
    main()
