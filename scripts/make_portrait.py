#!/usr/bin/env python3
import sys, html
from pathlib import Path
import numpy as np
from PIL import Image

try:
    import cv2
except Exception:
    cv2 = None

try:
    from rembg import remove
except Exception:
    remove = None

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 scripts/make_portrait.py /path/to/photo.png")

photo = Path(sys.argv[1])
out = Path(__file__).resolve().parents[1] / "assets" / "ascii.svg"

raw = Image.open(photo).convert("RGBA")
if remove is not None:
    raw = remove(raw)

bg = Image.new("RGBA", raw.size, (255,255,255,255))
bg.alpha_composite(raw)
gray = np.array(bg.convert("L"))

h, w = gray.shape
gray = gray[int(h*.06):int(h*.74), int(w*.24):int(w*.77)]

if cv2 is not None:
    gray = cv2.bilateralFilter(gray, 7, 40, 40)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)

v = np.power(gray.astype(np.float32)/255.0, 1.7)
gray = np.clip(v*255, 0, 255).astype(np.uint8)

cols = 90
rows = int(cols * (gray.shape[0]/gray.shape[1]) * 0.48)
im = Image.fromarray(gray).resize((cols, rows), Image.Resampling.LANCZOS)
a = np.asarray(im)
ramp = " .`:-=+*cs#%@"
indices = np.clip(((255-a)/255*(len(ramp)-1)).round().astype(int), 0, len(ramp)-1)
lines = ["".join(ramp[i] for i in row).rstrip() for row in indices]

font_size = 12.9
char_w = 7.74
line_h = 14.3
x0, y0 = 24, 29
svg_w = int(x0*2 + cols*char_w)
svg_h = int(y0*2 + rows*line_h)

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
    '<rect width="100%" height="100%" fill="#0d1117"/>',
    '<defs>',
]
for i, line in enumerate(lines):
    full_w = max(1, len(line)*char_w)
    parts += [
        f'<clipPath id="clip{i}">',
        f'<rect x="{x0}" y="{y0+i*line_h-font_size}" width="0" height="{line_h+2}">',
        f'<animate attributeName="width" from="0" to="{full_w:.1f}" dur="0.65s" begin="{i*.09:.2f}s" fill="freeze"/>',
        '</rect></clipPath>',
    ]
parts.append('</defs>')
for i, line in enumerate(lines):
    parts.append(
        f'<text x="{x0}" y="{y0+i*line_h:.1f}" clip-path="url(#clip{i})" '
        f'fill="#7ee787" font-family="JetBrains Mono, Liberation Mono, DejaVu Sans Mono, monospace" '
        f'font-size="{font_size}" xml:space="preserve">{html.escape(line)}</text>'
    )
parts.append('</svg>')
out.write_text("\n".join(parts), encoding="utf-8")
print(out)
