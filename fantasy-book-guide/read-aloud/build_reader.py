"""Build the read-aloud page from the guide's markdown files.

Usage: venv/bin/python build_reader.py <guide_dir> <template.html> <out.html>
"""
import json
import re
import sys
from pathlib import Path

import markdown

guide, template_path, out_path = (Path(p) for p in sys.argv[1:4])


def clean_md(md: str) -> str:
    # Task-list boxes read badly and can't be ticked here.
    md = re.sub(r"^(\s*)- \[[ xX]\] ", r"\1- ", md, flags=re.M)
    # Links to other guide files don't exist on the page; keep the link text.
    md = re.sub(r"\[([^\]]+)\]\((?!https?://)[^)]*\)", r"\1", md)
    return md


def render(md: str) -> str:
    html = markdown.markdown(clean_md(md), extensions=["tables", "fenced_code", "sane_lists"])
    html = html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    html = html.replace("<a href=", '<a target="_blank" rel="noopener" href=')
    return html


def split_h1(md: str):
    m = re.match(r"\s*# (.+)\n", md)
    return (m.group(1).strip(), md[m.end():]) if m else ("", md)


chapters = []

# 1. Current step first.
title, body = split_h1((guide / "05-premise-workshop.md").read_text())
chapters.append({"group": "Your current step", "title": "Step 3 Workshop: Knight & Wizard, Forced Together", "html": render(body)})

# 2. Craft lessons, one chapter per lesson (skip the intro + contents list).
craft = (guide / "01-craft-guide.md").read_text()
parts = re.split(r"^## (Lesson \d+ — .+)$", craft, flags=re.M)
for heading, body in zip(parts[1::2], parts[2::2]):
    body = re.sub(r"\n---\s*$", "\n", body.rstrip())
    chapters.append({"group": "Craft lessons", "title": heading.strip(), "html": render(body)})

# 3. Planning and publishing.
for fname, short in [
    ("02-age-editions-and-series-plan.md", "Kids, Teens & Adults Plan"),
    ("03-publishing-and-money.md", "Publishing & Money"),
]:
    _, body = split_h1((guide / fname).read_text())
    chapters.append({"group": "Planning & publishing", "title": short, "html": render(body)})

data = json.dumps(chapters, ensure_ascii=False).replace("</", "<\\/")
page = Path(template_path).read_text().replace("/*__CHAPTERS__*/[]", data)
Path(out_path).write_text(page)
print(f"{len(chapters)} chapters, {len(page):,} bytes")
