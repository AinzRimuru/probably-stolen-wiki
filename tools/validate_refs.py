import json, os, re, glob

ROOT = r"D:\nazarick\probably-stolen-wiki"
items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
known = {it["id"] for it in items}

def ids_from_io(entries):
    for e in entries:
        i = e.get("id", "")
        if not i:
            continue
        for part in re.split(r"[|/+,]", i):
            part = part.strip()
            if part and not part.startswith(("tag:", "liquid:")) and part not in ("any", "same_container"):
                yield part

problems = {}
for p in glob.glob(os.path.join(ROOT, "data", "systems", "*.json")):
    d = json.load(open(p, encoding="utf-8"))
    sysname = os.path.basename(p)
    miss = set()
    for m in d.get("machines", []):
        for r in m.get("recipes", []):
            miss.update(x for x in ids_from_io(r.get("inputs", [])) if x not in known)
            miss.update(x for x in ids_from_io(r.get("outputs", [])) if x not in known)
        mid = m.get("id")
        if mid not in known and not str(mid).startswith("tag:") and mid != "ammo_box":
            miss.add("(machine)" + str(mid))
    for it in d.get("items", []):
        i = it.get("id")
        if i and i not in known and not str(i).startswith(("tag:", "liquid:")) and i not in ("any", "same_container"):
            miss.add(i)
    if miss:
        problems[sysname] = sorted(miss)

if problems:
    for k, v in problems.items():
        print(k)
        for x in v:
            print("   ?", x)
else:
    print("ALL REFERENCES OK")
print(f"item database: {len(known)} ids")
