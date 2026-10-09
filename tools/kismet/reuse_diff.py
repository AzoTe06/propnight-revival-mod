"""Which packages an old map takes from the current game have changed since.

For every package of <src>/reused.txt (written by deps.py --reused-out), the
source build's .uexp/.ubulk are compared with the current game's. Changed art
(StaticMesh, Material, MaterialInstanceConstant, Texture2D) is what made the
restored maps show wrong textures/meshes: it goes to <src>/relocate.txt and is
shipped in its old version under /Game/Revival<SRC>/ by build_modpak.py.

usage: python reuse_diff.py --src v4|v2
writes <src>/reused_diff.txt (package, class, changed 0/1) and <src>/relocate.txt
"""
import argparse, struct, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pkgheader

REVIVAL = Path(__file__).resolve().parents[2]
REPAK = str(REVIVAL / "tools/repak-v0.2.3/repak.exe")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paks_key import KEY  # noqa: E402  (game pak AES key, not in the source)
CURRENT_PAK = str(REVIVAL.parent / "Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak")
SOURCES = {
    "v4": r"<games>/Propnight.v4.0.0.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
    "v2": r"<games>/Propnight.v2.0.1.Steam/Propnight.v2.0.1.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
}
ART = {"StaticMesh", "Material", "MaterialInstanceConstant", "Texture2D"}


def get(pak, entry):
    return subprocess.run([REPAK, "-a", KEY, "get", pak, entry], capture_output=True).stdout


def main_class(header, package):
    """Class name of the package's main export (the one named like the package)."""
    f, _ = pkgheader.parse(header)
    g = lambda pos: struct.unpack_from("<i", header, pos)[0]
    r = pkgheader.Reader(header, g(f["NameOffset"]))
    names = []
    for _ in range(g(f["NameCount"])):
        names.append(r.fstring())
        r.p += 4
    imp_off, exp_off = g(f["ImportOffset"]), g(f["ExportOffset"])
    base = package.rsplit("/", 1)[1].lower()
    for k in range(g(f["ExportCount"])):
        e = exp_off + k * 104
        cls, outer, name = g(e), g(e + 12), g(e + 16)
        if outer == 0 and names[name].lower() == base and cls < 0:
            return names[g(imp_off + (-cls - 1) * 28 + 20)]
    return "?"


def compare(src_pak, package):
    stem = "Propnight/Content/" + package[len("/Game/"):]
    header = get(src_pak, stem + ".uasset") or get(src_pak, stem + ".umap")
    try:
        cls = main_class(header, package) if header else "?"
    except Exception:
        cls = "?"
    changed = any(get(src_pak, stem + ext) != get(CURRENT_PAK, stem + ext) for ext in (".uexp", ".ubulk"))
    return package, cls, int(changed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, choices=["v4", "v2"])
    args = ap.parse_args()
    packages = [l.strip() for l in open(REVIVAL / args.src / "reused.txt", encoding="utf-8") if l.strip()]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda p: compare(SOURCES[args.src], p), packages))
    (REVIVAL / args.src / "reused_diff.txt").write_text(
        "".join(f"{p}\t{c}\t{d}\n" for p, c, d in rows), encoding="utf-8")
    relocate = [p for p, c, d in rows if d and c in ART]
    (REVIVAL / args.src / "relocate.txt").write_text("".join(p + "\n" for p in relocate), encoding="utf-8")
    from collections import Counter
    print(Counter((c, d) for _, c, d in rows).most_common())
    print(f"relocate: {len(relocate)} packages")


if __name__ == "__main__":
    main()
