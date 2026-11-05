import re, glob, json

TERM = [
    ("unitValue", "售价"), ("SEED_YIELD", "种子返还率"), ("WINE_SCORE_INT", "品质分"),
    ("AGE_INT", "酒龄"), ("WATER_QUALITY_SCORE", "水质分表"),
    ("GetPurityArrayIndex", "纯度档位"), ("GetMaxPurityCap", "纯度上限"), ("GetDirtBonus", "污垢加成"),
    ("GetOutputQuality", "产出水质"), ("GetAgingDays", "陈化天数"), ("GetCurrentStoreAttractiveness", "当前吸引力"),
    ("RunNightlyChemicalSimulation", "夜间化学模拟"), ("FreeNutrifruit", "株系解放"),
    ("AGE_WELL_QUALITY_PER_EXTRA_DAY=125", "每125品质加成+1天"), ("AGE_WELL_BASE_DAYS=1", "基础1天"),
    ("BASE_FERMENTATION_PERIOD", "基础发酵时长"), ("NUTRIFRUIT_SEED_RETURN", "种子返还数"),
    ("STARTING_HEIGHT=3", "起始高3"), ("MAX_SIZE=8", "上限8"),
    ("MACHINE_QUALITY_RATIO_INT", "品质系数"), ("CALIBER_12GAUGE=12", "12号口径"),
    ("Carnivore肉食", "肉食"), ("Herbivore植食", "植食"), ("Omnivore杂食", "杂食"),
    ("RNG.Roll", "随机判定"), ("IsMet", "判定"),
    ("GetRefurbishChance", "翻新成功率"), ("GetCurrentValue", "当前价值"),
    ("BASE_PREMIUM_PERCENT=50", "基础溢价50%"),
    ("GetWaterUsePerCycle", "每日耗水"),
    ("TryDrawCyclePower 8能量", "供电8能量"), ("TryDrawCyclePower", "供电判定"),
    ("SetTraitRank(infertile,0)", "不育清零"),
    ("GetMislabeledWaterWeight", "掺假权重"),
    ("IsLabelledHazardousWater", "危险水判定"), ("GetRandomWater", "随机水质"),
    ("RunRemediation", "水质修复"),
    ("GetWaterQualityScore", "水质分"), ("IsLethal", "致死判定"),
    ("GetSharedAirPercent", "共享空气占比"), ("IsExperiencedChemist", "经验化学家开局"),
    ("GetWineQualityTier", "品质档位"), ("FinishFermentation", "发酵完成"),
    ("FinishCounterfeitWine", "假酒发酵完成"),
    ("GetWaterPurity", "纯度"), ("WATER_PURITIES", "档位阈值"),
    ("IsWet", "湿润判定"), ("GetLethalDose", "致死剂量倍数"),
    ("MixTemperature", "混合温度"), ("AgableHelper", "陈化"),
    ("harvestItemId='hydroreed' 仅为贴图用，不存在该物品。", "收获物为滤芯与种子。"),
    ("harvestItemId='bloomberry' 仅为贴图用，实际产物为 wine_berry。", "实际产物为荧光莓。"),
    ("注册于UnusedDirectory但被活跃代码引用", "特殊弹药箱"),
]

def clean(text, aggressive=False):
    if not text:
        return text
    # 0. 术语映射
    for a, b in TERM:
        text = text.replace(a, b)
    # 1. 整句剔除：纯代码视角的从句/句子
    drop_patterns = [
        r"[（(][^（）()]*以代码为准[^（）()]*[）)]",
        r"[，；。][^。，；]*以代码为准[^。，；]*[。；]?",
        r"[（(][^（）()]*代码[^（）()]*[）)]",
        r"[（(][^（）()]*WIP[^（）()]*[）)]",
        r"[（(][^（）()]*贴图[^（）()]*[）)]",
        r"[（(][^（）()]*常量[^（）()]*[）)]",
        r"[（(][^（）()]*无调用点[^（）()]*[）)]",
        r"[（(][^（）()]*疑为死代码[^（）()]*[）)]",
        r"[（(][^（）()]*遗留代码[^（）()]*[）)]",
        r"注：代码[^。]*。",
        r"但代码[^。]*。",
        r"在代码中[^。，；]*[。，；]?",
        r"代码中[^。，；]*[。，；]?",
        r"从代码看[^。，；]*[。，；]?",
        r"代码未限制[^。，；]*[。，；]?",
        r"未在代码中[^。，；]*[。，；]?",
        r"代码无[^。，；]*[。，；]?",
    ]
    for p in drop_patterns:
        text = re.sub(p, "", text)
    # 2. 函数/方法名
    text = re.sub(r"`?\b(?:Get|Set|Run|Is|Can|Try|Add|Draw|Compute|Apply|Init|Create|Finish|Rush|Roll|Make|Build|Place|Handle|Have|Inherit|Expel|Destroy)[A-Z]\w*(?:\([^)]*\))?`?", "", text)
    text = re.sub(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\.(?:[A-Z][a-z]+)\(?", "", text)  # Xxx.Yyy(
    # 3. 裸常量 token
    text = re.sub(r"`?[A-Z][A-Z_0-9]{3,}(?:=[\w.]+)?`?", "", text)
    # 4. 类文件名
    text = re.sub(r"`?\w+\.(?:cs|json)`?", "", text)
    # 5. 标点修复
    text = re.sub(r"（\s*）|\(\s*\)", "", text)
    text = re.sub(r"[（(]\s*[,，；、]\s*", "（", text)
    text = re.sub(r"\s*[,，；、]\s*[）)]", "）", text)
    text = re.sub(r"[，；]\s*[。]", "。", text)
    text = re.sub(r"[：=]\s*[，；。]", "：", text)
    text = re.sub(r"[，；、]{2,}", "，", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"^[，；、。\s]+", "", text)
    return text.strip()

n_files = 0
for f in sorted(glob.glob('data/systems/*.json')):
    d = json.load(open(f, encoding='utf-8'))
    def walk(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k in ("note", "notes", "conditions", "name_zh", "desc_zh") and isinstance(v, str):
                    out[k] = clean(v)
                elif k == "mechanics" and isinstance(v, list):
                    out[k] = [clean(x) if isinstance(x, str) else walk(x) for x in v]
                else:
                    out[k] = walk(v)
            return out
        if isinstance(o, list):
            return [walk(x) for x in o]
        return o
    d2 = walk(d)
    d2["unresolved"] = [clean(u) for u in d2.get("unresolved", []) if clean(u)]
    json.dump(d2, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_files += 1

for f in sorted(glob.glob('wiki/systems/*.md') + ['wiki/mechanics.md', 'wiki/index.md']):
    s = open(f, encoding='utf-8').read()
    s2 = clean(s)
    if s2 != s:
        open(f, 'w', encoding='utf-8').write(s2)
        n_files += 1
print('processed files:', n_files)
