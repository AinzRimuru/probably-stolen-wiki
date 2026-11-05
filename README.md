# 深空当铺 (Probably Stolen) 合成路线 Wiki

游戏版本 **0.46D**（Questing Goose Studio）。全部数据反编译自游戏本体（Unity Mono 程序集 + 资源），数值均为代码常量。

## 目录结构

```
wiki/                    ← Wiki 页面（Markdown）
  index.md               首页：系统导航 + 核心生产链
  graph.html             🌐 交互式合成产业链图（Canvas 力导向动画）
  mechanics.md           通用机制（游戏日/电池/模组）
  items.md               物品图鉴（522 项可获得）
  systems/               七大生产系统页面
    wine.md              酿酒与陈化
    water.md             净水与集水
    pharma.md            制药与化学合成
    hydroponics.md       水培种植
    guns.md              枪支打印
    aquaculture.md       养鱼与畜牧
    misc-machines.md     熔炉/冰箱/售货机等其他生产机器
  assets/
    icons/               1156 张物品图标（按精灵名命名）
    graph-data.json/.js  产业链图数据（.js 供 file:// 直接打开用）

data/                    ← 结构化数据（JSON，供二次利用）
  items.json             全物品注册表
  systems/*.json         各系统配方与机制（含源码溯源、存疑标注）
  localization.json      本地化 key → 中英文

tools/                   ← 提取工具链
  rip/                   AssetRipper 导出的完整 Unity 工程（源码在
                         rip/ExportedProject/Assets/Scripts/Assembly-CSharp/）
  extract_loc.py         本地化提取
  extract_icons.py       图标裁剪
  gen_items_page.py      物品图鉴生成
  validate_refs.py       物品引用一致性校验
  scan_mb.py             MonoBehaviour 清点
  SPEC.md（根目录）       子任务数据提取规范
```

## 游戏版本更新后的再提取流程

1. 启动 `tools/assetripper/AssetRipper.GUI.Free.exe --headless --port 14000`
2. `POST /LoadFolder`（游戏 Data 目录）→ `POST /Export/UnityProject`（导出到 `tools/rip`）
3. `python tools/extract_loc.py`（重建 localization.json）
3. `python tools/extract_loc.py`（重建 localization.json）
4. `python tools/extract_icons.py`（重建图标）
5. `python tools/build_sprite_map.py` + `python tools/extract_obtainable.py` + `python tools/build_graph.py`（图标映射、获取途径证据、产业链图数据）
6. `python tools/build_site.py`（把 wiki/*.md 渲染成同目录 .html 网页，配色取自游戏 UI 调色板 RenderHandler.ColorPalette）
7. `python tools/build_singlefile.py`（可选：打包成单文件 `wiki/probably-stolen-wiki-standalone.html`，图标/搜索/产业链图全部 base64 内嵌）
8. `python tools/build_graph_singlefile.py`（可选：产业链图单文件版 `wiki/chain-graph-standalone.html`）
9. 对照 `data/systems/*.json` 的 `source_files` 复核代码变化，更新 JSON 与 wiki 页，再跑 `build_site.py`（如需单文件版再跑 `build_singlefile.py` / `build_graph_singlefile.py`）
10. `python tools/validate_refs.py`（校验引用一致性）

## 数据可信度

- 配方输入/输出/数量/耗时/耗电：直接抄录代码常量
- 品质与产率公式：按代码逻辑复原，常量名保留（如 `WINE_SCORE_INT`）
- 每个系统 JSON 的 `unresolved` 字段记录了未定结论（多为游戏文本与代码矛盾处）
- 废弃内容（UnusedDirectory.cs 及无引用代码）已排除，个别疑似开发用途机器（纸箱机）单独标注
