"""Give the character-select characters of a restored level the components of the current Blueprint.

The scene (NewLobbyV2) shows each player through a child actor (Player1..5, LobbyPlayerMesh_C).
A level stores those child actors' templates (..._GEN_VARIABLE_LobbyPlayerMesh_C_CAT_n) with the
components the Blueprint had when the level was cooked: 2022 levels have only DefaultSceneRoot and
PointLight, so the characters are spawned without their skeletal mesh (MainChar), weapons and effects,
and nothing shows in the lobby. The missing components are cloned from a current level's templates
(GoldenM_Main), the same way upgrade_props.py does for placed actors.

usage: python upgrade_lobby_chars.py TEMPLATE_LEVEL.json TARGET_LEVEL.json OUT.json
"""
import copy, json, sys

CLASS = "LobbyPlayerMesh_C"
NEW = ["MainChar", "WeaponL", "WeaponR", "NiagaraDoppel", "NiagaraRabbit"]
KEEP = ["DefaultSceneRoot"]
HEADER_REFS = ("ClassIndex", "SuperIndex", "TemplateIndex", "OuterIndex")
DEP_LISTS = ("SerializationBeforeSerializationDependencies", "CreateBeforeSerializationDependencies",
             "SerializationBeforeCreateDependencies", "CreateBeforeCreateDependencies")

tpl = json.load(open(sys.argv[1], encoding="utf-8"))
dst = json.load(open(sys.argv[2], encoding="utf-8"))
t_imp, t_exp = tpl["Imports"], tpl["Exports"]
d_imp, d_exp = dst["Imports"], dst["Exports"]
names = set(dst["NameMap"])


def cls_name(doc, e):
    ci = e.get("ClassIndex")
    return doc["Imports"][-ci - 1]["ObjectName"] if isinstance(ci, int) and ci < 0 else None


def imp_key(imports, i):
    x = imports[-i - 1]
    outer = imp_key(imports, x["OuterIndex"]) if x["OuterIndex"] < 0 else None
    return (x["ClassPackage"], x["ClassName"], x["ObjectName"], outer)


d_index = {imp_key(d_imp, -(n + 1)): -(n + 1) for n in range(len(d_imp))}


def ensure_import(t_index):
    key = imp_key(t_imp, t_index)
    if key in d_index:
        return d_index[key]
    src = copy.deepcopy(t_imp[-t_index - 1])
    if src["OuterIndex"] < 0:
        src["OuterIndex"] = ensure_import(src["OuterIndex"])
    d_imp.append(src)
    d_index[key] = -len(d_imp)
    return d_index[key]


def remap_ref(v, mapping):
    if not isinstance(v, int) or v == 0:
        return v
    return ensure_import(v) if v < 0 else mapping[v]


def remap(o, mapping):
    if isinstance(o, list):
        return [remap(x, mapping) for x in o]
    if not isinstance(o, dict):
        return o
    t = o.get("$type", "")
    out = {}
    for k, v in o.items():
        if k == "Value" and "ObjectPropertyData" in t and isinstance(v, int):
            out[k] = remap_ref(v, mapping)
        elif k == "Object" and "FDelegate" in t:
            out[k] = remap_ref(v, mapping)
        else:
            out[k] = remap(v, mapping)
    return out


for n in tpl["NameMap"]:
    if n not in names:
        dst["NameMap"].append(n)
        names.add(n)

# template: the first current character template that has every component
t_actor = None
for i, e in enumerate(t_exp):
    if cls_name(tpl, e) == CLASS:
        comps = {x["ObjectName"] for x in t_exp if x.get("OuterIndex") == i + 1}
        if all(n in comps for n in NEW + KEEP):
            t_actor = i + 1
            break
assert t_actor, "no complete LobbyPlayerMesh_C template in the template level"
t_comp = {e["ObjectName"]: i + 1 for i, e in enumerate(t_exp) if e.get("OuterIndex") == t_actor}
t_actor_data = {p["Name"]: p for p in t_exp[t_actor - 1]["Data"]}

actors = [i + 1 for i, e in enumerate(d_exp) if cls_name(dst, e) == CLASS]
upgraded = skipped = 0
for actor in actors:
    children = {e["ObjectName"]: i + 1 for i, e in enumerate(d_exp) if e.get("OuterIndex") == actor}
    if any(n in children for n in NEW) or not all(n in children for n in KEEP):
        skipped += 1
        continue
    mapping = {t_actor: actor}
    for n in KEEP:
        mapping[t_comp[n]] = children[n]
    first_new = len(d_exp) + 1
    for k, n in enumerate(NEW):
        mapping[t_comp[n]] = first_new + k
    for n in NEW:
        e = copy.deepcopy(t_exp[t_comp[n] - 1])
        for k in HEADER_REFS:
            e[k] = remap_ref(e.get(k, 0), mapping)
        for k in DEP_LISTS:
            e[k] = [remap_ref(v, mapping) for v in e.get(k) or []]
        e["Data"] = remap(e.get("Data"), mapping)
        d_exp.append(e)
    a = d_exp[actor - 1]
    data = [p for p in a["Data"] if p["Name"] not in NEW]
    at = next((i for i, p in enumerate(data) if p["Name"] == "RootComponent"), len(data))
    data[at:at] = [remap(copy.deepcopy(t_actor_data[n]), mapping) for n in NEW if n in t_actor_data]
    added = [mapping[t_comp[n]] for n in NEW]
    bcc = next((p for p in data if p["Name"] == "BlueprintCreatedComponents"), None)
    if bcc is not None and bcc.get("Value"):
        have = {x["Value"] for x in bcc["Value"]}
        for v in added:
            if v not in have:
                item = copy.deepcopy(bcc["Value"][0])
                item["Value"] = v
                bcc["Value"].append(item)
    a["Data"] = data
    deps = a.get("CreateBeforeSerializationDependencies") or []
    a["CreateBeforeSerializationDependencies"] = deps + [v for v in added if v not in deps]
    upgraded += 1

json.dump(dst, open(sys.argv[3], "w", encoding="utf-8"))
print(f"{CLASS}: {len(actors)} found, {upgraded} upgraded, {skipped} skipped")
