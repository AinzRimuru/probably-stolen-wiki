# 深空当铺 (Probably Stolen) Wiki 数据提取规范 v1

游戏版本: 0.46D (Questing Goose Studio)

## 路径

- 反编译源码: `tools/rip/ExportedProject/Assets/Scripts/Assembly-CSharp/`（下称 SRC）
- 本地化映射: `data/localization.json`，格式 `{key: {"zh": 中文, "en": English}}`
- 你产出的结构化数据: `data/systems/<系统英文名>.json`
- 你产出的 wiki 页面: `wiki/systems/<系统英文名>.md`
- 输出目录不存在时先创建

## 本地化 key 规则

- 物品名: `item_<identifier>_name`，短描述: `item_<identifier>_desc`，风味文本: `item_<identifier>_flavor`
- 机器/机制: `mech_*`
- 界面: `ui_*`
- 查询中文名时务必用 localization.json 反查；JSON 里没有的 key 就用 identifier 原文并在 note 里标注"无中文翻译"

## 代码模型要点（务必先读这些类建立认知）

- `GameItem`: 所有物品。`identifier` 是稳定英文 ID；`unitValue` 是基准单价；`SetGameItemType("FOOD")` 设分类；`EnableTag("XX_TAG")` 打标签。
- `Directory<T>` / `DirectoryMaster`: 物品注册表。`Add("identifier", () => Factory())` 注册工厂，工厂方法里定义该物品的一切属性。
- `FurnitureItemDirectory.cs` 注册所有机器（熔炉/水培/打印机/净水器/催陈器等）。
- 机器的产能逻辑通常在 `Machine*.cs`（窗口/槽位布局）和 `*Helper.cs`（规则计算）里。
- `onCycleEndSlotItemFunc` / `onDayEnd*` = 每游戏日（周期）结算。时间一律换算成"游戏日"。
- `MachineHelper.SetupBatterySlot` + `TryDrawCyclePower` = 每次运作耗电（电池标签 `power_source_item`）。
- 模组槽 `SetupModuleBay` + `MachineryHelper.GetCurrentQualityBonus` 等影响产量/品质。
- `UnusedDirectory.cs` 是废弃/未启用内容，**不要**纳入，除非有活跃代码引用它。

## JSON schema（data/systems/<系统>.json）

```json
{
  "system": "<系统中文名>",
  "version": "0.46D",
  "source_files": ["<你读过的 SRC 下文件名>"],
  "machines": [
    {
      "id": "<identifier>",
      "name_zh": "<中文名>",
      "desc_zh": "<一句话用途>",
      "value": 0,
      "power": "<耗电描述，如 每周期1电池>",
      "recipes": [
        {
          "name": "<配方/过程名>",
          "inputs": [{"id": "<identifier 或 tag>", "name_zh": "<中文名>", "amount": 1, "note": ""}],
          "outputs": [{"id": "", "name_zh": "", "amount": 1, "note": ""}],
          "time": "<耗时，如 4游戏日 / 1周期>",
          "conditions": "<触发条件，品质需求等>",
          "notes": "<细节：品质影响、产率、副产物、失败条件>"
        }
      ]
    }
  ],
  "mechanics": ["<系统级机制，逐条中文说明，如品质分数的精确计算式>"],
  "items": [
    {"id": "<identifier>", "name_zh": "", "desc_zh": "", "value": 0, "note": "<在本系统中的角色>"}
  ],
  "unresolved": ["<没看懂/需要人工确认的点>"]
}
```

- inputs/outputs 的 id 用物品 identifier；若输入是"任意带某标签的物品"（tag 过滤），id 写 `tag:<TAG>` 并在 note 里列出满足该标签的具体物品（用 grep 查标签启用处）。
- 数量必须从代码常量抄录，不许猜。液量单位是 µL（如 750000 = 750ml）；JSON 里 note 换算成 ml。
- 品质/分数公式用中文写清楚，但保留代码常量名（如 `WINE_SCORE_INT`）。

## wiki 页面模板（wiki/systems/<系统>.md）

用中文撰写，结构：

```markdown
# <系统中文名>

> 一句话概述本系统在游戏中的作用。

## 机器与设备
（表格：中文名 | 英文ID | 基准价 | 耗电 | 用途）

## 合成/加工配方
按机器分小节，每个配方用表格：
| 输入 | 数量 | 输出 | 数量 | 耗时 | 备注 |

## 机制详解
（品质公式、天数、电力、模组加成、特殊规则——用列表和小表格，公式要精确）

## 相关物品
（表格：中文名 | 英文ID | 基准价 | 说明）
```

- 所有物品名用中文名（从 localization.json），后跟 `(id)`。
- 数据必须与你的 JSON 完全一致。
- 页面开头加 `版本: 0.46D` 与数据来源说明（反编译自游戏代码）。

## 质量要求

- 逐文件通读分配给你的源码，lambda 内的逻辑也要追（尤其 `onCycleEndSlotItemFunc`、`SetCraftingFunc`、`mayInventoryAddItemFunc`）。
- 输入输出物品要顺藤摸瓜：grep 它的 identifier 找到定义它的工厂方法，确认中文名与单价。
- 宁可标 `unresolved` 也不要编造数值。
