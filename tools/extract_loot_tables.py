import UnityPy, os, json, re

GAME = r"D:\Program Files (x86)\Steam\steamapps\common\Probably Stolen\Probably Stolen_Data"
ROOT = r"D:\nazarick\probably-stolen-wiki"

# known item ids
items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
ids = sorted([it["id"] for it in items], key=len, reverse=True)

# table name -> raw data scan
env = UnityPy.load(os.path.join(GAME, "resources.assets"))
tables = {}
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    raw = obj.get_raw_data()
    if len(raw) < 40:
        continue
    # MonoBehaviour header: m_GameObject PPtr(12) + m_Enabled(4) + m_Script PPtr(12) + m_Name(len+str)
    import struct
    name_len = struct.unpack_from("<i", raw, 28)[0]
    name = raw[32:32 + name_len].decode("utf-8", "ignore") if 0 < name_len < 100 else ""
    if not name:
        continue
    hits = set()
    for i in ids:
        if i.encode() in raw:
            hits.add(i)
    if hits:
        tables[name] = sorted(hits)

json.dump(tables, open(os.path.join(ROOT, "data", "loot_tables.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in tables.items():
    print(f"{k}: {len(v)} items -> {', '.join(v[:12])}{'...' if len(v) > 12 else ''}")
