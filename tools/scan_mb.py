import os, re, sys, json
from collections import Counter, defaultdict

ROOT = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets"

# 1. Build guid -> class name map from script meta files
guid2class = {}
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "Scripts")):
    for fn in filenames:
        if fn.endswith(".cs.meta"):
            p = os.path.join(dirpath, fn)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"guid: ([0-9a-f]{32})", f.read())
            if m:
                cls = fn[:-8]  # strip .cs.meta
                guid2class[m.group(1)] = (cls, os.path.basename(dirpath))

print(f"scripts mapped: {len(guid2class)}", file=sys.stderr)

# 2. Walk all .asset/.prefab/.unity files, find m_Script guids
counter = Counter()
examples = defaultdict(list)
script_re = re.compile(r"m_Script: \{fileID: 11500000, guid: ([0-9a-f]{32})")

exts = (".asset", ".prefab", ".unity")
nfiles = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    if "Scripts" in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if fn.endswith(exts):
            nfiles += 1
            p = os.path.join(dirpath, fn)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for m in script_re.finditer(content):
                g = m.group(1)
                counter[g] += 1
                if len(examples[g]) < 3:
                    examples[g].append(os.path.relpath(p, ROOT))

print(f"files scanned: {nfiles}", file=sys.stderr)
print(f"distinct script guids used: {len(counter)}", file=sys.stderr)

result = []
for g, cnt in counter.most_common():
    cls, asm = guid2class.get(g, ("<UNKNOWN>", "?"))
    result.append({"class": cls, "assembly": asm, "count": cnt, "guid": g, "examples": examples[g]})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mb_inventory.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

for r in result:
    print(f"{r['count']:5d}  {r['class']}")
