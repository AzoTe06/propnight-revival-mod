"""Dependency closure of packages from an older pak against the current game.

usage: python deps.py --src v4|v2 [--have LIST ...] --out NEEDED.txt ROOT_PACKAGE [...]
  e.g. python deps.py --src v4 --out v4/needed.txt /Game/Maps/GeneralLevels/Reborn_Mansion/Reborn_Mansion_MAIN
Reads package headers from the source pak (cached under revival/<src>/cache),
follows every /Game/ package they import, and lists the source files of every
package that is neither in the current pak nor in the --have lists (files
already shipped by the mod pak from another source).
Run from Git Bash with MSYS_NO_PATHCONV=1 so /Game/ paths are not rewritten.
"""
import sys
import argparse, os, re, subprocess
from pathlib import Path

REVIVAL = Path(__file__).resolve().parents[2]
REPAK = REVIVAL / "tools/repak-v0.2.3/repak.exe"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paks_key import KEY  # noqa: E402  (game pak AES key, not in the source)
SOURCES = {
    "v4": r"<games>/Propnight.v4.0.0.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
    "v2": r"<games>/Propnight.v2.0.1.Steam/Propnight.v2.0.1.Steam/common/Propnight/Propnight/Content/Paks/Propnight-WindowsNoEditor.pak",
}

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True, choices=SOURCES)
ap.add_argument("--have", action="append", default=[])
ap.add_argument("--out", required=True)
ap.add_argument("--reused-out", help="also list the packages taken from the current game")
ap.add_argument("--roots-file", help="more root packages, one per line (always copied from the source)")
ap.add_argument("roots", nargs="+")
args = ap.parse_args()
if args.roots_file:
    args.roots += [l.strip() for l in open(args.roots_file, encoding="utf-8") if l.strip()]
SRC_PAK = SOURCES[args.src]
CACHE = REVIVAL / args.src / "cache"


def load_list(path):
    by_pkg = {}
    for e in (l.strip() for l in open(path, encoding="utf-8", errors="ignore")):
        if e:
            by_pkg.setdefault(os.path.splitext(e)[0].lower(), []).append(e)
    return by_pkg


src = load_list(REVIVAL / args.src / "pak-file-list.txt")
cur = load_list(REVIVAL / "pak-file-list.txt")
for extra in args.have:
    for k, v in load_list(extra).items():
        cur.setdefault(k, v)


def entry_stem(pkg):
    return ("Propnight/Content/" + pkg[len("/Game/"):]).lower()


def header(entry):
    out = CACHE / entry
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(subprocess.run([str(REPAK), "-a", KEY, "get", SRC_PAK, entry], capture_output=True).stdout)
    return out.read_bytes()


PKG = re.compile(rb"/Game/[A-Za-z0-9_\-/ .]+")


def imports_of(stem):
    names = set()
    for e in src.get(stem, []):
        if e.endswith((".uasset", ".umap")):
            for m in PKG.findall(header(e)):
                names.add(m.decode().split(".")[0].rstrip("/"))
    return names


todo = list(args.roots)
seen, missing, present, absent = set(), [], set(), set()
while todo:
    pkg = todo.pop()
    stem = entry_stem(pkg)
    if stem in seen:
        continue
    seen.add(stem)
    if stem not in src and stem not in cur:
        # FNames keep a numeric suffix apart ("Chest_1" is "Chest" + number 2),
        # so the name map may hold only the base: try the numbered variants.
        variants = {k for k in list(src) + list(cur) if re.fullmatch(re.escape(stem) + r"_\d+", k)}
        if not variants:
            absent.add(pkg)
        todo.extend("/Game/" + k[len("propnight/content/"):] for k in variants)
        continue
    if stem not in src:
        continue
    if stem in cur and pkg not in args.roots:
        present.add(pkg)
        continue
    missing.append(pkg)
    todo.extend(d for d in imports_of(stem) if entry_stem(d) not in seen)

needed = sorted(e for pkg in missing for e in src[entry_stem(pkg)])
if args.reused_out:
    Path(args.reused_out).write_text("\n".join(sorted(present)) + "\n", encoding="utf-8")
Path(args.out).write_text("\n".join(needed) + "\n", encoding="utf-8")
print(f"[{args.src}] packages to copy: {len(missing)} ({len(needed)} files); reused: {len(present)}; unresolved: {len(absent)}")
for p in sorted(absent)[:20]:
    print("   ?", p)
