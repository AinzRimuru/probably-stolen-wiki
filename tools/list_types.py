import dnfile
from dnfile import dnPE

path = r"D:\Program Files (x86)\Steam\steamapps\common\Probably Stolen\Probably Stolen_Data\Managed\Assembly-CSharp.dll"
pe = dnPE(path)

names = []
for t in pe.net.mdtables.TypeDef:
    ns = str(t.TypeNamespace) if t.TypeNamespace else ""
    n = str(t.TypeName)
    names.append((ns, n))


# print all, grouped
for ns, n in sorted(set(names)):
    print(f"{ns}.{n}" if ns else n)
