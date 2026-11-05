import os, re, json, sys

LOC = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets\Resources\emporium\localization"

tables = {}  # table name -> {id: key}
for d in os.listdir(LOC):
    dp = os.path.join(LOC, d)
    if not os.path.isdir(dp):
        continue
    for fn in os.listdir(dp):
        if not fn.endswith("Shared Data.asset"):
            continue
        tname = fn[:-len(" Shared Data.asset")]
        content = open(os.path.join(dp, fn), encoding="utf-8").read()
        id2key = {}
        for m in re.finditer(r"- m_Id: (\d+)\s*\n\s*m_Key: (.+?)\s*\n", content):
            id2key[m.group(1)] = m.group(2)
        tables[f"{d}/{tname}"] = id2key

out = {}
counts = {}
for tname, id2key in tables.items():
    d, tname_short = tname.split("/", 1)
    dp = os.path.join(LOC, d)
    for lang in ("zh", "en"):
        fn = f"{tname_short}_{lang}.asset"
        p = os.path.join(dp, fn)
        if not os.path.exists(p):
            continue
        content = open(p, encoding="utf-8").read()
        # entries: - m_Id: N\n    m_Localized: text
        n = 0
        for m in re.finditer(r"- m_Id: (\d+)\s*\n\s*m_Localized: (.*?)(?=\s*m_Metadata:)", content, re.S):
            mid, val = m.group(1), m.group(2).strip()
            key = id2key.get(mid)
            if key is None:
                continue
            # unescape unity string escapes
            val = val.strip('"') if val.startswith('"') and val.endswith('"') else val
            out.setdefault(key, {})[lang] = val
            n += 1
        counts[f"{tname}/{lang}"] = n

dst = r"D:\nazarick\probably-stolen-wiki\data\localization.json"
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(counts, indent=1))
print(f"total keys: {len(out)}")
