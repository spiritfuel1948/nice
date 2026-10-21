"""Build the publishable files for The Heart-Thread from the chapter files.

Outputs (in my-series/publishing/):
  The-Heart-Thread.epub                 Kindle / ebook upload
  The-Heart-Thread.docx                 editable copy (KDP also accepts .docx)
  The-Heart-Thread-paperback-5.5x8.5.pdf  print-ready interior for KDP paperback
  book.md                               combined manuscript with front/back matter
Also refreshes my-series/manuscript/Season-1-The-Heart-Thread.md (reading copy).

Needs: pandoc, Node + Playwright (for the PDF).
Usage: python build_book.py
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent
SERIES = GUIDE / "my-series"
MS = SERIES / "manuscript"
OUT = SERIES / "publishing"
OUT.mkdir(exist_ok=True)

TITLE = "The Heart-Thread"
SERIES_LINE = "The Bridgewatch · Book One"
AUTHOR = "Avery Ashcombe"
YEAR = "2026"

PARTS = [
    ("part-1", "Part One: The Burned March"),
    ("part-2", "Part Two: The Hollowwood"),
    ("part-3", "Part Three: The Broken Oath"),
    ("part-4", "Part Four: The Bridge of Dawn"),
]

COPYRIGHT = f"""Copyright © {YEAR} {AUTHOR}. All rights reserved.

This is a work of fiction. Names, characters, places, and incidents are products of the author's imagination or are used fictitiously. Any resemblance to actual persons, living or dead, or to actual events is entirely coincidental.

No part of this book may be reproduced in any form without permission, except for brief quotations in reviews.

First edition, {YEAR}."""

THANKS = f"""Thank you for reading *{TITLE}*.

Maren and Emrys's story continues in **Book Two of The Bridgewatch**.

If you enjoyed this book, please consider leaving a short review on the store where you bought it. Reviews are the single biggest help to a new author. Even a sentence or two makes a real difference."""

ABOUT = f"""{AUTHOR} writes fantasy about oaths, magic, and the people brave enough to break the wrong ones. *{TITLE}* is their first novel."""


def chapters():
    for folder, part in PARTS:
        for f in sorted((MS / folder).glob("ch*.md")):
            text = f.read_text()
            text = re.sub(r"^# Part [^\n]*\n\n", "", text)          # part header lives here instead
            text = re.sub(r"^# (Chapter [^\n]+)", r"## \1", text, count=1, flags=re.M)
            yield part, text.strip()


def combined_markdown():
    out, last = [], None
    for part, text in chapters():
        if part != last:
            out += [f"# {part}", ""]
            last = part
        out += [text, ""]
    return "\n".join(out)


def fetch_fonts():
    """Download EB Garamond (SIL Open Font License) as static TTFs, if missing."""
    fonts = HERE / "fonts"
    fonts.mkdir(exist_ok=True)
    css_out = fonts / "ebgaramond-local.css"
    if css_out.exists() and list(fonts.glob("*.ttf")):
        return
    url = "https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400"
    css = subprocess.run(["curl", "-sS", "-A", "Mozilla/4.0", url], capture_output=True,
                         text=True, check=True).stdout
    faces = []
    for block in re.findall(r"@font-face \{.*?\}", css, re.S):
        style = re.search(r"font-style: (\w+)", block).group(1)
        weight = re.search(r"font-weight: (\d+)", block).group(1)
        src = re.search(r"url\((https://[^)]+)\)", block).group(1)
        name = f"EBGaramond-{weight}-{style}.ttf"
        subprocess.run(["curl", "-sS", "-o", str(fonts / name), src], check=True)
        faces.append(f"@font-face {{ font-family: 'EB Garamond'; font-style: {style}; "
                     f"font-weight: {weight}; src: url({name}) format('truetype'); }}")
    css_out.write_text("\n".join(faces) + "\n")


def build():
    fetch_fonts()
    body = combined_markdown()

    # Reading copy (no front matter), kept in the manuscript folder.
    (MS / "Season-1-The-Heart-Thread.md").write_text(
        f"# {TITLE}\n\n*{SERIES_LINE}* · by {AUTHOR}\n\n---\n\n"
        + body.replace("\n## Chapter", "\n### Chapter").replace("\n# Part", "\n## Part")
    )

    book_md = (
        f"---\ntitle: \"{TITLE}\"\nsubtitle: \"{SERIES_LINE}\"\nauthor: \"{AUTHOR}\"\n"
        f"lang: en-US\nrights: \"© {YEAR} {AUTHOR}. All rights reserved.\"\n---\n\n"
        f"# Copyright {{.unnumbered .unlisted}}\n\n{COPYRIGHT}\n\n"
        f"{body}\n\n"
        f"# Thank You for Reading {{.unnumbered}}\n\n{THANKS}\n\n"
        f"# About the Author {{.unnumbered}}\n\n{ABOUT}\n"
    )
    (OUT / "book.md").write_text(book_md)

    css = OUT / "epub.css"
    css.write_text(EPUB_CSS)
    subprocess.run(["pandoc", str(OUT / "book.md"), "-o", str(OUT / "The-Heart-Thread.epub"),
                    "--toc", "--toc-depth=2", "--split-level=2", "--css", str(css)], check=True)
    subprocess.run(["pandoc", str(OUT / "book.md"), "-o", str(OUT / "The-Heart-Thread.docx"),
                    "--toc", "--toc-depth=2"], check=True)

    # Print interior: HTML -> PDF with Chromium.
    html_body = subprocess.run(["pandoc", "-f", "markdown", "-t", "html5"], input=body,
                               capture_output=True, text=True, check=True).stdout
    fonts_css = (HERE / "fonts" / "ebgaramond-local.css").read_text()
    copyright_html = "".join(f"<p>{p}</p>" for p in COPYRIGHT.split("\n\n"))
    thanks_html = subprocess.run(["pandoc", "-t", "html5"], input=THANKS, capture_output=True,
                                 text=True, check=True).stdout
    about_html = subprocess.run(["pandoc", "-t", "html5"], input=ABOUT, capture_output=True,
                                text=True, check=True).stdout
    print_html = PRINT_HTML.format(
        fonts=fonts_css, title=TITLE, series=SERIES_LINE, author=AUTHOR,
        copyright=copyright_html, body=html_body, thanks=thanks_html, about=about_html)
    (HERE / "fonts" / "print.html").write_text(print_html)   # next to the font files it references
    pdf = OUT / "The-Heart-Thread-paperback-5.5x8.5.pdf"
    subprocess.run(["node", str(HERE / "print_pdf.js"), str(HERE / "fonts" / "print.html"), str(pdf)],
                   check=True)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    print(f"EPUB, DOCX, PDF built. Paperback interior: {pages} pages. "
          f"Spine (white paper): {pages * 0.002252:.3f} in")


EPUB_CSS = """
body { font-family: serif; line-height: 1.45; }
h1 { text-align: center; margin-top: 30%; font-size: 1.6em; }
h2 { text-align: center; margin: 2em 0 1.5em; font-size: 1.3em; }
p { margin: 0; text-indent: 1.3em; }
h1 + p, h2 + p, hr + p, p:first-of-type { text-indent: 0; }
hr { border: none; text-align: center; margin: 1.2em 0; }
hr::after { content: "* * *"; }
blockquote { margin: 1em 1.5em; font-style: italic; }
"""

PRINT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>
{fonts}
@page {{ size: 5.5in 8.5in; margin: 0.75in 0.7in 0.85in 0.7in; }}
html {{ font-family: 'EB Garamond', 'Liberation Serif', serif; font-size: 11.5pt; }}
body {{ margin: 0; line-height: 1.38; text-align: justify; hyphens: auto; -webkit-hyphens: auto; }}
p {{ margin: 0; text-indent: 1.4em; orphans: 2; widows: 2; }}
h1 + p, h2 + p, hr + p, .pov + p {{ text-indent: 0; }}
h1 {{ break-before: page; break-after: page; text-align: center; font-weight: 400;
      font-size: 20pt; letter-spacing: 0.04em; padding-top: 2.6in; margin: 0; }}
h2 {{ break-before: page; text-align: center; font-weight: 400; font-size: 15pt;
      margin: 1.1in 0 0.45in; }}
h2 + p em:only-child {{ display: block; text-align: center; letter-spacing: 0.15em;
      text-transform: uppercase; font-size: 9pt; font-style: normal; margin-bottom: 0.3in; }}
hr {{ border: none; text-align: center; margin: 0.9em 0; height: 1em; }}
hr::after {{ content: "*   *   *"; font-size: 10pt; }}
blockquote {{ margin: 0.8em 1.6em; font-style: italic; }}
blockquote p {{ text-indent: 0; text-align: left; }}
.title-page {{ text-align: center; padding-top: 2.2in; break-after: page; }}
.title-page .t {{ font-size: 26pt; letter-spacing: 0.05em; }}
.title-page .s {{ font-size: 11pt; margin-top: 0.25in; font-style: italic; }}
.title-page .a {{ font-size: 13pt; margin-top: 1.6in; letter-spacing: 0.12em; text-transform: uppercase; }}
.copyright {{ break-after: page; padding-top: 4.4in; font-size: 8.5pt; }}
.copyright p {{ text-indent: 0; margin-bottom: 0.6em; text-align: left; }}
.back {{ break-before: page; }}
.back h3 {{ text-align: center; font-weight: 400; font-size: 14pt; margin: 1in 0 0.4in; }}
.back p {{ text-indent: 0; margin-bottom: 0.7em; }}
</style></head><body>
<section class="title-page"><div class="t">{title}</div><div class="s">{series}</div><div class="a">{author}</div></section>
<section class="copyright">{copyright}</section>
{body}
<section class="back"><h3>Thank You for Reading</h3>{thanks}</section>
<section class="back"><h3>About the Author</h3>{about}</section>
</body></html>"""

if __name__ == "__main__":
    build()
