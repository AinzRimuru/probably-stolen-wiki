import os, re, json, base64, html as htmlmod

ROOT = r"D:\nazarick\probably-stolen-wiki"
WIKI = os.path.join(ROOT, "wiki")

SRC = [
    ("index.html", "首页", "deed"),
    ("mechanics.html", "通用生产机制", "module_green"),
    ("items.html", "物品图鉴", "the_coin"),
    ("graph.html", "产业链图（交互）", "module_black_5"),
    ("systems/wine.html", "酿酒与陈化", "wine_berry"),
    ("systems/water.html", "净水与集水", "portable_water_purifier"),
    ("systems/pharma.html", "制药与化学合成", "dream_dust"),
    ("systems/hydroponics.html", "水培种植", "nutrifruit_seed"),
    ("systems/guns.html", "枪支打印", "printed_gun"),
    ("systems/aquaculture.html", "养鱼与畜牧", "fishscrap"),
    ("systems/misc-machines.html", "其他生产机器", "furnace"),
]
GROUPS = [("总览", SRC[:4]), ("生产系统", SRC[4:])]

# ---- 1. extract page fragments from built site ----
frag = {}
search_json = None
for f, title, _ in SRC:
    if f == "graph.html":
        continue
    s = open(os.path.join(WIKI, f), encoding="utf-8").read()
    m = re.search(r'(<div class="hero"[^>]*>.*?</div>\n\s*<div class="doc" id="doc">.*?</div>)\s*</main>', s, re.S)
    frag[f] = m.group(1) if m else None
    if search_json is None:
        sm = re.search(r"const SEARCH_DATA = (\[.*?\]);\n", s, re.S)
        search_json = sm.group(1)

# ---- 2. collect icons & build data-uri map ----
needed = set()
def scan(s):
    for m in re.finditer(r'assets/icons/([a-z0-9_]+)\.png', s):
        needed.add(m.group(1))
for f, body in frag.items():
    scan(body or "")
for _, _, sprite in SRC:
    needed.add(sprite)
graph_src = open(os.path.join(WIKI, "graph.html"), encoding="utf-8").read()
scan(graph_src)
gd = json.load(open(os.path.join(WIKI, "assets", "graph-data.json"), encoding="utf-8"))
for n in gd["nodes"]:
    if n.get("icon"):
        needed.add(n["icon"].replace(".png", ""))

ICONS = {}
missing = []
for name in sorted(needed):
    p = os.path.join(WIKI, "assets", "icons", name + ".png")
    if os.path.exists(p):
        ICONS[name] = "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
    else:
        missing.append(name)

def to_datauri(s):
    return re.sub(r'(?:\.\./)?assets/icons/([a-z0-9_]+)\.png',
                  lambda m: ICONS.get(m.group(1), m.group(0)), s)

# ---- 3. prepare graph document (self-contained) ----
g = to_datauri(graph_src)
gdata_js = open(os.path.join(WIKI, "assets", "graph-data.js"), encoding="utf-8").read()
g = g.replace('<script src="assets/graph-data.js"></script>',
              f'<script>{gdata_js}</script>')
icon_map_js = "const ICONS_B64 = " + json.dumps({k: v for k, v in ICONS.items()}) + ";"
g = g.replace('"use strict";', '"use strict";\n' + icon_map_js, 1)
g = g.replace('img.src = "assets/icons/" + n.icon;',
              'img.src = ICONS_B64[n.icon.replace(/\\.png$/, "")] || "";')
graph_srcdoc_js = json.dumps(g, ensure_ascii=False).replace("</", "<\\/")

# ---- 4. assemble single-file SPA ----
sections = []
nav_html, nav_options = "", ""
for gname, items in GROUPS:
    nav_html += f'<div class="navgroup">{gname}</div><div class="nav">'
    for f, title, sprite in items:
        pid = f[:-5] if f.endswith(".html") else f
        icon = f'<img src="{ICONS[sprite]}" alt="">' if sprite in ICONS else ""
        nav_html += f'<a href="#" data-page="{pid}">{icon}{title}</a>'
        nav_options += f'<option value="{pid}">{title}</option>'
    nav_html += "</div>"

page_sections = []
for f, title, _ in SRC:
    pid = f[:-5] if f.endswith(".html") else f
    if pid == "graph":
        page_sections.append(
            f'<section class="page" id="page-graph" data-title="产业链图">'
            f'<iframe id="graphFrame" title="产业链图" style="width:100%;height:calc(100vh - 24px);border:none"></iframe></section>')
        continue
    body = to_datauri(frag[f] or "<p>（正文缺失）</p>")
    page_sections.append(f'<section class="page" id="page-{pid}">{body}</section>')
sections = "\n".join(page_sections)

SPA_JS = """
const PAGES = [...document.querySelectorAll(".page")];
const frame = document.getElementById("graphFrame");
let graphLoaded = false;
function showPage(pid, anchor) {
  PAGES.forEach(p => p.classList.toggle("active", p.id === "page-" + pid));
  document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("active", a.dataset.page === pid));
  const sel = document.getElementById("pagesel");
  if (sel) sel.value = pid;
  if (pid === "graph" && !graphLoaded) {
    frame.srcdoc = GRAPH_SRCDOC; graphLoaded = true;
  }
  if (anchor) {
    const el = document.getElementById(anchor);
    if (el) setTimeout(() => el.scrollIntoView({block: "center"}), 40);
  } else window.scrollTo(0, 0);
  location.hash = pid + (anchor ? "/" + anchor : "");
}
document.querySelectorAll(".nav a").forEach(a =>
  a.addEventListener("click", e => { e.preventDefault(); showPage(a.dataset.page); }));
const sel = document.getElementById("pagesel");
if (sel) sel.addEventListener("change", () => showPage(sel.value));
// search
const SEARCH_DATA = __SEARCHDATA__;
const sbox = document.getElementById("search"), sres = document.getElementById("sresults");
function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;"); }
function doSearch(q) {
  q = q.trim().toLowerCase();
  if (!q) { sres.style.display = "none"; return; }
  const out = [];
  for (const e of SEARCH_DATA) {
    const t = e.text.toLowerCase();
    if (e.title.toLowerCase().includes(q) || t.includes(q)) {
      const idx = t.indexOf(q);
      const s = idx >= 0 ? e.text.slice(Math.max(0, idx - 16), idx + 56) : e.text.slice(0, 60);
      const score = e.title.startsWith(q) ? 0 : (e.title.toLowerCase().includes(q) ? 1 : 2);
      out.push({ e, s, score });
    }
  }
  out.sort((a, b) => a.score - b.score);
  out.length = Math.min(out.length, 14);
  sres.innerHTML = out.length ? out.map(o => {
    const [pg, anchor] = o.e.url.replace(".html", "").split("#");
    return `<button type="button" data-pg="${pg}" data-anchor="${anchor || ""}"><b>${esc(o.e.title)}</b><span>${esc(o.s)}</span></button>`;
  }).join("") : `<button type="button" disabled><span>没有匹配的结果，换个词试试</span></button>`;
  sres.style.display = "block";
  sres.querySelectorAll("button[data-pg]").forEach(b =>
    b.onclick = () => { sres.style.display = "none"; showPage(b.dataset.pg, b.dataset.anchor); });
}
sbox.addEventListener("input", () => doSearch(sbox.value));
sbox.addEventListener("keydown", e => { if (e.key === "Enter") {
  const f = sres.querySelector("button[data-pg]");
  if (f) { sres.style.display = "none"; showPage(f.dataset.pg, f.dataset.anchor); }
}});
document.addEventListener("click", e => { if (!e.target.closest("#side")) sres.style.display = "none"; });
// initial page from hash
const h = location.hash.replace("#", "").split("/");
showPage(["index","mechanics","items","graph","wine","water","pharma","hydroponics","guns","aquaculture","misc-machines"].includes(h[0]) ? h[0] : "index", h[1]);
"""

CSS = open(os.path.join(WIKI, "index.html"), encoding="utf-8").read()
css_m = re.search(r"<style>(.*?)</style>", CSS, re.S)
site_css = css_m.group(1)
site_css += """
.page { display: none; }
.page.active { display: block; }
#sresults button { display:block; width:100%; text-align:left; background:none; border:none; cursor:pointer;
  padding:8px 12px; font-size:12.5px; font-family:inherit; color:var(--text); border-bottom:1px solid var(--line2); }
#sresults button:hover { background:var(--raised); }
#sresults button b { color:var(--amber-hi); font-size:12px; font-weight:700; display:block; }
#sresults button span { color:var(--dim); display:block; font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#topbar .t { cursor:pointer; }
"""

# fix in-section hero/doc nesting (site CSS expects #main > .hero + .doc)
out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>深空当铺 Wiki（单文件版）</title>
<link rel="icon" href="{ICONS.get('deed','')}">
<style>{site_css}</style>
</head>
<body>
<div id="topbar"><img src="{ICONS.get('deed','')}" alt=""><span class="t" onclick="showPage('index')">深空当铺 Wiki</span>
<select id="pagesel" aria-label="切换页面">{nav_options}</select></div>
<div id="layout">
<nav id="side">
  <div class="brand"><img src="{ICONS.get('deed','')}" alt=""><div><div class="t">深空当铺 Wiki</div><small>Probably Stolen</small></div></div>
  <input id="search" placeholder="搜索物品 / 页面" autocomplete="off">
  <div id="sresults"></div>
  {nav_html}
  <hr>
  <div class="sidefoot">本文件自包含全部页面、图标与产业链图。</div>
</nav>
<main id="main">
{sections}
</main>
</div>
<script>
const GRAPH_SRCDOC = __GRAPHDOC__;
{SPA_JS.replace("__SEARCHDATA__", search_json)}
</script>
</body>
</html>""".replace("__GRAPHDOC__", graph_srcdoc_js)

dst = os.path.join(WIKI, "probably-stolen-wiki-standalone.html")
open(dst, "w", encoding="utf-8").write(out)
print(f"single file: {dst}")
print(f"size: {os.path.getsize(dst)/1024/1024:.2f} MB, icons embedded: {len(ICONS)}, missing: {missing[:5]}")
