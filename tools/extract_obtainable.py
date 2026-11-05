import UnityPy, struct, os, json, re

GAME = r"D:\Program Files (x86)\Steam\steamapps\common\Probably Stolen\Probably Stolen_Data"
SRC = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets\Scripts\Assembly-CSharp"
ROOT = r"D:\nazarick\probably-stolen-wiki"

items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
known = set(it["id"] for it in items)

evidence = {}  # id -> set of sources

def add_evidence(iid, src):
    if iid in known:
        evidence.setdefault(iid, set()).add(src)

# ---- 1. loot tables in sharedassets1.assets ----
env = UnityPy.load(os.path.join(GAME, "sharedassets1.assets"))
loot_tables = {}
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    raw = obj.get_raw_data()
    if len(raw) < 40:
        continue
    nl = struct.unpack_from("<i", raw, 28)[0]
    name = raw[32:32 + nl].decode("utf-8", "ignore") if 0 < nl < 100 else ""
    if not name or name[0].islower() is False and not name.endswith("Table") and not name.startswith("dumping"):
        pass
    body = raw[32 + nl:]
    pos, out = 0, []
    while pos < len(body) - 4:
        sl = struct.unpack_from("<i", body, pos)[0]
        if 2 <= sl <= 48 and pos + 4 + sl <= len(body):
            s = body[pos + 4:pos + 4 + sl]
            if all(32 <= b < 127 for b in s):
                txt = s.decode()
                if txt in known:
                    out.append(txt)
                pos += 4 + sl
                continue
        pos += 1
    if out:
        loot_tables[name] = sorted(set(out))
        for i in set(out):
            add_evidence(i, f"loot:{name}")

# ---- 2. code: grants, vendors, spawns ----
FILES = ["StoreClientList.cs", "NetworkUpgradeList.cs", "CommissaryData.cs",
         "ScavHelper.cs", "DebrisHelper.cs", "DumpingGroundLocation.cs",
         "ExpeditionData.cs", "PreBuiltItemHelper.cs", "StoreService.cs",
         "StoryHelper.cs", "ExpeditionPoi.cs", "StartingPerkContent.cs", "AmenitiesItemDirectory.cs"]
pats = [
    (re.compile(r'AddDirectSellingItemToTable\("([\w]+)"\)'), "vendor"),
    (re.compile(r'ItemSpawner\.Spawn\("([\w]+)"\)'), "spawn"),
    (re.compile(r'DirectoryMaster\.Item\("([\w]+)"\)'), "grant"),
    (re.compile(r'ItemSpawner\.SpawnFromTable\w*\("([\w]+)"\)'), "table-ref"),
]
for fn in FILES:
    p = os.path.join(SRC, fn)
    if not os.path.exists(p):
        continue
    content = open(p, encoding="utf-8", errors="ignore").read()
    for pat, src in pats:
        for m in pat.finditer(content):
            add_evidence(m.group(1), f"{fn}:{src}")

# broad pass: ItemSpawner.Spawn / DirectSelling in ALL files except debug/unused
# broad pass: ItemSpawner.Spawn / DirectSelling in ALL files except debug/unused
for fn in os.listdir(SRC):
    if not fn.endswith(".cs") or fn in ("DebugPanel.cs", "UnusedDirectory.cs", "ItemSpawner.cs", "DirectoryMaster.cs"):
        continue
    content = open(os.path.join(SRC, fn), encoding="utf-8", errors="ignore").read()
    for pat, src in ((pats[0][0], "vendor"), (pats[1][0], "spawn"), (pats[3][0], "table-ref")):
        for m in pat.finditer(content):
            add_evidence(m.group(1), f"{fn}:{src}")

# ---- 3. species-based fish sales (retired aquafarmer / AQUACULTURE_II grant) ----
FISH = ["tilapia", "gutter_tilapia", "graft_tilapia", "eel", "electric_eel", "sturgeon"]
for f in FISH:
    add_evidence(f, "StoreClientListSpec.cs:vendor(退休水产商)")
for r in ["tilapia_roe", "gutter_tilapia_roe", "graft_tilapia_roe"]:
    if r in known:
        add_evidence(r, "StoreClientListSpec.cs:vendor(退休水产商)")

# ---- 4. lock dicts guarantee keycards & crypto chips (GuaranteeLockedCrateKeycardItems) ----
scl = open(os.path.join(SRC, "StoreClientList.cs"), encoding="utf-8", errors="ignore").read()
for m in re.finditer(r'\{ "(LOCK_ID_\w+)", "([\w]+)" \}', scl):
    add_evidence(m.group(2), "StoreClientList.cs:guarantee(锁箱保底)")

out = {
    "loot_tables": loot_tables,
    "evidence": {k: sorted(v) for k, v in evidence.items()},
}
json.dump(out, open(os.path.join(ROOT, "data", "obtainable.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"loot tables: {len(loot_tables)}, ids with evidence: {len(evidence)}")
for t, ids in sorted(loot_tables.items()):
    print(f"  {t}: {len(ids)} -> {', '.join(ids[:10])}{'...' if len(ids) > 10 else ''}")
