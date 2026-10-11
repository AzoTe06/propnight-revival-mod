"""Build revival/modpak/RevivalMaps.pak (restored maps for the current game).

Run from revival/ after the dependency lists exist:
  MSYS_NO_PATHCONV=1 python tools/kismet/deps.py --src v4 --out v4/needed.txt <v4 roots>
  MSYS_NO_PATHCONV=1 python tools/kismet/deps.py --src v2 --have v4/needed.txt --out v2/needed.txt <v2 roots>
  python tools/kismet/build_modpak.py [maps|menu|all]

Contents: package files from v4/needed.txt and v2/needed.txt, the v4 MainMenu
atlas and sprites renamed under /Game/RevivalMaps/UI/ (the same names show
other images in the current game), and DT_LevelsReverse with the restored rows
listed in the selector (GameMode 2) and pointed at those sprites.
"""
import sys
import json, os, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REVIVAL = Path(__file__).resolve().parents[2]
UAG = str(REVIVAL / "tools/UAssetGUI-v1.1.0/UAssetGUI.exe")
REPAK = str(REVIVAL / "tools/repak-v0.2.3/repak.exe")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paks_key import KEY  # noqa: E402  (game pak AES key, not in the source)
from game_root import GAME_PAK  # noqa: E402  (reference install)
CURRENT_PAK = str(GAME_PAK)
PAKS = {
    "v4": r"<games>/Propnight.v4.0.0.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
    "v2": r"<games>/Propnight.v2.0.1.Steam/Propnight.v2.0.1.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
}
STAGE = REVIVAL / "modpak/RevivalMaps"        # frozen: restored maps and their assets
MENU_STAGE = REVIVAL / "modpak/RevivalMenu"    # versioned, classic maps DLC: selector list with them, icons, names
BASE_STAGE = REVIVAL / "modpak/RevivalMenuBase"  # versioned, every player: the game's own selector list, sorted
UI_OUT = MENU_STAGE / "Propnight/Content/RevivalMaps/UI"
WORK = REVIVAL / "v4/spr"
OLD_DIR = "/Game/UI/Atlas/HorrorUI/MainMenu/"
NEW_DIR = "/Game/RevivalMaps/UI/"
# DT_LevelsReverse row -> v4 MainMenu sprite shown in the selector.
ROWS = {
    "Reborn_Mansion_MAIN": 51,                  # v4
    "PropNight_Map_TEST3_Farm_Day_MERGED": 18,  # v2 day farm (v2 had no selector icons)
    "PropNight_Map_TEST5_School": 52,           # v2 school
}


# Map names shown in the selector: the restored v2 farm is the daytime farm and
# the current BigFarm the night one. The game has no "day"/"night" strings, so
# new keys are added to every Game.locres (farm word from the game's own text).
FARM_WORD_KEY = "57A5399E4E9236B70A3CD390F705E308"
RENAMES = {  # row -> (key, English source, index in DAY_NIGHT)
    "PropNight_Map_TEST3_Farm_Day_MERGED": ("RevivalFarmDay", "Farm (Day)", 0),
    "BigNew_Farm_Main": ("RevivalFarmNight", "Farm (Night)", 1),
}
# Restored maps named like a current one: the game's own (translated) name + the year, so the
# two are told apart in every language without new translations. row -> (key, English, name key, suffix)
# (The 2022 Summer Camp was listed as "Camp (2022)": removed, the last build has its own Camp.)
YEAR_RENAMES = {}
DAY_NIGHT = {  # language -> (farm word fallback, day, night, opening, closing)
    "da": (None, "dag", "nacht", " (", ")"),  # this locale holds Dutch text
    "de": (None, "Tag", "Nacht", " (", ")"),
    "en": (None, "Day", "Night", " (", ")"),
    "es-419": ("Granja", "día", "noche", " (", ")"),
    "es": (None, "día", "noche", " (", ")"),
    "fr": (None, "jour", "nuit", " (", ")"),
    "it": (None, "giorno", "notte", " (", ")"),
    "ja": (None, "昼", "夜", "（", "）"),
    "ko": (None, "낮", "밤", " (", ")"),
    "pl": (None, "dzień", "noc", " (", ")"),
    "pt-BR": (None, "dia", "noite", " (", ")"),
    "pt": ("Fazenda", "dia", "noite", " (", ")"),
    "ru": (None, "день", "ночь", " (", ")"),
    "sv": (None, "dag", "natt", " (", ")"),
    "tr": (None, "gündüz", "gece", " (", ")"),
    "zh-Hans": (None, "白天", "夜晚", "（", "）"),
    "zh-Hant": (None, "白天", "夜晚", "（", "）"),
}


def localization():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import locres_edit
    for lang, (fallback, day, night, op, cl) in DAY_NIGHT.items():
        # always the reference game's own text (a cached copy would bring back an older build's)
        src = WORK / "loc" / lang / "Game.locres"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(subprocess.run([REPAK, "-a", KEY, "get", CURRENT_PAK,
                                        f"Propnight/Content/Localization/Game/{lang}/Game.locres"], capture_output=True, check=True).stdout)
        loc = locres_edit.load(src)
        farm = fallback or next((k[3] for n in loc.namespaces if n[1] == "" for k in n[2] if k[1] == FARM_WORD_KEY), "Farm")
        farm = farm.strip()
        for key, source, which in RENAMES.values():
            loc.set("", key, source, f"{farm}{op}{(day, night)[which]}{cl}")
        for key, source, name_key, suffix in YEAR_RENAMES.values():
            name = next((k[3] for n in loc.namespaces if n[1] == "" for k in n[2] if k[1] == name_key), None)
            loc.set("", key, source, (name.strip() if name else source.split(" (")[0]) + suffix)
        out = MENU_STAGE / f"Propnight/Content/Localization/Game/{lang}/Game.locres"
        out.parent.mkdir(parents=True, exist_ok=True)
        loc.save(out)
    print("localized names:", list(DAY_NIGHT))


def get(src, entry, out):
    data = subprocess.run([REPAK, "-a", KEY, "get", PAKS[src], entry], capture_output=True).stdout
    if not data:
        return entry
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def copy_packages():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    jobs = []
    for src in ("v4", "v2"):
        for e in (l.strip() for l in open(REVIVAL / src / "needed.txt")):
            if e:
                jobs.append((src, e, STAGE / e))
    with ThreadPoolExecutor(8) as ex:
        failed = [r for r in ex.map(lambda j: get(*j), jobs) if r]
    print(f"package files: {len(jobs)}, failed: {failed[:5]}")


def fromjson(j, dst):
    """UAssetGUI fromjson exits with 0 even when it fails and writes nothing, so
    write next to the target and only replace it when the new files exist."""
    dst = Path(dst)
    tmp = dst.with_name(dst.stem + ".__new" + dst.suffix)
    for f in dst.parent.glob(dst.stem + ".__new.*"):
        f.unlink()
    subprocess.run([UAG, "fromjson", str(j), str(tmp)], check=True, capture_output=True)
    if not tmp.exists():
        raise RuntimeError(f"UAssetGUI could not write {dst.name} from {Path(j).name}")
    for f in dst.parent.glob(dst.stem + ".__new.*"):
        f.replace(dst.with_suffix(f.suffix))


def relocate_v2():
    """Art assets changed since February 2022 (v2/relocate.txt: meshes, materials,
    textures whose data differs from the current game) are shipped in their v2
    version under /Game/RevivalV2/ and the v2 packages are pointed at them, so v2
    maps get their original look while the current maps keep theirs."""
    import re
    reloc = [l.strip() for l in open(REVIVAL / "v2/relocate.txt", encoding="utf-8") if l.strip()]
    new_path = {p.lower(): "/Game/RevivalV2/" + p[len("/Game/"):] for p in reloc}
    moved = 0
    for e in (l.strip() for l in open(REVIVAL / "v2/needed.txt", encoding="utf-8")):
        stem = os.path.splitext(e)[0]
        pkg = "/Game/" + stem[len("Propnight/Content/"):]
        if pkg.lower() in new_path:
            dst = STAGE / ("Propnight/Content/RevivalV2/" + e[len("Propnight/Content/"):])
            dst.parent.mkdir(parents=True, exist_ok=True)
            (STAGE / e).replace(dst)
            moved += 1
    # Imports are re-pointed in the binary header (pkgheader.py): json round
    # trips through UAssetGUI corrupt some exports (Materials), and names added
    # at the front of a name map shift indices used by raw texture data.
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import pkgheader
    # numbered names ("X_1") are stored as their base "X" plus a number
    needles = {re.sub(r"_\d+$", "", p).lower().encode() for p in reloc}
    candidates = [p for p in STAGE.rglob("*") if p.suffix in (".uasset", ".umap")
                  and ("RevivalV2" in p.parts or p.relative_to(STAGE).as_posix() in V2_FILES)]
    rewritten = 0
    for path in candidates:
        if any(n in path.read_bytes().lower() for n in needles):
            rewritten += 1 if pkgheader.repoint_imports(path, new_path) else 0
    print(f"relocated v2 art: {moved} files moved, {rewritten} packages rewritten")


def upgrade_v2_props():
    """v2 levels: add the components the current BasePropBP expects (see upgrade_props.py)."""
    def template(name, level):
        path = REVIVAL / f"cmp2/{name}.json"
        if not path.exists():
            base = f"Propnight/Content/Maps/GeneralLevels/Reborn_Mansion/{level}"
            path.parent.mkdir(parents=True, exist_ok=True)
            for ext in ("umap", "uexp"):
                get("v4", f"{base}.{ext}", path.with_suffix("." + ext))
            subprocess.run([UAG, "tojson", str(path.with_suffix(".umap")), str(path), "VER_UE4_26"], check=True)
        return str(path)

    prop_tpl = template("v4_mansion_prop", "Reborn_Mansion_PropData")
    lobby_tpl = template("v4_mansion_sound", "Reborn_Mansion_Sound")  # holds the v4 NewLobbyV2
    levels = [STAGE / e for e in V2_FILES if e.endswith(".umap")
              and any(c in (STAGE / e).read_bytes() for c in (b"BasePropBP_C", b"NewLobbyV2_C"))]
    for level in levels:
        j = level.with_suffix(".json")
        subprocess.run([UAG, "tojson", str(level), str(j), "VER_UE4_26"], check=True, capture_output=True)
        out = subprocess.run(["python", str(Path(__file__).parent / "upgrade_props.py"), prop_tpl, str(j), str(j), lobby_tpl],
                             check=True, capture_output=True, text=True).stdout.strip()
        fromjson(j, level)
        j.unlink()
        print(" ", level.name, out)


def convert(src_name, dst_name, replace):
    for ext in ("uasset", "uexp", "ubulk"):
        get("v4", f"Propnight/Content/UI/Atlas/HorrorUI/MainMenu/{src_name}.{ext}", WORK / f"{src_name}.{ext}")
    j = WORK / f"{src_name}.json"
    subprocess.run([UAG, "tojson", str(WORK / f"{src_name}.uasset"), str(j), "VER_UE4_26"], check=True)
    text = j.read_text(encoding="utf-8")
    for a, b in replace:
        text = text.replace(a, b)
    out_json = WORK / f"{dst_name}.json"
    out_json.write_text(text, encoding="utf-8")
    UI_OUT.mkdir(parents=True, exist_ok=True)
    fromjson(out_json, UI_OUT / f"{dst_name}.uasset")


def game_table():
    """The reference game's own map list (keeps the maps of its build, e.g. Golden Mine), as UAssetGUI JSON."""
    WORK.mkdir(parents=True, exist_ok=True)
    for ext in ("uasset", "uexp"):
        (WORK / f"DT_LevelsReverse.{ext}").write_bytes(subprocess.run(
            [REPAK, "-a", KEY, "get", CURRENT_PAK, f"Propnight/Content/Blueprints/Server/DT_LevelsReverse.{ext}"],
            capture_output=True, check=True).stdout)
    subprocess.run([UAG, "tojson", str(WORK / "DT_LevelsReverse.uasset"), str(WORK / "DT_LevelsReverse.json"), "VER_UE4_26"], check=True)
    return json.loads((WORK / "DT_LevelsReverse.json").read_text(encoding="utf-8"))


# English names of rows whose name comes from a string table (no source text in the row)
STRING_TABLE_NAMES = {"DarkSwampLevelName": "Dark Swamp"}


def sort_rows(table):
    """The selector lists the rows in table order: the shown ones (GameMode 2) go first, A to Z by English name."""
    def gamemode(row):
        return next((p["Value"] for p in row["Value"] if p["Name"].startswith("GameMode_")), None)

    def name(row):
        for p in row["Value"]:
            if p["Name"].startswith("LocalizableMapName_"):
                return p.get("CultureInvariantString") or STRING_TABLE_NAMES.get(p.get("Value")) or str(p.get("Value"))
        return row["Name"]
    rows = table["Table"]["Data"]
    shown = sorted((r for r in rows if gamemode(r) == 2), key=lambda r: name(r).lower())
    table["Table"]["Data"] = shown + [r for r in rows if gamemode(r) != 2]
    print("selector order:", ", ".join(name(r) for r in shown))


def write_table(d, stage, label):
    out_json = REVIVAL / f"modpak/DT_LevelsReverse.{label}.json"
    out_json.write_text(json.dumps(d), encoding="utf-8")
    dst = stage / "Propnight/Content/Blueprints/Server/DT_LevelsReverse.uasset"
    dst.parent.mkdir(parents=True, exist_ok=True)
    fromjson(out_json, dst)


def base_table():
    """For players without the classic maps: the game's list, only sorted."""
    d = game_table()
    sort_rows(next(e for e in d["Exports"] if e.get("Table")))
    write_table(d, BASE_STAGE, "base")


def icons_and_table():
    WORK.mkdir(parents=True, exist_ok=True)
    atlas = [(f'"{OLD_DIR}MainMenu"', f'"{NEW_DIR}RM_MainMenu"'), ('"MainMenu"', '"RM_MainMenu"')]
    convert("MainMenu", "RM_MainMenu", atlas)
    for n in sorted(set(ROWS.values())):
        convert(f"MainMenu_Sprite_{n}", f"RM_Sprite_{n}",
                [(f'"{OLD_DIR}MainMenu_Sprite', f'"{NEW_DIR}RM_Sprite'), ('"MainMenu_Sprite', '"RM_Sprite')] + atlas)

    d = game_table()
    imports = d["Imports"]
    for name in (NEW_DIR + "RM_Sprite", "RM_Sprite"):
        if name not in d["NameMap"]:
            d["NameMap"].append(name)
    sprite = {}
    for n in sorted(set(ROWS.values())):
        imports.append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": f"{NEW_DIR}RM_Sprite_{n}", "OuterIndex": 0,
                        "ClassPackage": "/Script/CoreUObject", "ClassName": "Package", "PackageName": None, "bImportOptional": False})
        imports.append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": f"RM_Sprite_{n}", "OuterIndex": -len(imports),
                        "ClassPackage": "/Script/Paper2D", "ClassName": "PaperSprite", "PackageName": None, "bImportOptional": False})
        sprite[n] = -len(imports)
    table = next(e for e in d["Exports"] if e.get("Table"))
    for row in table["Table"]["Data"]:
        if row["Name"] in RENAMES or row["Name"] in YEAR_RENAMES:
            key, source = (RENAMES.get(row["Name"]) or YEAR_RENAMES[row["Name"]])[:2]
            for p in row["Value"]:
                if p["Name"].startswith("LocalizableMapName_"):
                    p["Namespace"], p["Value"], p["CultureInvariantString"] = "", key, source
    shown = set()
    for row in table["Table"]["Data"]:
        if row["Name"] not in ROWS:
            continue
        for p in row["Value"]:
            if p["Name"].startswith("GameMode_"):
                p["Value"] = 2
            elif p["Name"].startswith("CreateScreen_"):
                p["Value"] = sprite[ROWS[row["Name"]]]
        shown.add(row["Name"])
    deps = table["CreateBeforeSerializationDependencies"]
    deps.extend(v for v in sprite.values() if v not in deps)
    sort_rows(table)
    write_table(d, MENU_STAGE, "classic")
    print("selector rows:", sorted(shown), "missing:", sorted(set(ROWS) - shown))


# Selector icons painted over sprites of the copied atlas: the v2 day farm had no icon of its own and
# borrowed sprite 18 (the night farm); it gets the image the launcher and the site show for it.
ICON_IMAGES = {18: REVIVAL / "release/dlc/farm-day.jpg"}
ATLAS_SIZE = 4096


def paint_icons():
    import struct
    from PIL import Image
    path = UI_OUT / "RM_MainMenu.uexp"
    data = bytearray(path.read_bytes())
    size = ATLAS_SIZE * ATLAS_SIZE * 4
    # inline FByteBulkData of the BGRA mip: flags, element count, size on disk (int32), offset (int64), pixels
    head = data.find(struct.pack("<ii", size, size))
    assert head != -1, "atlas pixels not found"
    start = head + 16
    assert len(data) >= start + size
    for n, image in ICON_IMAGES.items():
        sprite = json.loads((WORK / f"MainMenu_Sprite_{n}.json").read_text(encoding="utf-8"))
        uv = dim = None
        stack = [sprite]
        while stack and not (uv and dim):
            o = stack.pop()
            if isinstance(o, dict):
                if o.get("Name") == "BakedSourceUV" and isinstance(o.get("Value"), dict): uv = o["Value"]
                if o.get("Name") == "BakedSourceDimension" and isinstance(o.get("Value"), dict): dim = o["Value"]
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
        x, y, w, h = int(uv["X"]), int(uv["Y"]), int(dim["X"]), int(dim["Y"])
        pixels = Image.open(image).convert("RGBA").resize((w, h), Image.LANCZOS).tobytes("raw", "BGRA")
        for row in range(h):
            at = start + ((y + row) * ATLAS_SIZE + x) * 4
            data[at:at + w * 4] = pixels[row * w * 4:(row + 1) * w * 4]
        print(f"icon {n}: {image.name} -> atlas {x},{y} {w}x{h}")
    path.write_bytes(bytes(data))


V2_FILES = {l.strip() for l in open(REVIVAL / "v2/needed.txt", encoding="utf-8") if l.strip()}


def pack(stage):
    pak = stage.with_suffix(".pak")
    if pak.exists():
        pak.unlink()
    subprocess.run([REPAK, "pack", "--version", "V11", "--compression", "Zlib", "--mount-point", "../../../", "-q", str(stage)], check=True)
    print("pak:", pak, round(pak.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    import sys
    # maps: the big frozen pak (installed once) / menu: the small versioned pak
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("maps", "all"):
        copy_packages()
        relocate_v2()
        upgrade_v2_props()
        pack(STAGE)
    if target in ("menu", "all"):
        # RevivalMenuBase.pak -> Propnight-WindowsNoEditor_RevivalMenu_P.pak (every player, +100)
        # RevivalMenu.pak     -> Propnight-WindowsNoEditor_RevivalMenuClassic_1_P.pak (classic maps DLC, +200: wins)
        for stage in (MENU_STAGE, BASE_STAGE):
            if stage.exists():
                shutil.rmtree(stage)
        base_table()
        pack(BASE_STAGE)
        icons_and_table()
        paint_icons()
        localization()
        pack(MENU_STAGE)
