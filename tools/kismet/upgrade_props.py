"""Give actors placed in a v2 (February 2022) level the component set of the current Blueprints.

Cooked levels store placed actors' components, so actors placed before a
Blueprint gained components have none of them and the Blueprint aborts on the
missing references:

- BasePropBP_C: DestroyedPropStaticMesh, SpawnParticleLocation, Arrow and the
  Looper, Timeline_0 and TimelineOutline timelines (no physics, no destruction).
- NewLobbyV2_C (character select scene): Surv5..8 / SurvPF1..8 points and
  TextRender3 (empty scene, no characters).

The missing components are cloned from an actor of the same class in a v4 level
(which works with the current class) onto every actor of the target level.

usage: python upgrade_props.py PROP_TEMPLATE.json TARGET_LEVEL.json OUT.json [LOBBY_TEMPLATE.json]
"""
import copy, json, sys

UPGRADES = [
    # (class, components to clone, components the clones may reference and the target must have)
    ("BasePropBP_C", ["Arrow", "SpawnParticleLocation", "DestroyedPropStaticMesh", "Looper", "Timeline_0", "TimelineOutline"],
     ["Box", "PropStaticMesh", "ShakeTimeline"]),
    ("NewLobbyV2_C", ["Surv5-1", "Surv5-2", "Surv6-1", "Surv7-1", "Surv8-1"] + [f"SurvPF{n}" for n in range(1, 9)] + ["TextRender3"],
     ["KillerVisible", "SurvVisible"]),
]

dst = json.load(open(sys.argv[2], encoding="utf-8"))
d_imp, d_exp = dst["Imports"], dst["Exports"]
names = set(dst["NameMap"])

HEADER_REFS = ("ClassIndex", "SuperIndex", "TemplateIndex", "OuterIndex")
DEP_LISTS = ("SerializationBeforeSerializationDependencies", "CreateBeforeSerializationDependencies",
             "SerializationBeforeCreateDependencies", "CreateBeforeCreateDependencies")


def cls_name(doc, e):
    ci = e.get("ClassIndex")
    return doc["Imports"][-ci - 1]["ObjectName"] if isinstance(ci, int) and ci < 0 else None


# --- imports: same (package, class, name, outer chain) in both files
def imp_key(imports, i):
    x = imports[-i - 1]
    outer = imp_key(imports, x["OuterIndex"]) if x["OuterIndex"] < 0 else None
    return (x["ClassPackage"], x["ClassName"], x["ObjectName"], outer)


d_index = {imp_key(d_imp, -(n + 1)): -(n + 1) for n in range(len(d_imp))}


def upgrade(tpl, cls, new, keep):
    t_imp, t_exp = tpl["Imports"], tpl["Exports"]

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
        if v < 0:
            return ensure_import(v)
        return mapping[v]

    def remap(o, mapping):
        """Rewrite object references (imports and template exports) inside a JSON value."""
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

    actors = [i + 1 for i, e in enumerate(d_exp) if cls_name(dst, e) == cls]
    if not actors:
        return actors, 0, 0
    # Every FName of the template becomes available to the written package.
    for n in tpl["NameMap"]:
        if n not in names:
            dst["NameMap"].append(n)
            names.add(n)

    t_actor = next(i for i, e in enumerate(t_exp) if cls_name(tpl, e) == cls) + 1
    t_comp = {e["ObjectName"]: i + 1 for i, e in enumerate(t_exp) if e.get("OuterIndex") == t_actor}
    assert all(n in t_comp for n in new + keep), t_comp
    t_actor_data = {p["Name"]: p for p in t_exp[t_actor - 1]["Data"]}

    upgraded = skipped = 0
    for actor in actors:
        children = {e["ObjectName"]: i + 1 for i, e in enumerate(d_exp) if e.get("OuterIndex") == actor}
        if any(n in children for n in new) or not all(n in children for n in keep):
            skipped += 1
            continue
        mapping = {t_actor: actor}
        for n in keep:
            mapping[t_comp[n]] = children[n]
        first_new = len(d_exp) + 1
        for k, n in enumerate(new):
            mapping[t_comp[n]] = first_new + k
        for n in new:
            e = copy.deepcopy(t_exp[t_comp[n] - 1])
            for k in HEADER_REFS:
                e[k] = remap_ref(e.get(k, 0), mapping)
            for k in DEP_LISTS:
                e[k] = [remap_ref(v, mapping) for v in e.get(k) or []]
            e["Data"] = remap(e.get("Data"), mapping)
            d_exp.append(e)
        a = d_exp[actor - 1]
        data = [p for p in a["Data"] if p["Name"] not in new]
        at = next((i for i, p in enumerate(data) if p["Name"] == "RootComponent"), len(data))
        data[at:at] = [remap(copy.deepcopy(t_actor_data[n]), mapping) for n in new]
        added = [mapping[t_comp[n]] for n in new]
        bcc = next((p for p in data if p["Name"] == "BlueprintCreatedComponents"), None)
        t_bcc = t_actor_data["BlueprintCreatedComponents"]
        if bcc is None or all(x["Value"] in mapping for x in t_bcc["Value"]):
            # the template list only names cloned/kept components: take it as is
            data = [p for p in data if p["Name"] != "BlueprintCreatedComponents"]
            data.append(remap(copy.deepcopy(t_bcc), mapping))
        else:
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
    return actors, upgraded, skipped


prop_tpl = json.load(open(sys.argv[1], encoding="utf-8"))
templates = {"BasePropBP_C": prop_tpl}
if len(sys.argv) > 4:
    templates["NewLobbyV2_C"] = json.load(open(sys.argv[4], encoding="utf-8"))
report = []
prop_actors = []
for cls, new, keep in UPGRADES:
    if cls not in templates:
        continue
    actors, upgraded, skipped = upgrade(templates[cls], cls, new, keep)
    if cls == "BasePropBP_C":
        prop_actors = actors
    if actors or cls == "BasePropBP_C":
        report.append(f"{cls}: {len(actors)} found, {upgraded} upgraded, {skipped} skipped")

# Props whose mesh was relocated to its v2 version (/Game/RevivalV2/...) go back
# to the current mesh without their v2 OverrideMaterials: destruction takes a
# current "destroyed" mesh from a data table and copies the intact prop's
# materials onto it, so a v2 mesh/material broke the texture once destroyed.
# Decoration (non-prop meshes) keeps the v2 version.
RELOC = "/Game/RevivalV2/"


def find_or_add_import(class_package, class_name, object_name, outer):
    for n, x in enumerate(d_imp):
        if (x["ClassPackage"], x["ClassName"], x["ObjectName"], x["OuterIndex"]) == (class_package, class_name, object_name, outer):
            return -(n + 1)
    if object_name not in names:
        dst["NameMap"].append(object_name)
        names.add(object_name)
    d_imp.append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": object_name, "OuterIndex": outer,
                  "ClassPackage": class_package, "ClassName": class_name, "PackageName": None, "bImportOptional": False})
    return -len(d_imp)


restored = 0
prop_set = set(prop_actors)
for e in d_exp:
    if e.get("OuterIndex") not in prop_set or e["ObjectName"] != "PropStaticMesh":
        continue
    mesh = next((p for p in e.get("Data") or [] if p["Name"] == "StaticMesh"), None)
    if not mesh or not isinstance(mesh.get("Value"), int) or mesh["Value"] >= 0:
        continue
    obj = d_imp[-mesh["Value"] - 1]
    pkg = d_imp[-obj["OuterIndex"] - 1] if obj["OuterIndex"] < 0 else None
    if not pkg or not pkg["ObjectName"].startswith(RELOC):
        continue
    current_pkg = "/Game/" + pkg["ObjectName"][len(RELOC):]
    new_pkg = find_or_add_import("/Script/CoreUObject", "Package", current_pkg, 0)
    new_obj = find_or_add_import(obj["ClassPackage"], obj["ClassName"], obj["ObjectName"], new_pkg)
    old = mesh["Value"]
    mesh["Value"] = new_obj
    e["Data"] = [p for p in e["Data"] if p["Name"] != "OverrideMaterials"]
    for k in DEP_LISTS:
        e[k] = [new_obj if v == old else v for v in e.get(k) or []]
    restored += 1

json.dump(dst, open(sys.argv[3], "w", encoding="utf-8"))
print("; ".join(report) + f"; {restored} props back on current meshes; imports {len(d_imp)}, exports {len(d_exp)}")
