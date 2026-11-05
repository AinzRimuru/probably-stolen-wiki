import os, re, json
import markdown

ROOT = r"D:\nazarick\probably-stolen-wiki"
WIKI = os.path.join(ROOT, "wiki")

# nav: (file, title, sprite)
SRC = [
    ("index.md", "首页", "deed"),
    ("mechanics.md", "通用生产机制", "module_green"),
    ("items.md", "物品图鉴", "the_coin"),
    ("graph.html", "产业链图", "module_black_5"),
    ("systems/wine.md", "酿酒与陈化", "wine_berry"),
    ("systems/water.md", "净水与集水", "portable_water_purifier"),
    ("systems/pharma.md", "制药与化学合成", "dream_dust"),
    ("systems/hydroponics.md", "水培种植", "nutrifruit_seed"),
    ("systems/guns.md", "枪支打印", "printed_gun"),
    ("systems/aquaculture.md", "养鱼与畜牧", "fishscrap"),
    ("systems/misc-machines.md", "其他生产机器", "furnace"),
]
GROUPS = [("总览", SRC[:4]), ("生产系统", SRC[4:])]

# game palette (RenderHandler.ColorPalette)
C = dict(ink="#1a0b35", panel="#230f47", raised="#2c1656", line="#413d78",
         text="#c4c4b0", dim="#8397bb", amber="#ad6107", amberhi="#d9a75a",
         brick="#be514c")

sprite_map = json.load(open(os.path.join(ROOT, "data", "sprite_map.json"), encoding="utf-8"))
icons = set(f[:-4] for f in os.listdir(os.path.join(WIKI, "assets", "icons")))
items_db = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
# 无获取途径/内部物品不进图鉴与搜索（与 gen_items_page.py 保持一致）
HIDDEN_ITEMS = {"test_gizmo","aug_chip","sign_berry","box_dispenser","restricted_medical",
                "blank_module","node_small","barrel","lottery_ticket_old",
                "save_bag","back_inv_save_bag","hidden_save_bag","showcase_save_bag","sold_save_bag","tutorial_page"}
items_db = [it for it in items_db if it["id"] not in HIDDEN_ITEMS]
MD_EXT = ["tables", "toc", "fenced_code", "sane_lists"]

# hero sprites: a pawn-counter strip of iconic items
HERO_SPRITES = ["deed", "coin", "wine_bottle", "normal", "dream_dust", "nutrifruit_seed",
                "printed_gun", "fishscrap", "furnace", "metal_ingot", "energy_credit", "tilapia_roe"]
HERO_SPRITES = [s for s in HERO_SPRITES if s in icons]

CSS = """
:root{
  --ink:#1a0b35; --panel:#230f47; --raised:#2c1656; --line:#413d78; --line2:#341f63;
  --text:#c4c4b0; --dim:#8397bb; --faint:#5d6b9e;
  --amber:#ad6107; --amber-hi:#d9a75a; --brick:#be514c; --link:#429cbd;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--ink);color:var(--text);
  font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif;line-height:1.75;font-size:14.5px}
#layout{display:flex;min-height:100vh}

/* ---- sidebar ---- */
#side{width:248px;flex-shrink:0;background:var(--panel);border-right:1px solid var(--line);
  padding:20px 14px;position:sticky;top:0;height:100vh;overflow-y:auto}
.brand{display:flex;align-items:center;gap:10px;padding:2px 6px 4px}
.brand img{width:34px;height:34px;image-rendering:pixelated}
.brand .t{font-size:16.5px;font-weight:800;letter-spacing:.06em}
.brand small{display:block;color:var(--dim);font-weight:400;font-size:11px;margin-top:1px;letter-spacing:0}
#side hr{border:none;border-top:1px solid var(--line);margin:14px 4px}
.navgroup{color:var(--faint);font-size:12px;letter-spacing:.28em;padding:12px 8px 4px}
.nav a{display:flex;align-items:center;gap:10px;color:var(--text);text-decoration:none;
  padding:6px 8px;border-left:2px solid transparent;font-size:13.5px}
.nav a img{height:24px;width:auto;max-width:30px;image-rendering:pixelated;flex-shrink:0;
  background:#c4c4b0;padding:3px;border-radius:4px}
.nav a:hover{background:var(--raised);color:var(--amber-hi)}
.nav a.active{border-left-color:var(--amber);background:var(--raised);color:var(--amber-hi)}
.sidefoot{padding:0 8px;font-size:11px;color:var(--faint);line-height:1.6}
.sidefoot a{color:var(--link)}

/* search */
#search{width:100%;margin:12px 0 4px;padding:7px 10px;font-size:13px;color:var(--text);
  background:var(--ink);border:1px solid var(--line);outline:none;font-family:inherit}
#search:focus{border-color:var(--amber)}
#sresults{background:var(--panel);border:1px solid var(--line);margin-top:6px;
  max-height:340px;overflow:auto;display:none}
#sresults button{display:block;width:100%;text-align:left;background:none;border:none;cursor:pointer;
  padding:8px 12px;font-size:12.5px;font-family:inherit;color:var(--text);border-bottom:1px solid var(--line2)}
#sresults button:hover{background:var(--raised)}
#sresults button b{color:var(--amber-hi);font-size:12px;font-weight:700;display:block}
#sresults button span{color:var(--dim);display:block;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ---- main ---- */
#main{flex:1;min-width:0;padding:36px 48px 90px;max-width:1060px}
.hero{display:flex;align-items:flex-end;gap:6px;flex-wrap:wrap;margin:-6px 0 18px;opacity:.9}
.hero img{width:30px;height:30px;image-rendering:pixelated;margin-bottom:6px;background:#c4c4b0;padding:2px;border-radius:3px}
.hero img:first-child{width:38px;height:38px;margin-bottom:2px}
.doc h1{font-size:27px;font-weight:800;letter-spacing:.04em;margin-bottom:4px;
  border-bottom:3px solid var(--amber);padding-bottom:12px}
.doc h2{font-size:19px;font-weight:700;margin:36px 0 12px;color:var(--amber-hi);
  border-left:3px solid var(--amber);padding-left:10px;letter-spacing:.02em}
.doc h3{font-size:15.5px;margin:24px 0 8px;color:#d8d8c8}
.doc h4{font-size:14px;margin:16px 0 6px;color:#d8d8c8}
.doc p{margin:8px 0;max-width:78ch}
.doc ul,.doc ol{margin:8px 0 8px 22px;max-width:76ch}
.doc li{margin:3px 0}
.doc blockquote{border-left:3px solid var(--line);background:var(--panel);border-radius:0;
  padding:10px 14px;margin:12px 0;color:var(--dim);font-size:13.5px}
.doc blockquote p{margin:4px 0}
.doc code{background:var(--ink);border:1px solid var(--line2);padding:1px 5px;
  font-size:12px;color:#a9c98a;font-family:Consolas,"Courier New",monospace}
.doc pre{background:var(--ink);border:1px solid var(--line2);padding:12px 14px;overflow-x:auto;margin:10px 0}
.doc pre code{border:none;background:none;padding:0}
.doc a{color:var(--link);text-decoration:none;border-bottom:1px solid #2a5a70}
.doc a:hover{color:#7ec3e3;border-bottom-color:#7ec3e3}
.doc hr{border:none;border-top:1px solid var(--line);margin:20px 0}
.doc strong{color:#e2e2d2}

/* ledger tables */
.doc table{border-collapse:collapse;width:100%;font-size:13px;margin:12px 0;display:block;overflow-x:auto}
.doc th{text-align:left;padding:8px 10px;font-size:12.5px;font-weight:700;color:var(--amber-hi);
  background:var(--panel);border-top:2px solid var(--amber);border-bottom:1px solid var(--line);white-space:nowrap}
.doc td{padding:7px 10px;border-bottom:1px solid var(--line2);vertical-align:middle}
.doc tr:hover td{background:var(--raised)}
td .icon,.icon{width:22px;height:22px;image-rendering:pixelated;vertical-align:middle;margin-right:7px;
  background:#c4c4b0;padding:1px;border-radius:3px}

/* mobile: top bar replaces sidebar */
#topbar{display:none}
@media (max-width:900px){
  #side{display:none}
  #main{padding:16px 14px 70px}
  #topbar{display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:30;
    background:var(--panel);border-bottom:1px solid var(--line);padding:10px 14px}
  #topbar img{width:24px;height:24px;image-rendering:pixelated}
  #topbar .t{font-weight:800;font-size:15px}
  #topbar select{margin-left:auto;background:var(--ink);color:var(--text);border:1px solid var(--line);
    padding:6px 8px;font-family:inherit;font-size:13px;max-width:52vw}
}
:where(a,button,input,select,[tabindex]):focus-visible{outline:2px solid var(--amber);outline-offset:2px}
"""

JS = """
const SEARCH_DATA = __SEARCHDATA__;
const BASE = location.pathname.includes("/systems/") ? "../" : "";
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
  sres.innerHTML = out.length ? out.map(o =>
    `<button type="button" data-url="${o.e.url}"><b>${esc(o.e.title)}</b><span>${esc(o.s)}</span></button>`).join("")
    : `<button type="button" disabled><span>没有匹配的结果，换个词试试</span></button>`;
  sres.style.display = "block";
  sres.querySelectorAll("button[data-url]").forEach(b => b.onclick = () => location.href = BASE + b.dataset.url);
}
sbox.addEventListener("input", () => doSearch(sbox.value));
sbox.addEventListener("keydown", e => { if (e.key === "Enter") {
  const first = sres.querySelector("button[data-url]");
  if (first) location.href = BASE + first.dataset.url;
} });
document.addEventListener("click", e => { if (!e.target.closest("#side")) sres.style.display = "none"; });
// mobile page switcher
const sel = document.getElementById("pagesel");
if (sel) sel.addEventListener("change", () => location.href = BASE + sel.value);
"""


def page_shell(title, body, nav, nav_options, favicon="deed"):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 深空当铺 Wiki</title>
<link rel="icon" href="__P__assets/icons/{favicon}.png">
<style>{CSS}</style>
</head>
<body>
<div id="topbar"><img src="__P__assets/icons/deed.png" alt=""><span class="t">深空当铺 Wiki</span>
<select id="pagesel" aria-label="切换页面">{nav_options}</select></div>
<div id="layout">
<nav id="side">
  <div class="brand"><img src="__P__assets/icons/deed.png" alt=""><div><div class="t">深空当铺 Wiki</div><small>Probably Stolen</small></div></div>
  <input id="search" placeholder="搜索物品 / 页面" autocomplete="off">
  <div id="sresults"></div>
  {nav}
  <hr>
  <div class="sidefoot">交互产业链图见<a href="__P__graph.html">此处</a>。</div>
</nav>
<main id="main">
  <div class="hero" aria-hidden="true">__HERO__</div>
  <div class="doc" id="doc">{body}</div>
</main>
</div>
<script>{JS}</script>
</body>
</html>"""


def add_icons(body_html):
    def cell_repl(m):
        inner = m.group(1)
        mm = re.fullmatch(r"\s*<code>([a-z0-9_]+)</code>\s*", inner)
        if mm:
            iid = mm.group(1)
            sp = sprite_map.get(iid)
            img = f'<img class="icon" src="ICONSRC/{sp}.png" alt="" loading="lazy">' if sp and sp in icons else ""
            return f'<td id="item-{iid}">{img}<code>{iid}</code>'
        return m.group(0)
    return re.sub(r"<td>(.*?)</td>", cell_repl, body_html)


def md_links_to_html(md_text):
    return re.sub(r"(\[[^\]]*\])\(([^)]+?)\.md\)", lambda m: f"{m.group(1)}({m.group(2)}.html)", md_text)


# ---- pass 1: bodies ----
pages = []
for src, title, sprite in SRC:
    if src.endswith(".html"):
        pages.append({"file": src, "title": title, "sprite": sprite, "body": None})
        continue
    md = open(os.path.join(WIKI, src), encoding="utf-8").read()
    md = md_links_to_html(md)
    body = markdown.markdown(md, extensions=MD_EXT)
    body = add_icons(body)
    pages.append({"file": src[:-3] + ".html", "title": title, "sprite": sprite, "body": body})

# ---- nav ----
def href_of(f):
    return f if f.endswith(".html") else f[:-3] + ".html"

nav_html, nav_options = "", ""
for gname, items in GROUPS:
    nav_html += f'<div class="navgroup">{gname}</div><div class="nav">'
    for f, title, sprite in items:
        h = href_of(f)
        nav_html += f'<a href="{h}"><img src="__P__assets/icons/{sprite}.png" alt="">{title}</a>'
        nav_options += f'<option value="{h}">{title}</option>'
    nav_html += "</div>"

# ---- search index ----
search_index = []
for p in pages:
    if p["body"] is None:
        continue
    text = re.sub(r"<[^>]+>", " ", p["body"])
    text = re.sub(r"\s+", " ", text)[:4000]
    search_index.append({"title": p["title"], "url": p["file"], "text": text})
for it in items_db:
    t = f"{it.get('name_zh') or it['id']} {it['id']} 基准价{it.get('value')} 分类{' '.join(it.get('types') or [])} {it.get('note') or ''}"
    search_index.append({"title": f"{it.get('name_zh') or it['id']}", "url": f"items.html#item-{it['id']}", "text": t})

# ---- pass 2: write ----
for p in pages:
    if p["body"] is None:
        continue
    nav = nav_html.replace(f'href="{p["file"]}"', f'href="{p["file"]}" class="active"', 1)
    opts = nav_options.replace(f'value="{p["file"]}"', f'value="{p["file"]}" selected', 1)
    html = page_shell(p["title"], p["body"], nav, opts).replace("__SEARCHDATA__", json.dumps(search_index, ensure_ascii=False))
    if p["file"].startswith("systems/"):
        html = html.replace("__P__", "../").replace('src="ICONSRC/', 'src="../assets/icons/').replace('src="assets/icons/', 'src="../assets/icons/')
    else:
        html = html.replace("__P__", "").replace('src="ICONSRC/', 'src="assets/icons/')
    hero = "".join(f'<img src="{"../" if p["file"].startswith("systems/") else ""}assets/icons/{s}.png" alt="" loading="lazy">'
                   for s in HERO_SPRITES)
    html = html.replace("__HERO__", hero)
    out = os.path.join(WIKI, p["file"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    print("built", p["file"])

print(f"search entries: {len(search_index)} ({len(items_db)} items)")
