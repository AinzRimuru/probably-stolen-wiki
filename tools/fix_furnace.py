import json

p = r"D:\nazarick\probably-stolen-wiki\data\systems\misc-machines.json"
d = json.load(open(p, encoding="utf-8"))
f = [m for m in d["machines"] if m["id"] == "furnace"][0]

for r in f["recipes"]:
    if r["name"].startswith(("标准冶炼", "高炉冶炼")):
        n = r["inputs"][0]["amount"]
        r["inputs"] = [{
            "id": "scrap_metal|common_ore",
            "name_zh": "废金属 / 金属矿石（可混装）",
            "amount": n,
            "note": "两者合计任意 " + str(n) + " 个；混装时先耗矿石（代码取列表末尾，矿石靠后）"
        }]

json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fixed furnace inputs:", [r["inputs"] for r in f["recipes"][:2]])
