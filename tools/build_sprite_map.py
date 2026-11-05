import os, re, json

SRC = r"D:\nazarick\probably-stolen-wiki\tools\rip\ExportedProject\Assets\Scripts\Assembly-CSharp"
OUT = r"D:\nazarick\probably-stolen-wiki\data\sprite_map.json"

def method_body(content, name):
    """Return body of first method named `name` (any class), by brace matching."""
    for m in re.finditer(rf"(?:public|private|protected|internal)[^\n]*\s{name}\s*\([^)]*\)\s*\{{", content):
        start = m.end() - 1
        depth = 0
        for i in range(start, len(content)):
            c = content[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return content[start:i + 1]
    return None

# 1. method name -> first sprite in body (only GameItem-returning helpers w/ sprite call)
method_sprite = {}
for fn in os.listdir(SRC):
    if not fn.endswith(".cs"):
        continue
    content = open(os.path.join(SRC, fn), encoding="utf-8", errors="ignore").read()
    for m in re.finditer(r"SetSpriteAndShape\(\"([^\"]+)\", \"([^\"]+)\"\)", content):
        pass  # counted below per method
    for mm in re.finditer(r"(?:public|private|protected|internal)[^\n]*?GameItem[^\n]*?\s(\w+)\s*\([^)]*\)\s*\{", content):
        name = mm.group(1)
        if name in method_sprite:
            continue
        start = mm.end() - 1
        depth = 0
        body = None
        for i in range(start, len(content)):
            c = content[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    body = content[start:i + 1]
                    break
        if body:
            sm = re.search(r"SetSpriteAndShape\(\"([^\"]+)\", \"([^\"]+)\"\)", body)
            if sm:
                method_sprite[name] = sm.group(2)

# 2. id -> factory method name from Add("id", () => Method())
id2sprite = {}
for fn in os.listdir(SRC):
    if not fn.endswith(".cs") or fn == "UnusedDirectory.cs":
        continue
    content = open(os.path.join(SRC, fn), encoding="utf-8", errors="ignore").read()
    for m in re.finditer(r'Add\("([\w]+)",\s*\(\)\s*=>\s*(\w+)\(\)\)', content):
        ident, meth = m.group(1), m.group(2)
        if ident not in id2sprite and meth in method_sprite:
            id2sprite[ident] = method_sprite[meth]

# also resolve X.Y() factory form like MachineWineRack.AgeWell
for m in re.finditer(r'Add\("([\w]+)",\s*\(\)\s*=>\s*(\w+)\.(\w+)\(\)\)', content):
    pass

json.dump(id2sprite, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
icons = os.listdir(r"D:\nazarick\probably-stolen-wiki\wiki\assets\icons")
have = sum(1 for v in id2sprite.values() if v + ".png" in icons)
print(f"mapped {len(id2sprite)} items to sprites; {have} sprites exist as png")
