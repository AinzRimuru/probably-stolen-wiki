#!/usr/bin/env python3
"""
深空当铺 wiki 物品注册表提取器 v2
从反编译源码 *Directory*.cs (+ PreBuiltItemHelper/PreBuildChemHelper/AquacultureItems) 提取全部注册物品:
id / 中文名 / 描述 / 风味文本 / unitValue / GameItemType / 所属目录
- value: 工厂链中最后一次字面量 unitValue 赋值 (含参数常量传播)
- types: 按调用顺序应用 SetGameItemType / RemoveGameItemType (递归追踪 Init* 辅助方法,
  if(字面量条件) 分支会求值, 运行时条件分支保守跳过)
输出: data/items.json
"""
import json
import os
import re
import sys
from collections import OrderedDict

SRC = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets\Scripts\Assembly-CSharp"
LOC_PATH = r"D:\nazarick\probably-stolen-wiki\data\localization.json"
OUT_PATH = r"D:\nazarick\probably-stolen-wiki\data\items.json"

ITEM_DIRECTORIES = [
    "AmenitiesItemDirectory", "ArmorItemDirectory", "ConstructionItemDirectory",
    "ContainerItemDirectory", "EquipmentDirectory", "ExplosiveItemDirectory",
    "FoodItemDirectory", "FurnitureItemDirectory", "GunModDirectory",
    "GunsItemDirectory", "HusbandryDirectory", "HydroponicDirectory",
    "KeyItemDirectory", "MaterialDirectory", "MedsItemDirectory",
    "MeleeWeaponItemDirectory", "MiscItemDirectory", "ModItemDirectory",
    "ModuleDirectory", "OrganDirectory", "RuinedMachineDirectory",
    "ShipItemDirectory", "ShipSystemDirectory", "TechnicianBackpackDirectory",
    "ToolDirectory", "WineDirectory", "PlayerAbilityItemDirectory",
    "StationMachinery",
]

DIR_NOTE = {
    "AmenitiesItemDirectory": "生活设施/装饰",
    "ArmorItemDirectory": "护甲",
    "ConstructionItemDirectory": "建筑材料",
    "ContainerItemDirectory": "容器",
    "EquipmentDirectory": "装备配件",
    "ExplosiveItemDirectory": "爆炸物",
    "FoodItemDirectory": "食物/饮料",
    "FurnitureItemDirectory": "机器/家具",
    "GunModDirectory": "枪械配件",
    "GunsItemDirectory": "枪械",
    "HusbandryDirectory": "畜牧业/水产",
    "HydroponicDirectory": "水培作物/种子",
    "KeyItemDirectory": "钥匙/门禁卡",
    "MaterialDirectory": "原料/材料",
    "MedsItemDirectory": "药物/医疗用品",
    "MeleeWeaponItemDirectory": "近战武器",
    "MiscItemDirectory": "杂项",
    "ModItemDirectory": "模组物品",
    "ModuleDirectory": "机器功能模组",
    "OrganDirectory": "器官",
    "RuinedMachineDirectory": "损坏机器",
    "ShipItemDirectory": "飞船",
    "ShipSystemDirectory": "飞船舱室/储藏区",
    "TechnicianBackpackDirectory": "技师背包部件",
    "ToolDirectory": "工具",
    "WineDirectory": "酿酒相关",
    "PlayerAbilityItemDirectory": "玩家能力物品",
    "StationMachinery": "空间站机器",
    "PreBuiltItemHelper": "预生成物品（含内容物）",
    "PreBuildChemHelper": "预灌装化学瓶变体",
}

# ---------- 文本处理 ----------

def read_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comments(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\' and j + 1 < n:
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            i = n if j == -1 else j + 2
            out.append(' ')
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def mask_strings(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\' and j + 1 < n:
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append('"' + 'x' * max(0, j - i - 1) + '"')
            i = j + 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def brace_block(masked, open_idx):
    depth = 0
    for k in range(open_idx, len(masked)):
        if masked[k] == '{':
            depth += 1
        elif masked[k] == '}':
            depth -= 1
            if depth == 0:
                return open_idx + 1, k, k
    return open_idx + 1, len(masked), len(masked)


# ---------- 方法索引 ----------

METHOD_RE = re.compile(
    r"^\t(?:(?:public|private|protected|internal|static|override|virtual|sealed|async|extern|readonly)\s+)*"
    r"(?P<ret>[\w<>\[\], \.]+?)\s+(?P<name>\w+)\s*\((?P<params>(?:[^()]|\([^()]*\))*)\)\s*\{",
    re.M,
)

KEYWORDS = {"if", "while", "for", "foreach", "switch", "using", "lock", "return",
            "new", "nameof", "typeof", "catch", "do", "else", "Add", "Empty"}


class MethodDef:
    __slots__ = ("cls", "name", "params", "ret", "body", "masked", "base_indent")

    def __init__(self, cls, name, params, ret, body, masked, base_indent):
        self.cls, self.name, self.params, self.ret = cls, name, params, ret
        self.body, self.masked, self.base_indent = body, masked, base_indent


def parse_file(path):
    raw = strip_comments(read_file(path))
    masked_full = mask_strings(raw)
    m = re.search(r"\bclass\s+(\w+)", raw)
    cls = m.group(1) if m else os.path.basename(path)[:-3]
    methods = []
    for m in METHOD_RE.finditer(masked_full):
        name = m.group("name")
        if name in KEYWORDS:
            continue
        s, e, _ = brace_block(masked_full, m.end() - 1)
        body, mb = raw[s:e], masked_full[s:e]
        base_indent = 1
        for ln in mb.split("\n"):
            if ln.strip():
                base_indent = len(ln) - len(ln.lstrip("\t"))
                break
        raw_params = raw[m.start("params"):m.end("params")]
        methods.append(MethodDef(cls, name, raw_params, m.group("ret").strip(), body, mb, base_indent))
    return cls, methods


print("Loading source files ...")
class_methods = {}
name_index = {}
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith(".cs"):
        continue
    cls, methods = parse_file(os.path.join(SRC, fn))
    d = class_methods.setdefault(cls, {})
    for md in methods:
        d[md.name] = md
        name_index.setdefault(md.name, [])
        if cls not in name_index[md.name]:
            name_index[md.name].append(cls)

# ---------- FishSpecies ----------

fish_map = {}
fs_path = os.path.join(SRC, "FishSpecies.cs")
if os.path.exists(fs_path):
    fs_raw = strip_comments(read_file(fs_path))
    fs_masked = mask_strings(fs_raw)
    for m in re.finditer(r"FishSpecies\s+(\w+)\s*=\s*new\s+FishSpecies", fs_raw):
        species = m.group(1)
        s, e, _ = brace_block(fs_masked, fs_masked.find("{", m.end() - 1))
        block = fs_raw[s:e]
        for f in ("fishIdentifier", "roeIdentifier", "fryIdentifier"):
            fm = re.search(f + r'\s*=\s*"([^"]+)"', block)
            if fm:
                fish_map[(species, f)] = fm.group(1)

# ---------- 本地化 ----------

# 人工核实覆盖: id -> 名称本地化 key (源码中经变量/属性链传递, 已逐条对照源码验证)
MANUAL_NAME_KEYS = {
    # PlantGeneticsHelper.DISK_BLANK_NAME => PlantGeneticsText.DiskName() => item_dna_disk_name
    "plant_dna_disk": "item_dna_disk_name",
    # IntelHelper.CreateRevCodeword: GetLocalizedUI("intel_rev_codeword_title") 经 CreatePaperWithText(title) 设为 name
    "rev_codeword": "intel_rev_codeword_title",
}

loc = json.load(open(LOC_PATH, encoding="utf-8"))

def zh(key):
    if not key:
        return None
    v = loc.get(key)
    if isinstance(v, dict):
        s = v.get("zh")
        return s if s else None
    return None

# ---------- Add 解析 ----------

def split_top_args(s):
    args, depth, cur = [], 0, []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = i + 1
            while j < len(s):
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == '"':
                    break
                j += 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    last = "".join(cur).strip()
    if last:
        args.append(last)
    return args


def parse_adds(method):
    results = []
    mk = method.masked
    for m in re.finditer(r"\bAdd\s*\(", mk):
        depth = 0
        k = m.end() - 1
        while k < len(mk):
            if mk[k] == "(":
                depth += 1
            elif mk[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        args = split_top_args(method.body[m.end():k])
        if len(args) < 2:
            continue
        id_expr, fact = args[0].strip(), args[1].strip()
        item_id = None
        mid = re.fullmatch(r'"([^"]+)"', id_expr)
        if mid:
            item_id = mid.group(1)
        else:
            mf = re.fullmatch(r"FishSpecies\.(\w+)\.(fishIdentifier|roeIdentifier|fryIdentifier)", id_expr)
            if mf:
                item_id = fish_map.get((mf.group(1), mf.group(2)))
        if item_id is None:
            continue
        lm = re.match(r"\(\)\s*=>\s*(.+)$", fact, re.S)
        expr = lm.group(1).strip() if lm else None
        results.append((item_id, expr, id_expr))
    return results


# ---------- 工厂解析 ----------

def literal_of(tok):
    tok = tok.strip()
    if re.fullmatch(r"\d+[LlFfDd]?", tok):
        return tok.rstrip("LlFfDd")
    if re.fullmatch(r'"[^"]*"', tok):
        return tok
    if tok in ("true", "false", "null"):
        return tok
    if re.fullmatch(r"\w+\.\w+", tok):
        return tok  # enum 字面量, 供 switch case 匹配
    return None


def param_names_and_defaults(params):
    """[(name, default_literal_or_None), ...]"""
    out = []
    for p in split_top_args(params):
        if not p.strip():
            continue
        pname, default = p, None
        if "=" in p:
            head, tail = p.split("=", 1)
            pname = head.strip()
            default = literal_of(tail.strip())
        name = pname.split()[-1].strip() if pname.split() else None
        if name:
            out.append((name, default))
    return out


def call_signature(expr):
    m = re.match(r"^(?:([\w\.]+?)\.)?(\w+)\s*\(", expr)
    if not m:
        return None
    qual, name = m.group(1), m.group(2)
    open_idx = expr.find("(", m.start(2))
    masked = mask_strings(expr)
    depth = 0
    k = open_idx
    while k < len(masked):
        if masked[k] == "(":
            depth += 1
        elif masked[k] == ")":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return qual, name, split_top_args(expr[open_idx + 1:k])


def resolve_factory(qual, name, cur_class):
    if qual:
        return class_methods.get(qual, {}).get(name)
    md = class_methods.get(cur_class, {}).get(name)
    if md:
        return md
    clss = name_index.get(name, [])
    cands = [c for c in clss if "GameItem" in class_methods[c][name].ret]
    if len(cands) == 1:
        return class_methods[cands[0]][name]
    return None


def args_to_literals(cargs, pdefs):
    """位置参数 + 命名参数 + 默认值 → {param: literal}"""
    lits = {name: dflt for name, dflt in pdefs if dflt is not None}
    pnames = [n for n, _ in pdefs]
    for idx, a in enumerate(cargs):
        a = a.strip()
        mm = re.match(r"^(\w+)\s*:\s*(.+)$", a, re.S)
        if mm and mm.group(1) in pnames:
            lit = literal_of(mm.group(2))
            if lit is not None:
                lits[mm.group(1)] = lit
            continue
        if idx < len(pnames):
            lit = literal_of(a)
            if lit is not None:
                lits[pnames[idx]] = lit
    return lits


LOC_KEY_RES = [
    ("name", re.compile(r'SetName\(\s*LocHelper\.GetLocalized(?:Item|Mechanic)\(\s*"([^"]+)"\s*\)')),
    ("name", re.compile(r'SetName\(\s*LocHelper\.GetLocalizedOrDefault\(\s*"[^"]*",\s*"([^"]+)"')),
    ("name", re.compile(r'\.name\s*=\s*LocHelper\.GetLocalized(?:Item|Mechanic|OrDefault|UI)\(\s*(?:"[^"]*",\s*)?"([^"]+)"')),
    ("name", re.compile(r'SetName\(\s*LocHelper\.GetLocalizedUI\(\s*"([^"]+)"')),
    ("desc", re.compile(r'shortDescription\s*=\s*LocHelper\.GetLocalizedUI\(\s*"([^"]+)"')),
    ("flavor", re.compile(r'flavorText\s*=\s*LocHelper\.GetLocalizedUI\(\s*"([^"]+)"')),
    ("desc", re.compile(r'shortDescription\s*=\s*LocHelper\.GetLocalized(?:Item|Mechanic|OrDefault)\(\s*(?:"[^"]*",\s*)?"([^"]+)"')),
    ("flavor", re.compile(r'flavorText\s*=\s*LocHelper\.GetLocalized(?:Item|Mechanic|OrDefault)\(\s*(?:"[^"]*",\s*)?"([^"]+)"')),
]
SET_TYPE = re.compile(r'\.SetGameItemType\(\s*"([^"]+)"\s*\)')
REMOVE_TYPE = re.compile(r'\.RemoveGameItemType\(\s*"([^"]+)"\s*\)')
UNIT_VALUE = re.compile(r"\.unitValue\s*=\s*([^;]+);")
SET_VALUE = re.compile(r"\.SetValue\(\s*(\d+)[Ll]?\s*\)")
NAME_ASSIGN_RE = re.compile(r"\.(name|shortDescription|flavorText)\s*=\s*([^;]+);")
EN_NAME_RE = re.compile(r'(?:\.name\s*=\s*|SetName\()\s*"([^"]+)"')
GETLOC_RE = re.compile(r'GetLocalized(?:Item|Mechanic|UI|OrDefault)\(\s*(?:"[^"]*",\s*)?"([^"]+)"')
UNIT_BASE_VALUE = re.compile(r"\.unitBaseValue\s*=\s*([^;]+);")
ARITH_RE = re.compile(r"^[\d\s\+\-\*/\(\)]+$")
SWITCH_RE = re.compile(r"^\s*switch\s*\((.+)\)\s*$")
CASE_RE = re.compile(r"^\s*case\s+([^:]+):\s*$")
DEFAULT_RE = re.compile(r"^\s*default\s*:\s*$")


def try_int_expr(tok):
    tok = tok.strip().rstrip("Ll").strip()
    if re.fullmatch(r"\d+", tok):
        return int(tok)
    if ARITH_RE.match(tok) and any(op in tok for op in "+-*/"):
        try:
            v = eval(tok.replace("/", "//"), {"__builtins__": {}}, {})
            if isinstance(v, int):
                return v
            if isinstance(v, float) and v == int(v):
                return int(v)
        except Exception:
            return None
    return None
BASE_REF = re.compile(r'DirectoryMaster\.Item\(\s*"([^"]+)"\s*\)|ItemSpawner\.Spawn\(\s*"([^"]+)"\s*\)')
IF_RE = re.compile(r"^\s*if\s*\((.+)\)\s*$")
ELSE_RE = re.compile(r"^\s*else\s*$")
ELSE_IF_RE = re.compile(r"^\s*else\s+if\s*\((.+)\)\s*$")
CALL_RE = re.compile(r"(?:([\w\.]+)\.)?(\w+)\s*\(")


def eval_bool(cond):
    c = cond.strip()
    while c.startswith("(") and c.endswith(")"):
        c = c[1:-1].strip()
    if c == "true":
        return True
    if c == "false":
        return False
    if c == "!true":
        return False
    if c == "!false":
        return True
    return None


class Analyzer:
    def __init__(self):
        self.helper_calls = 0

    def analyze(self, md, arg_literals=None, depth=0, seq=None):
        result = {"ops": [], "value": None, "base_value": None, "keys": {}, "base_refs": []}
        if md is None or depth > 5:
            return result
        if seq is None:
            seq = []
        body = md.body
        if arg_literals:
            for pname, lit in arg_literals.items():
                if lit is not None:
                    body = re.sub(r"\b" + re.escape(pname) + r"\b", lit, body)
        lines = body.split("\n")
        mlines = md.masked.split("\n")
        # 参数名替换后 masked 与 body 行数一致, 但内容未替换 —— 重新 mask
        mlines = mask_strings(body).split("\n")
        self.scan(md, lines, mlines, md.base_indent, depth, seq, result)
        return result

    def scan(self, md, lines, mlines, base_indent, depth, seq, result):
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            ml = mlines[i]
            indent = len(ml) - len(ml.lstrip("\t"))
            if indent > base_indent:
                i += 1
                continue
            if indent < base_indent:
                i += 1
                continue
            msw = SWITCH_RE.match(line)
            if msw:
                cond = msw.group(1).strip()
                blk = self.find_block(lines, mlines, i, base_indent)
                if blk is not None:
                    bs, be, nxt = blk
                    self.scan_switch(md, lines[bs:be], mlines[bs:be], base_indent + 1, cond, depth, seq, result)
                    i = nxt
                    continue
                i += 1
                continue
            mif = IF_RE.match(line)
            if mif:
                val = eval_bool(mif.group(1))
                # 找 if 块范围
                blk = self.find_block(lines, mlines, i, base_indent)
                if blk is not None:
                    bs, be, nxt = blk
                    if val is True:
                        self.scan(md, lines[bs:be], mlines[bs:be], base_indent + 1, depth, seq, result)
                    # else / else if
                    j = nxt
                    while j < n:
                        melse = ELSE_RE.match(lines[j])
                        melseif = ELSE_IF_RE.match(lines[j])
                        if not melse and not melseif:
                            break
                        if melseif:
                            val2 = eval_bool(melseif.group(1))
                            blk2 = self.find_block(lines, mlines, j, base_indent)
                            if blk2 and val2 is True:
                                self.scan(md, lines[blk2[0]:blk2[1]], mlines[blk2[0]:blk2[1]], base_indent + 1, depth, seq, result)
                            j = blk2[2] if blk2 else j + 1
                            continue
                        blk2 = self.find_block(lines, mlines, j, base_indent)
                        if blk2:
                            if val is False:
                                self.scan(md, lines[blk2[0]:blk2[1]], mlines[blk2[0]:blk2[1]], base_indent + 1, depth, seq, result)
                            j = blk2[2]
                        else:
                            j += 1
                    i = j if blk else i + 1
                    if blk:
                        i = blk[2]
                        # 再跳过已处理的 else 链
                        while i < n and (ELSE_RE.match(lines[i]) or ELSE_IF_RE.match(lines[i])):
                            b2 = self.find_block(lines, mlines, i, base_indent)
                            i = b2[2] if b2 else i + 1
                    continue
            # 普通语句
            self.statement(md, line, depth, seq, result)
            i += 1

    def find_block(self, lines, mlines, i, base_indent):
        """从 if/else 行 i 开始, 返回 (body_start, body_end, after_idx)"""
        n = len(lines)
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n:
            return None
        if lines[j].strip() != "{":
            return None
        depth = 0
        k = j
        while k < n:
            for ch in mlines[k]:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return j + 1, k, k + 1
            k += 1
        return None

    def scan_switch(self, md, lines, mlines, label_indent, cond, depth, seq, result):
        """按字面量条件匹配 case 段; 无法匹配时扫描 default 段"""
        n = len(lines)
        # 自动探测 case 标签缩进 (反编译代码 case 与 switch 同缩进)
        for k in range(n):
            if CASE_RE.match(lines[k]) or DEFAULT_RE.match(lines[k]):
                label_indent = len(mlines[k]) - len(mlines[k].lstrip("	"))
                break
        i = 0
        # 收集 case 段: (labels, stmt_start, stmt_end)
        segs = []
        cur_labels, cur_start = [], None
        while i < n:
            line = lines[i]
            mc = CASE_RE.match(line)
            md_ = DEFAULT_RE.match(line)
            ind = len(mlines[i]) - len(mlines[i].lstrip("	")) if mlines[i].strip() else -1
            if mc and ind == label_indent:
                if cur_start is not None:
                    segs.append((cur_labels, cur_start, i))
                cur_labels.append(mc.group(1).strip())
                cur_start = None
                i += 1
                continue
            if md_ and ind == label_indent:
                if cur_start is not None:
                    segs.append((cur_labels, cur_start, i))
                cur_labels.append("__default__")
                cur_start = None
                i += 1
                continue
            if cur_labels and cur_start is None and line.strip() and ind == label_indent + 1:
                cur_start = i
            i += 1
        if cur_labels and cur_start is not None:
            segs.append((cur_labels, cur_start, n))
        chosen = None
        for labels, ss, se in segs:
            if any(l == cond for l in labels):
                chosen = (ss, se)
                break
        if chosen is None:
            for labels, ss, se in segs:
                if "__default__" in labels:
                    chosen = (ss, se)
                    break
        if chosen is None:
            return
        ss, se = chosen
        stmts, stmts_m = [], []
        for k in range(ss, se):
            if not lines[k].strip():
                continue
            ind = len(mlines[k]) - len(mlines[k].lstrip("	"))
            if ind == label_indent + 1:
                stmts.append(lines[k])
                stmts_m.append(mlines[k])
        self.scan(md, stmts, stmts_m, label_indent + 1, depth, seq, result)

    def resolve_name_expr(self, expr):
        """解析 .name = X.Y() / 三元 else 分支 / return GetLocalized 链 → loc key"""
        expr = expr.strip()
        if "?" in expr and ":" in expr:
            expr = expr.split(":", 1)[1].strip().rstrip(")").strip()
        if '"' in expr:
            return None
        sig = call_signature(expr)
        if not sig:
            return None
        qual, name, cargs = sig
        if cargs:
            return None
        sub = resolve_factory(qual, name, "")
        if sub is None:
            return None
        keys = list(dict.fromkeys(GETLOC_RE.findall(sub.body)))
        if len(keys) == 1:
            return keys[0]
        if not keys:
            mret = re.findall(r"return\s+([\w\.]+\(\s*\))\s*;", sub.body)
            if mret:
                return self.resolve_name_expr(mret[0])
        return None

    def statement(self, md, line, depth, seq, result):
        for t in SET_TYPE.finditer(line):
            result["ops"].append(("set", t.group(1)))
        for t in REMOVE_TYPE.finditer(line):
            result["ops"].append(("remove", t.group(1)))
        for v in UNIT_VALUE.finditer(line):
            n = try_int_expr(v.group(1))
            if n is not None:
                result["value"] = n
        for v in SET_VALUE.finditer(line):
            result["value"] = int(v.group(1))
        for v in UNIT_BASE_VALUE.finditer(line):
            n = try_int_expr(v.group(1))
            if n is not None:
                result["base_value"] = n
        for kind, rgx in LOC_KEY_RES:
            for km in rgx.finditer(line):
                result["keys"].setdefault(kind, km.group(1))
        for km in NAME_ASSIGN_RE.finditer(line):
            kind = {"name": "name", "shortDescription": "desc", "flavorText": "flavor"}[km.group(1)]
            if not result["keys"].get(kind):
                key = self.resolve_name_expr(km.group(2))
                if key:
                    result["keys"].setdefault(kind, key)
        for km in EN_NAME_RE.finditer(line):
            result["keys"]["en_name"] = km.group(1)
        for bm in BASE_REF.finditer(line):
            result["base_refs"].append(bm.group(1) or bm.group(2))
        if depth >= 5:
            return
        for cm in CALL_RE.finditer(line):
            qual, cname = cm.group(1), cm.group(2)
            if cname in KEYWORDS:
                continue
            sub = resolve_factory(qual, cname, md.cls)
            if sub is None:
                continue
            if not (("GameItem" in sub.ret) or sub.ret in ("void", "Void")):
                continue
            sig = call_signature(line[cm.start():])
            if not sig:
                continue
            _, _, cargs = sig
            pdefs = param_names_and_defaults(sub.params)
            lits = args_to_literals(cargs, pdefs)
            key = (sub.cls, sub.name)
            if key in seq:
                continue
            if sub.ret in ("void", "Void"):
                self.helper_calls += 1
            sub_res = self.analyze(sub, lits, depth + 1, seq + [key])
            result["ops"].extend(sub_res["ops"])
            if sub_res["value"] is not None:
                result["value"] = sub_res["value"]
            for k2, v2 in sub_res["keys"].items():
                result["keys"].setdefault(k2, v2)
            result["base_refs"].extend(sub_res["base_refs"])
            break


def apply_ops(ops):
    types = []
    for op, t in ops:
        if op == "set" and t not in types:
            types.append(t)
        elif op == "remove" and t in types:
            types.remove(t)
    return types


analyzer = Analyzer()

# ---------- 第一遍: 目录物品 ----------
items = []
report = OrderedDict()
print("Extracting directories ...")
for dname in ITEM_DIRECTORIES:
    path = os.path.join(SRC, dname + ".cs")
    count = 0
    if os.path.exists(path):
        cls, methods = parse_file(path)
        init = next((md for md in methods if md.name == "InitDirectory"), None)
        if init:
            for item_id, expr, id_expr in parse_adds(init):
                res = {"ops": [], "value": None, "keys": {}, "base_refs": []}
                unresolved = None
                if expr:
                    sig = call_signature(expr)
                    if sig:
                        qual, name, cargs = sig
                        if qual in ("DirectoryMaster", "ItemSpawner") and name in ("Item", "Spawn"):
                            for a in cargs:
                                mm = re.fullmatch(r'"([^"]+)"', a.strip())
                                if mm:
                                    res["base_refs"].append(mm.group(1))
                                    break
                        else:
                            sub = resolve_factory(qual, name, dname)
                            if sub is not None and "GameItem" in sub.ret:
                                pdefs = param_names_and_defaults(sub.params)
                                lits = args_to_literals(cargs, pdefs)
                                res = analyzer.analyze(sub, lits, 0, [])
                            else:
                                unresolved = expr
                    else:
                        unresolved = expr
                items.append({"id": item_id, "directory": dname, "res": res, "unresolved": unresolved})
                count += 1
    report[dname] = count

# ---------- 第二遍: PreBuilt ----------
print("Extracting prebuilt items ...")
raw_pb = strip_comments(read_file(os.path.join(SRC, "PreBuiltItemHelper.cs")))
pb_count = 0
for m in re.finditer(r'\{\s*\n\s*"([^"]+)",\s*\n\s*\(\)\s*=>\s*([\w\.]+)\(\s*\)\s*\n\s*\}', raw_pb):
    item_id, fexpr = m.group(1), m.group(2)
    sig = call_signature(fexpr + "()")
    res = {"ops": [], "value": None, "keys": {}, "base_refs": []}
    if sig:
        qual, name, cargs = sig
        sub = resolve_factory(qual, name, "PreBuiltItemHelper")
        if sub is not None and "GameItem" in sub.ret:
            res = analyzer.analyze(sub, None, 0, [])
    items.append({"id": item_id, "directory": "PreBuiltItemHelper", "res": res, "unresolved": None})
    pb_count += 1
report["PreBuiltItemHelper"] = pb_count

chem_bases = [
    ("CreateFantaPrecusorBottle", "med_bottle_violet", "methylol 125ml + stabilizing_agent 125ml"),
    ("CreateAcidBottle", "med_bottle_red", "acid 250ml"),
    ("CreateBaseBottle", "med_bottle_blue", "base 250ml"),
    ("CreateReducingAgentBottle", "med_bottle_orange", "reducing_agent 250ml"),
    ("CreateLipobondAgentBottle", "med_bottle_small_pink", "lipobond_agent 150ml"),
    ("CreateMiniAlcoholBottle", "mini_bottle", "alcohol 175ml + water 75ml"),
]
chem_count = 0
for meth, base, contents in chem_bases:
    md = class_methods.get("PreBuildChemHelper", {}).get(meth)
    res = analyzer.analyze(md, None, 0, []) if md else {"ops": [], "value": None, "keys": {}, "base_refs": []}
    if base not in res["base_refs"]:
        res["base_refs"].append(base)
    items.append({"id": base, "directory": "PreBuildChemHelper", "res": res,
                  "unresolved": None, "chem_contents": contents})
    chem_count += 1
report["PreBuildChemHelper"] = chem_count

# ---------- 汇总 ----------
print("Assembling output ...")
dir_index = {}
for e in items:
    if e["directory"] not in ("PreBuiltItemHelper", "PreBuildChemHelper"):
        dir_index[e["id"]] = e

out = []
no_name = 0
for e in items:
    res = e["res"]
    item_id = e["id"]
    keys = res["keys"]
    name = zh("item_%s_name" % item_id) or zh(MANUAL_NAME_KEYS.get(item_id)) or zh(keys.get("name"))
    desc = zh("item_%s_desc" % item_id) or zh(keys.get("desc"))
    flavor = zh("item_%s_flavor" % item_id) or zh(keys.get("flavor"))
    value = res["value"]
    types = apply_ops(res["ops"])
    notes = []
    base = res["base_refs"][0] if res["base_refs"] else None

    # unitBaseValue 回退 (电池类: 实际价值随电量变化, unitBaseValue 为底价)
    if value is None and res.get("base_value") is not None:
        value = res["base_value"]
        notes.append("value 取 unitBaseValue=%d（电量类物品，实际价值随电量变化）" % value)

    if e["directory"] in ("PreBuiltItemHelper", "PreBuildChemHelper"):
        if value is None and base and base in dir_index:
            value = dir_index[base]["res"]["value"]
        if not types and base and base in dir_index:
            types = apply_ops(dir_index[base]["res"]["ops"])
        if name is None and base and base in dir_index:
            bk = dir_index[base]["res"]["keys"]
            name = zh("item_%s_name" % base) or zh(bk.get("name"))
            if name:
                notes.append("名称沿用基础物品 %s" % base)
        chem = e.get("chem_contents")
        if chem:
            notes.append("预灌装变体：%s 内含 %s（无独立ID，复用基础物品）" % (base, chem))
        else:
            notes.append(("预生成物品，基于 %s（数值/类型继承基础物品）" % base) if base else "预生成物品")
    else:
        if value is None and base and base in dir_index:
            bv = dir_index[base]["res"]["value"]
            if bv is None and dir_index[base]["res"].get("base_value") is not None:
                bv = dir_index[base]["res"]["base_value"]
            if bv is not None:
                value = bv
                notes.append("数值继承基础物品 %s" % base)
        if not types and base and base in dir_index:
            types = apply_ops(dir_index[base]["res"]["ops"])
            if types:
                notes.append("类型继承基础物品 %s" % base)
        note = DIR_NOTE.get(e["directory"], "")
        if note:
            notes.append(note)

    if name is None:
        no_name += 1
        en = keys.get("en_name")
        notes.append("无中文翻译（代码硬编码名: %s）" % en if en else "无中文翻译")
    if e.get("unresolved"):
        notes.append("工厂未能解析: %s" % e["unresolved"])

    rec = OrderedDict()
    rec["id"] = item_id
    rec["name_zh"] = name
    rec["desc_zh"] = desc
    if flavor:
        rec["flavor_zh"] = flavor
    rec["value"] = value
    rec["types"] = types
    rec["directory"] = e["directory"]
    rec["note"] = "；".join(notes) if notes else None
    out.append(rec)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("\n=== 目录统计 ===")
total = 0
for k, v in report.items():
    print("%-32s %d" % (k, v))
    total += v
print("%-32s %d" % ("TOTAL", total))
print("无中文名物品数:", no_name)
unres = [r for r in out if r["note"] and "工厂未能解析" in r["note"]]
print("工厂未解析:", len(unres), [r["id"] for r in unres][:20])
novalue = [r["id"] for r in out if r["value"] is None]
print("无 value 物品数:", len(novalue), novalue[:40])
notypes = [r["id"] for r in out if not r["types"]]
print("无 types 物品数:", len(notypes), notypes[:40])
print("void 辅助方法递归次数:", analyzer.helper_calls)
print("输出:", OUT_PATH)
