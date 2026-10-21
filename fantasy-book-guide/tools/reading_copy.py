"""Make a reading copy of the novel: the cover image as page 1, then the interior.

Usage: python reading_copy.py <cover.jpg|png> <interior.pdf> <out.pdf>
Needs: pypdf, Pillow
"""
import io
import sys

from PIL import Image
from pypdf import PdfReader, PdfWriter

cover_path, interior_path, out_path = sys.argv[1:4]

interior = PdfReader(interior_path)
box = interior.pages[0].mediabox
page_w, page_h = float(box.width), float(box.height)   # points (5.5x8.5 in = 396x612)

# Fit the cover image onto a page the same size as the interior. If the shapes differ,
# pad the short side with the cover's own edge color instead of stretching the art.
img = Image.open(cover_path).convert("RGB")
target_w = round(img.height * page_w / page_h)
target_h = round(img.width * page_h / page_w)
if target_w > img.width:
    edge = img.crop((0, 0, 1, img.height)).resize((1, 1), Image.BOX).getpixel((0, 0))
    padded = Image.new("RGB", (target_w, img.height), edge)
    padded.paste(img, ((target_w - img.width) // 2, 0))
    img = padded
elif target_h > img.height:
    edge = img.crop((0, 0, img.width, 1)).resize((1, 1), Image.BOX).getpixel((0, 0))
    padded = Image.new("RGB", (img.width, target_h), edge)
    padded.paste(img, (0, (target_h - img.height) // 2))
    img = padded
dpi = img.width / (page_w / 72)
buf = io.BytesIO()
img.save(buf, format="PDF", resolution=dpi)
cover_pdf = PdfReader(io.BytesIO(buf.getvalue()))
cover_page = cover_pdf.pages[0]
cover_page.scale_to(page_w, page_h)

out = PdfWriter()
out.add_page(cover_page)
for p in interior.pages:
    out.add_page(p)
out.add_metadata({"/Title": "The Heart-Thread", "/Author": "Luke Moreland"})
with open(out_path, "wb") as f:
    out.write(f)
print(f"wrote {out_path}: {len(out.pages)} pages")
