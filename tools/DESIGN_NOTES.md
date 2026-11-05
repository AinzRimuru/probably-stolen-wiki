# 设计备忘（深空当铺 Wiki 前端）

## 已确立的视觉语言（v2，2026-11 重设计）

- **配色全部取自游戏本体** `RenderHandler.ColorPalette` 枚举（hex 直接可读）：
  墨靛底 `#1a0b35`（Black #230f47 加深）、面板 `#230f47`、账本纸白 `#c4c4b0`（White）、
  靛青辅助 `#8397bb`（LightGray）、焦琥珀 `#ad6107`（Orange，唯一强调色，用于价签/激活态/H1 底线）、
  结构线 `#413d78`（VeryDarkGray）
- **系统色映射**（产业链图边/图例/导航）：酿酒 #be514c（Red）／净水 #429cbd（LightBlue）／制药 #9d5c9d（Purple）／水培 #7a9d4a（LightGreen）／枪支 #b8855a（LightOrange）／水产 #42a2aa（LightCyan）／杂项 #88948a（Gray）
- **导航与路线按钮一律用游戏原版像素精灵**（当票 deed=首页、模组=机制、信用点 coin=图鉴、芯片=产业链图、各系统用代表物品），禁用 emoji
- 物品表格 = 当铺账本：方角、琥珀表头、顶部 2px 琥珀规线、悬停行提亮；价格等数值可走等宽表格数字
- 字体只用系统 CJK 栈，个性来自字阶与琥珀铭牌式标题（H1 底部 3px 琥珀、H2 左 3px 琥珀），不引入网络字体（离线单文件约束）

## 教训（bug 记录）

- build_site.py 的 JS 块曾被 `.format()` 双花括号污染，换 f-string 插值时忘了还原单括号 → 整段脚本 SyntaxError 静默失效。**模板引擎切换时全文 grep `{{`**
- 替换占位符时 `assets/icons` 少了尾部斜杠 → 图标 404；`src="ICONSRC/` 占位符方案已稳定，别再改
- `<img loading="lazy">` 的 complete/naturalWidth 在未进视口时为 0，自动化测试会误报"损坏"
- **选精灵前先算亮度**：`coin.png` 竟是全透明空图（导航图标完全不可见）；16×64 长条精灵（酒瓶/水瓶）压扁成方块后不可辨认。规则：优先 32×32 左右的方形精灵；**衬底必须实色浅底 `#c4c4b0`（游戏 White），禁止半透明**——像素精灵普遍带黑描边，半透明浅底叠深紫面板后对深色像素对比度仅 1.9:1，实色衬底达 12:1；CSS 用 height 定宽 auto 保宽高比
- **一切名称以游戏本地化为准，禁止自造**：MACHINE_SHORT 曾自造"集水器"（官方=水分收集器）；"RAS" 是开发组英文缩写，中文本地化 0 次出现，玩家只见"循环水养殖系统"。注意官方 key 不都叫 `item_<id>_name`（3D打印机是 `item_3d_printer_name`、催陈器是 `item_age_well_name`、饲料分配器/动物笼/捕鼠夹/清洁机器人在 `livestock_/husbandry_` 前缀下）。图上工艺前缀、面板 machine_zh、MD 机器表三处都要跑比对脚本
- **本地化 `{0}` 占位符**：物品名里的 "x{0}/×{0}" 是运行时数量占位（如"3D打印机芯片（x{0} 红点瞄准镜）"），展示层要剥离；但 mech_/ui_/dialogue 文本的 {0} 是合法模板，**只允许清 `item_*_name` 键**——曾误清 511 个 key 后靠重跑 extract_loc.py 回滚
- **JS 字符串内嵌大 HTML 的两个坑**：① 换行符必须转义——用 `json.dumps(html)` 生成字符串字面量，禁止手工拼引号；② 内容里的 `</script>` 会让 HTML 解析器提前截断 script 块——`json.dumps` 后再 `.replace("</", "<\\/")`。另：模板占位符（如 `__GRAPHDOC__`）要确保 replace 作用在包含它的字符串上；iframe 内 const 不上 window，验证用 `frame.contentWindow.eval("typeof X")`
- **span 改 button 必须显式补 color/font**：浏览器按钮默认样式是黑字（buttontext）+系统字体。规则：凡是 createElement("button") 或标签改 button 的地方，对应 CSS 必须同时声明 `color` 和 `font-family: inherit`；上线前跑"全按钮对比度审计"（18+16 个控件实测 10~12:1）
- **无获取途径的物品一律不收录**：审计标准 = "定义外引用"（目录注册文件之外的 .cs 引用为零 = 死物）。已剔除 15 项：box_dispenser/test_gizmo/aug_chip/sign_berry/restricted_medical/blank_module/node_small/barrel/lottery_ticket_old（零引用死物）+ save_bag×5/tutorial_page（内部存档容器，ItemSpawnerHiddenList 隐藏名单坐实）。清单同步维护在三处：gen_items_page.py 的 HIDDEN、build_site.py 的 HIDDEN_ITEMS、build_graph.py 的 EXCLUDE_MACHINES。注意：剧情/事件发放的物品（许可证、证书、磁带、物资箱等）大量走 Helper/对话代码，不能只靠 vendor/loot 正则判断，先用引用审计甄别
- **工序节点必须带机器前缀**：配方名常与产物同名（成型机配方"山奈德片（毒药）" vs 物品"山奈德片"）。规则：节点标签 = 机器短名·核心名（去掉括号限定词），面板标题保留完整配方名 + 机器副标题；MACHINE_SHORT 映射表在 build_graph.py

## 有意不做的事

- 不加滚动入场动画/卡片悬浮动效（生成页通病）；动效只保留产业链粒子流（编码物料方向）与 reduced-motion 降级
- 不用 `A · B · C` 间隔号串接元信息、不在链接尾加 →、不加全大写字距标签
- 移动端不做汉堡菜单，用顶栏 <select> 换页（朴素但键盘/触屏都好用）
