import json, os, re

ROOT = r"D:\nazarick\probably-stolen-wiki"
OUT = os.path.join(ROOT, "wiki", "assets", "graph-data.json")
SRC_DIR = os.path.join(ROOT, "tools", "rip", "ExportedProject", "Assets", "Scripts", "Assembly-CSharp")

SYSTEMS = [
    {"id": "wine", "name": "酿酒与陈化", "color": "#be514c"},
    {"id": "water", "name": "净水与集水", "color": "#429cbd"},
    {"id": "pharma", "name": "制药与化学", "color": "#9d5c9d"},
    {"id": "hydroponics", "name": "水培种植", "color": "#7a9d4a"},
    {"id": "guns", "name": "枪支打印", "color": "#b8855a"},
    {"id": "aquaculture", "name": "养鱼与畜牧", "color": "#42a2aa"},
    {"id": "misc-machines", "name": "其他机器", "color": "#88948a"},
]

# ---- id resolution rules ----------------------------------------------------
RESOLVE = {  # tag -> concrete item id
    "tag:WINE_INGREDIENT_TAG": ["wine_berry"],
    "tag:WINE_YEAST_TAG": ["wine_yeast"],
    "tag:WINE_CONTAINER_TAG": ["wine_bottle"],
    "tag:DNA_DISK_TAG": ["plant_dna_disk"],
}
PSEUDO = {  # tag / wildcard -> pseudo node def
    "tag:LIQUID_CONTAINER_TAG": ("pseudo:liquid", "任意液体容器", "水与各类液体的载体（水质按纯度分档）"),
    "tag:WATER": ("pseudo:liquid", "任意液体容器", ""),
    "same_container": ("pseudo:liquid", "任意液体容器", ""),
    "liquid:water": ("pseudo:liquid", "任意液体容器", ""),
    "tag:CALORIE_VALUE_TAG": ("pseudo:food", "任意食物/热量", "任何带热量的食物、饲料、肉、活鱼活鼠"),
    "tag:BLENDABLE_TAG": ("pseudo:food", "任意食物/热量", ""),
    "tag:BREVAGE": ("pseudo:food", "任意食物/热量", ""),
    "any": ("pseudo:food", "任意食物/热量", ""),
    "tag:SEED_ITEM_TAG": ("pseudo:seed", "任意植物种子", ""),
    "tag:FISH_ITEM_TAG": ("pseudo:fish", "活鱼（任意）", ""),
    "tag:FISH_FRY_TAG": ("pseudo:fry", "鱼苗（任意）", ""),
    "tag:FISH_ROE_TAG": ("pseudo:roe", "鱼卵（任意）", ""),
    "tag:ACCESS_CARD": ("pseudo:accesscard", "门禁卡（任意）", ""),
    "tag:WATER_FILTER": ("pseudo:filter", "滤水器（任意）", ""),
    "tag:ANIMAL_FECES_TAG": (None, None, None),  # skip
    "tag:power_source_item": (None, None, None),  # skip: power, not material
}
LIQUID_ZH = {
    "liquid:alcohol": "酒精", "liquid:caffeine": "咖啡因",
    "liquid:coffee_mush": "咖啡糊", "liquid:debris": "不溶性碎屑",
    "liquid:dream_cap_extract": "梦帽菇萃取液", "liquid:dream_cap_mush": "梦帽菇糊",
    "liquid:fanta": "芬太", "liquid:lipobond_agent": "脂合剂",
    "liquid:methylol": "N-羟甲基碱", "liquid:nightmare_cap_mush": "梦魇帽菇糊",
    "liquid:nightmare_extract": "梦魇帽菇萃取液", "liquid:nomore": "奥克莫吸",
    "liquid:plant_matter": "植物质", "liquid:reducing_agent": "还原剂",
    "liquid:stabilizing_agent": "稳定剂", "liquid:zyanide": "山奈德",
    "liquid:contraceptive": "避孕激素", "liquid:acid": "酸", "liquid:base": "碱",
}
EXCLUDE_RECIPE = ("升级", "扩容")  # machine self-upgrades are not products

# short machine names for process node labels (avoids recipe/item name collisions)
MACHINE_SHORT = {
    "wine_bottle": "酒瓶", "wine_rack": "催陈器", "evaporator": "蒸发器",
    "water_purifier": "净水器", "moisture_farm": "水分收集器", "water_tank": "储水罐",
    "vending_fountain": "自动售水机",
    "blender": "搅拌机", "heating_plate": "加热板", "chem_finisher": "化学制剂成型机",
    "hydroponic": "水培系统", "plant_dna_manipulator": "DNA编辑器",
    "printer": "3D打印机", "ras": "循环水养殖系统", "livestock_feed_dispenser": "牲畜饲料分配器",
    "auto_butcher": "自动屠宰机", "animal_cage": "动物笼", "mouse_trap": "捕鼠夹",
    "vacuum_robot": "清洁机器人", "marking_pen": "标记笔", "surgery_tool": "手术工具",
    "furnace": "熔炉", "desequencer": "密码解序器", "fridge": "冰箱",
    "bottle_printer": "水瓶打印机", "box_dispenser": "纸箱机",
    "vending_machine": "自动售货机", "recharger": "充能器",
}

def make_node_label(machine, recipe):
    """Node label = 机器短名·核心名 (strip parenthetical qualifiers); keep full name for panels."""
    short = MACHINE_SHORT.get(machine, machine)
    core = re.sub(r"（[^）]*）|\([^)]*\)", "", recipe).strip()
    core = core or recipe
    if short and short not in recipe:
        return f"{short}·{core}"
    return core
EXCLUDE_RECIPE_EXACT = {
    ("misc-machines", "vending_machine", "夜间自动售卖（通用，非投币配方）"),  # goods->credits, no item link
    ("misc-machines", "recharger", "夜间充电"),  # power only
}
# unobtainable machines: registered in code but no acquisition path (vendor/loot/grant) — drop with their recipes
EXCLUDE_MACHINES = {"box_dispenser"}

# ---- load -------------------------------------------------------------------
items_db = {it["id"]: it for it in json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))}
sprite_map = json.load(open(os.path.join(ROOT, "data", "sprite_map.json"), encoding="utf-8"))
icons = set(f[:-4] for f in os.listdir(os.path.join(ROOT, "wiki", "assets", "icons")) if f.endswith(".png"))

nodes, links = {}, []
def get_item_node(iid):
    if iid in nodes:
        return nodes[iid]
    it = items_db.get(iid)
    n = {
        "id": iid, "type": "item",
        "label": (it and it.get("name_zh")) or iid,
        "value": (it and it.get("value")),
        "systems": set(), "icon": None, "hub": False, "note": (it and it.get("note")) or "",
    }
    sp = sprite_map.get(iid)
    if sp and sp in icons:
        n["icon"] = sp + ".png"
    nodes[iid] = n
    return n

def get_pseudo_node(pid, label, desc):
    if pid in nodes:
        return nodes[pid]
    n = {"id": pid, "type": "pseudo", "label": label, "value": None,
         "systems": set(), "icon": None, "hub": False, "note": desc}
    nodes[pid] = n
    return n

def get_liquid_node(lid):
    if lid in nodes:
        return nodes[lid]
    n = {"id": lid, "type": "liquid", "label": LIQUID_ZH.get(lid, lid.split(":", 1)[1]),
         "value": None, "systems": set(), "icon": None, "hub": False, "note": "液体成分（容器内）"}
    nodes[lid] = n
    return n

def resolve(eid):
    """yield ('node', id) or ('skip', None); attaches nothing"""
    if not eid:
        return [("skip", None)]
    if eid.startswith("tag:") and eid in RESOLVE:
        return [("node", x) for x in RESOLVE[eid]]
    if eid in PSEUDO:
        p = PSEUDO[eid]
        if not isinstance(p, tuple) or p[0] is None:
            return [("skip", None)]
        return [("pseudo", p)]
    if eid.startswith("liquid:"):
        if eid == "liquid:water":
            return [("pseudo", PSEUDO["liquid:water"])]
        return [("liquid", eid)]
    if "|" in eid:  # combined alternatives like scrap_metal|common_ore
        out = [("node", p.strip()) for p in eid.split("|") if p.strip()]
        return out or [("skip", None)]
    return [("node", eid)]

# ---- walk systems -----------------------------------------------------------
processes = []
for sys_ in SYSTEMS:
    sid = sys_["id"]
    d = json.load(open(os.path.join(ROOT, "data", "systems", f"{sid}.json"), encoding="utf-8"))
    mz = {m["id"]: m.get("name_zh") or m["id"] for m in d["machines"]}
    for m in d["machines"]:
        for ri, r in enumerate(m.get("recipes", [])):
            rname = r.get("name", "")
            if m["id"] in EXCLUDE_MACHINES:
                continue
            if rname.startswith(EXCLUDE_RECIPE) or (sid, m["id"], rname) in EXCLUDE_RECIPE_EXACT:
                continue
            pid = f"p:{sid}:{m['id']}:{ri}"
            proc = {
                "id": pid, "type": "process", "label": make_node_label(m["id"], rname), "name": rname,
                "system": sid, "machine": m["id"], "machine_zh": mz.get(m["id"], m["id"]),
                "time": r.get("time", ""), "conditions": r.get("conditions", ""),
                "notes": r.get("notes", ""), "in": [], "out": [],
            }
            touched = False
            for kind, entries in (("in", r.get("inputs", [])), ("out", r.get("outputs", []))):
                for e in entries:
                    eid = e.get("id", "")
                    for res in resolve(eid):
                        if res[0] == "skip":
                            continue
                        target = None
                        if res[0] == "node":
                            target = get_item_node(res[1])["id"]
                        elif res[0] == "pseudo":
                            p = res[1]
                            target = get_pseudo_node(p[0], p[1], p[2])["id"]
                        elif res[0] == "liquid":
                            target = get_liquid_node(res[1])["id"]
                        if target is None:
                            continue
                        touched = True
                        proc[kind].append({"id": target, "raw_id": eid,
                                           "amount": e.get("amount", 1),
                                           "name_zh": e.get("name_zh", ""),
                                           "note": e.get("note", "")})
                        if kind == "in":
                            links.append({"s": target, "t": pid})
                        else:
                            links.append({"s": pid, "t": target})
                        nodes[target]["systems"].add(sid)
            if touched:
                processes.append(proc)

# drop items not connected to any process (isolated)
connected = set()
for l in links:
    connected.add(l["s"]); connected.add(l["t"])
for nid in list(nodes):
    if nid not in connected:
        del nodes[nid]

# ---- obtainability evidence & manual hide list ----
obt = json.load(open(os.path.join(ROOT, "data", "obtainable.json"), encoding="utf-8"))
evidence = obt["evidence"]
HIDE_ITEMS = []  # 手动隐藏无需展示的物品 id（写在这里即可从图中移除）
# ---- drop phantom items: source items with no acquisition path, plus manual hide list ----
evidence = set(obt["evidence"].keys())
evidence_dict = obt["evidence"]
proc_by_id = {p["id"]: p for p in processes}

def has_inlinks(nid):
    return any(l["t"] == nid for l in links)

dropped = []
changed = True
while changed:
    changed = False
    # processes with no remaining links
    linked = set()
    for l in links:
        linked.add(l["s"]); linked.add(l["t"])
    for p in list(proc_by_id):
        if p not in linked:
            del proc_by_id[p]
            processes.remove(next(x for x in processes if x["id"] == p))
            changed = True
    # item nodes: no in-links AND no acquisition evidence -> phantom
    for nid in list(nodes):
        n = nodes[nid]
        if n["type"] != "item":
            continue
        if nid in HIDE_ITEMS or (nid in linked and not has_inlinks(nid) and nid not in evidence):
            dropped.append((nid, n["label"], "手动隐藏" if nid in HIDE_ITEMS else "无获取途径"))
            del nodes[nid]
            links[:] = [l for l in links if l["s"] != nid and l["t"] != nid]
            changed = True

print("dropped items:", len(dropped))
for nid, label, why in dropped:
    print(f"   - {label} ({nid}) [{why}]")

# attach acquisition evidence to surviving item nodes



# --- upgrade name lookup: item -> specific upgrade names ---
_loc_data = json.load(open(os.path.join(ROOT, "data", "localization.json"), encoding="utf-8"))
_upgrade_names = {}
for _k, _v in _loc_data.items():
    _m = re.match(r'network_(\w+)_title', _k)
    if _m and _v.get("zh"):
        _upgrade_names[_m.group(1)] = _v["zh"]

_upgrade_grants = {}
_nul_path = os.path.join(ROOT, "tools", "rip", "ExportedProject", "Assets", "Scripts", "Assembly-CSharp", "NetworkUpgradeList.cs")
if os.path.exists(_nul_path):
    _nul = open(_nul_path, encoding="utf-8").read()
    _cur = None
    for _ln in _nul.split("\n"):
        _m2 = re.match(r'\s*"(\w+)",\s*$', _ln)
        if _m2:
            _cur = _m2.group(1)
        if _cur and _cur in _upgrade_names:
            for _im in re.finditer(r'DirectoryMaster\.Item\("([\w]+)"\)|ItemSpawner\.Spawn\("([\w]+)"\)', _ln):
                _iid = _im.group(1) or _im.group(2)
                _upgrade_grants.setdefault(_iid, [])
                if _upgrade_names[_cur] not in _upgrade_grants[_iid]:
                    _upgrade_grants[_iid].append(_upgrade_names[_cur])

def evidence_zh(srcs):
    out = []
    for s in srcs:
        if s.startswith("loot:"):
            out.append(f"探险搜刮或客户携带（{s[5:]}）")
        elif "vendor" in s:
            out.append("商人/退休专家出售")
        elif "guarantee" in s:
            out.append("锁箱保底出售")
        elif "NetworkUpgradeList" in s and "grant" in s:
            out.append("网络升级赠送")  # replaced below with specific names
        elif "StartingPerk" in s:
            out.append("开局特长赠送")
        elif "DebrisHelper" in s:
            out.append("太空残骸打捞")
        elif "StoreClientList" in s and "grant" in s:
            out.append("剧情事件发放")
        elif "grant" in s:
            out.append("开局/事件赠送")
        elif "spawn" in s or "table-ref" in s:
            out.append("事件/场景生成")
        else:
            out.append(s)
    # dedupe while preserving order
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]

# 只统计"真正制作"的工艺：物品在输出中且不在输入中，且机器不是该物品自身
produced_by = {}
for p in processes:
    input_ids = set(i["id"] for i in p["in"])
    for o in p["out"]:
        if o["id"] in input_ids:  # 同一工艺的输入=输出，是状态转换不是制作
            continue
        if p["machine"] == o["id"]:  # 机器就是该物品自身（如酒瓶发酵）
            continue
        if o["id"] not in produced_by:
            produced_by[o["id"]] = []
        mz = p["machine_zh"]
        if mz not in produced_by[o["id"]]:
            produced_by[o["id"]].append(mz)
for n in nodes.values():
    obtain = []
    if n["id"] in produced_by:
        obtain.append("、".join(produced_by[n["id"]]) + " 制作")
    if n["type"] == "item" and n["id"] in evidence:
        for x in evidence_zh(evidence_dict[n["id"]]):
            if x == "网络升级赠送" and n["id"] in _upgrade_grants:
                for u in _upgrade_grants[n["id"]]:
                    obtain.append(f"“{u}”升级赠送")
            else:
                obtain.append(x)
    n["obtain"] = obtain

# hub = participates in >=2 systems
for n in nodes.values():
    n["hub"] = len(n["systems"]) >= 2
    n["systems"] = sorted(n["systems"])

# ranks for x-bias (longest path from sources, cycle-safe)
adj = {}
for l in links:
    adj.setdefault(l["s"], []).append(l["t"])
rank = {n: 0 for n in nodes}
for _ in range(24):
    changed = False
    for s, ts in adj.items():
        rs = rank.get(s, 0) + 1
        for t in ts:
            if rs > rank.get(t, 0):
                rank[t] = rs
                changed = True
    if not changed:
        break
for p in processes:
    rank[p["id"]] = rank.get(p["id"], 0) + 0.5
maxr = max(rank.values()) or 1
for p in processes:
    p["rank01"] = round(rank.get(p["id"], 0) / maxr, 4)
for n in nodes.values():
    n["rank01"] = round(rank.get(n["id"], 0) / maxr, 4)

out = {
    "meta": {"version": "0.46D", "systems": SYSTEMS},
    "nodes": list(nodes.values()),
    "processes": processes,
    "links": links,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
# also emit a .js build for file:// usage (script tag bypasses CORS)
js = "window.GRAPH_DATA = " + json.dumps(out, ensure_ascii=False) + ";"
open(OUT[:-5] + ".js", "w", encoding="utf-8").write(js)
n_items = sum(1 for n in nodes.values() if n["type"] == "item")
n_pseudo = sum(1 for n in nodes.values() if n["type"] == "pseudo")
n_liquid = sum(1 for n in nodes.values() if n["type"] == "liquid")
print(f"nodes: {len(nodes)} (items {n_items}, pseudo {n_pseudo}, liquid {n_liquid}), processes {len(processes)}, links {len(links)}")
print(f"hubs (>=2 systems): {sum(1 for n in nodes.values() if n['hub'])}")
