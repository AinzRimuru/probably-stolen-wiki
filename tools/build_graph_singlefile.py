import os, re, json, base64

ROOT = r"D:\nazarick\probably-stolen-wiki"
WIKI = os.path.join(ROOT, "wiki")

# ---- collect only the icons the graph needs ----
needed = set()
graph_src = open(os.path.join(WIKI, "graph.html"), encoding="utf-8").read()
for m in re.finditer(r'assets/icons/([a-z0-9_]+)\.png', graph_src):
    needed.add(m.group(1))
gd = json.load(open(os.path.join(WIKI, "assets", "graph-data.json"), encoding="utf-8"))
for n in gd["nodes"]:
    if n.get("icon"):
        needed.add(n["icon"].replace(".png", ""))
needed.add("deed")  # favicon
needed.add("the_coin")  # steam link icon

ICONS = {}
for name in sorted(needed):
    p = os.path.join(WIKI, "assets", "icons", name + ".png")
    if os.path.exists(p):
        ICONS[name] = "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()

# ---- transform graph.html ----
g = re.sub(r'(?:\.\./)?assets/icons/([a-z0-9_]+)\.png',
           lambda m: ICONS.get(m.group(1), m.group(0)), graph_src)
gdata_js = open(os.path.join(WIKI, "assets", "graph-data.js"), encoding="utf-8").read()
g = g.replace('<script src="assets/graph-data.js"></script>', f'<script>{gdata_js}</script>')
g = g.replace('"use strict";',
              '"use strict";\nconst ICONS_B64 = ' + json.dumps(ICONS, ensure_ascii=False) + ';', 1)
g = g.replace('img.src = "assets/icons/" + n.icon;',
              'img.src = ICONS_B64[n.icon.replace(/\\.png$/, "")] || "";')

dst = os.path.join(WIKI, "chain-graph-standalone.html")
open(dst, "w", encoding="utf-8").write(g)
print(f"built {dst}")
print(f"size: {os.path.getsize(dst)/1024:.0f} KB, icons embedded: {len(ICONS)}")
