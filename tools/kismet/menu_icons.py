"""Give the restored maps their October 2022 selector icons.

The selector shows DT_LevelsReverse CreateScreen, a PaperSprite cut from the
MainMenu atlas texture. Both changed between v4 and v5 under the same names, so
the v4 atlas and sprites are copied under /Game/RevivalMaps/UI/ and only the
restored rows of DT_LevelsReverse point to them.
Run from revival/: python tools/kismet/menu_icons.py
"""
import sys
import json, os, subprocess
from pathlib import Path

REVIVAL = Path(__file__).resolve().parents[2]
UAG = str(REVIVAL / "tools/UAssetGUI-v1.1.0/UAssetGUI.exe")
REPAK = str(REVIVAL / "tools/repak-v0.2.3/repak.exe")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paks_key import KEY  # noqa: E402  (game pak AES key, not in the source)
V4_PAK = r"<games>/Propnight.v4.0.0.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak"
WORK = REVIVAL / "v4/spr"
OUT = REVIVAL / "modpak/RevivalMaps/Propnight/Content/RevivalMaps/UI"
OLD_DIR = "/Game/UI/Atlas/HorrorUI/MainMenu/"
NEW_DIR = "/Game/RevivalMaps/UI/"
ROWS = {  # DT row -> sprite number used by v4
    "Reborn_Farm_Main": 18, "Reborn_Mansion_MAIN": 51, "Reborn_School_Main": 52,
    "PN_SummerCamp_Arena_Main": 29, "Circus_Small_Main": 64, "Small_Abbey_Main": 50,
}


def get_v4(name):
    for ext in ("uasset", "uexp", "ubulk"):
        data = subprocess.run([REPAK, "-a", KEY, "get", V4_PAK, f"Propnight/Content/UI/Atlas/HorrorUI/MainMenu/{name}.{ext}"],
                              capture_output=True).stdout
        if data:
            (WORK / f"{name}.{ext}").write_bytes(data)


def convert(src_name, dst_name, replace):
    get_v4(src_name)
    j = WORK / f"{src_name}.json"
    subprocess.run([UAG, "tojson", str(WORK / f"{src_name}.uasset"), str(j), "VER_UE4_26"], check=True)
    text = j.read_text(encoding="utf-8")
    for a, b in replace:
        text = text.replace(a, b)
    out_json = WORK / f"{dst_name}.json"
    out_json.write_text(text, encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([UAG, "fromjson", str(out_json), str(OUT / f"{dst_name}.uasset")], check=True)
    print("wrote", dst_name, sorted(p.name for p in OUT.glob(dst_name + ".*")))


WORK.mkdir(parents=True, exist_ok=True)
atlas = [(f'"{OLD_DIR}MainMenu"', f'"{NEW_DIR}RM_MainMenu"'), ('"MainMenu"', '"RM_MainMenu"')]
convert("MainMenu", "RM_MainMenu", atlas)
for n in sorted(set(ROWS.values())):
    convert(f"MainMenu_Sprite_{n}", f"RM_Sprite_{n}", [
        (f'"{OLD_DIR}MainMenu_Sprite', f'"{NEW_DIR}RM_Sprite'),
        ('"MainMenu_Sprite', '"RM_Sprite'),
    ] + atlas)

# DT_LevelsReverse (already GameMode-edited copy): new imports + CreateScreen.
dt_json = REVIVAL / "modpak/DT_LevelsReverse.json"
d = json.loads(dt_json.read_text(encoding="utf-8"))
imports = d["Imports"]
for name in (NEW_DIR + "RM_Sprite", "RM_Sprite"):
    if name not in d["NameMap"]:
        d["NameMap"].append(name)
new_index = {}
for n in sorted(set(ROWS.values())):
    imports.append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": f"{NEW_DIR}RM_Sprite_{n}", "OuterIndex": 0,
                    "ClassPackage": "/Script/CoreUObject", "ClassName": "Package", "PackageName": None, "bImportOptional": False})
    pkg = -len(imports)
    imports.append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": f"RM_Sprite_{n}", "OuterIndex": pkg,
                    "ClassPackage": "/Script/Paper2D", "ClassName": "PaperSprite", "PackageName": None, "bImportOptional": False})
    new_index[n] = -len(imports)
table_export = next(e for e in d["Exports"] if e.get("Table"))
for row in table_export["Table"]["Data"]:
    if row["Name"] in ROWS:
        for p in row["Value"]:
            if p["Name"].startswith("CreateScreen_"):
                p["Value"] = new_index[ROWS[row["Name"]]]
# The table must load the new sprites before it is serialized, like the old ones.
deps = table_export.get("CreateBeforeSerializationDependencies")
if isinstance(deps, list):
    deps.extend(v for v in new_index.values() if v not in deps)
dt_json.write_text(json.dumps(d), encoding="utf-8")
dst = REVIVAL / "modpak/RevivalMaps/Propnight/Content/Blueprints/Server/DT_LevelsReverse.uasset"
subprocess.run([UAG, "fromjson", str(dt_json), str(dst)], check=True)
print("DT updated; new sprite imports:", new_index, "deps list:", "updated" if isinstance(deps, list) else "absent")
