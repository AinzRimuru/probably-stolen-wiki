import json, os

ROOT = r"D:\nazarick\probably-stolen-wiki"
items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
# 无获取途径/内部物品，不进图鉴（与 items.json note 同步维护）
HIDDEN = {"test_gizmo","aug_chip","sign_berry","box_dispenser","restricted_medical",
          "blank_module","node_small","barrel","lottery_ticket_old",
          "save_bag","back_inv_save_bag","hidden_save_bag","showcase_save_bag","sold_save_bag","tutorial_page"}
items = [it for it in items if it["id"] not in HIDDEN]

DIR_ZH = {
    "FoodItemDirectory": "食物与饮品",
    "MedsItemDirectory": "药品",
    "GunsItemDirectory": "枪械",
    "GunModDirectory": "枪械改装件",
    "MeleeWeaponItemDirectory": "近战武器",
    "ArmorItemDirectory": "护甲",
    "AmmunitionItemDirectory": "弹药",
    "FurnitureItemDirectory": "机器与家具",
    "HydroponicDirectory": "水培种植",
    "WineDirectory": "酿酒",
    "HusbandryDirectory": "水产与畜牧",
    "ContainerItemDirectory": "容器",
    "MaterialDirectory": "材料",
    "ToolDirectory": "工具",
    "MiscItemDirectory": "杂项",
    "ModuleDirectory": "模组",
    "AmenitiesItemDirectory": "生活设施",
    "ExplosiveItemDirectory": "爆炸物",
    "KeyItemDirectory": "钥匙",
    "ConstructionItemDirectory": "建造",
    "EquipmentDirectory": "装备",
    "ShipSystemDirectory": "舱室系统",
    "PreBuiltItemHelper": "预生成物品",
    "PreBuildChemHelper": "化学变体",
    "Armor / Construction / Equipment": "其他",
}

def val(v):
    return str(v) if v is not None else "—"

lines = []
lines.append("# 物品图鉴")
lines.append("")
lines.append("按物品目录分组，中文名为游戏官方简体中文本地化。基准价为基础售价（实际售价受市场/声望/谈判影响）。")
lines.append("")

groups = {}
for it in items:
    groups.setdefault(it.get("directory") or "其他", []).append(it)

order = ["FoodItemDirectory", "WineDirectory", "MedsItemDirectory", "HydroponicDirectory",
         "HusbandryDirectory", "GunsItemDirectory", "GunModDirectory", "MeleeWeaponItemDirectory",
         "ArmorItemDirectory", "ExplosiveItemDirectory", "FurnitureItemDirectory", "MaterialDirectory",
         "ContainerItemDirectory", "ToolDirectory", "ModuleDirectory", "AmenitiesItemDirectory",
         "KeyItemDirectory", "ShipSystemDirectory", "ConstructionItemDirectory", "EquipmentDirectory",
         "MiscItemDirectory", "PreBuiltItemHelper", "PreBuildChemHelper"]

for d in order:
    if d not in groups:
        continue
    zh = DIR_ZH.get(d, d)
    lines.append(f"## {zh}（{d}）")
    lines.append("")
    lines.append("| 中文名 | 英文ID | 基准价 | 分类 | 备注 |")
    lines.append("|---|---|---|---|---|")
    for it in sorted(groups[d], key=lambda x: (x.get("value") is None, -(x.get("value") or 0), x["id"])):
        name = it.get("name_zh") or f"**无翻译** `{it['id']}`"
        types = ", ".join(it.get("types") or [])
        note = (it.get("note") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {name} | `{it['id']}` | {val(it.get('value'))} | {types} | {note} |")
    lines.append("")

# leftovers
rest = [d for d in groups if d not in order]
for d in rest:
    zh = DIR_ZH.get(d, d)
    lines.append(f"## {zh}（{d}）")
    lines.append("")
    lines.append("| 中文名 | 英文ID | 基准价 | 分类 | 备注 |")
    lines.append("|---|---|---|---|---|")
    for it in sorted(groups[d], key=lambda x: x["id"]):
        name = it.get("name_zh") or f"**无翻译** `{it['id']}`"
        types = ", ".join(it.get("types") or [])
        note = (it.get("note") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {name} | `{it['id']}` | {val(it.get('value'))} | {types} | {note} |")
    lines.append("")

dst = os.path.join(ROOT, "wiki", "items.md")
open(dst, "w", encoding="utf-8").write("\n".join(lines))
print("written", dst, len(lines), "lines")
