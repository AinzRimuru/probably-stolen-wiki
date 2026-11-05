import os, re, json
from PIL import Image

ROOT = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets\Resources\items"
DST = r"D:\nazarick\probably-stolen-wiki\wiki\assets\icons"
os.makedirs(DST, exist_ok=True)

# map tex guid -> png path (same folder)
guid2png = {}
for fn in os.listdir(ROOT):
    if fn.endswith(".png.meta"):
        g = re.search(r"guid: ([0-9a-f]{32})", open(os.path.join(ROOT, fn), encoding="utf-8").read())
        if g:
            guid2png[g.group(1)] = os.path.join(ROOT, fn[:-5])

count, missing = 0, []
for fn in sorted(os.listdir(ROOT)):
    if not fn.endswith(".asset"):
        continue
    content = open(os.path.join(ROOT, fn), encoding="utf-8").read()
    name = re.search(r"m_Name: (.+)", content).group(1).strip()
    mg = re.search(r"texture: \{fileID: 2800000, guid: ([0-9a-f]{32})", content)
    if not mg:
        continue
    png = guid2png.get(mg.group(1))
    if not png or not os.path.exists(png):
        missing.append(name)
        continue
    # first m_Rect after m_Name
    rect_m = re.search(r"m_Rect:\s*\n\s*serializedVersion: 2\s*\n\s*x: (-?\d+)\s*\n\s*y: (-?\d+)\s*\n\s*width: (\d+)\s*\n\s*height: (\d+)", content)
    if not rect_m:
        continue
    x, y, w, h = map(int, rect_m.groups())
    if w <= 0 or h <= 0:
        continue
    img = Image.open(png)
    # unity rect origin is bottom-left
    left, low = x, y
    box = (left, img.height - low - h, left + w, img.height - low)
    crop = img.crop(box)
    out = os.path.join(DST, f"{name}.png")
    crop.save(out)
    count += 1

print(f"icons extracted: {count}, missing tex: {len(missing)}")
if missing[:10]:
    print(missing[:10])
