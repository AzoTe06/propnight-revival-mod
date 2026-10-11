"""Build the small pak that points the game at the revival servers.

The former backend host (AWS API Gateway) is stored as plain strings in two
Blueprints (GI_Prophunt, BP_PC_MenuPlayfabCustomGames). It is replaced by a
host name of exactly the same length under our domain, so the packages keep
their layout (no re-serialization, no offset changes).

PlayFab is redirected by the PropnightLocalMap mod (setPlayFabSettings), because
"https://23b52.playfabapi.com/" is a bytecode constant shorter than any host
under the domain.

usage: python build_online_pak.py [--domain propnightrevival.online]
output: revival/online/Propnight-WindowsNoEditor_RevivalOnline_P.pak
"""
import sys
import argparse, subprocess, shutil
from pathlib import Path

REVIVAL = Path(__file__).resolve().parents[2]
ROOT = REVIVAL.parent
REPAK = str(REVIVAL / "tools/repak-v0.2.3/repak.exe")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paks_key import KEY  # noqa: E402  (game pak AES key, not in the source)
from game_root import GAME_PAK  # noqa: E402  (reference install)
OLD_HOST = "ddkkakl4x2.execute-api.eu-central-1.amazonaws.com"
ASSETS = [
    "Propnight/Content/Blueprints/GI_Prophunt",
    "Propnight/Content/Maps/MainMenu/BP_PC_MenuPlayfabCustomGames",
]


def backend_host(domain):
    """Same-length replacement: '<label>.<domain>' padded to len(OLD_HOST)."""
    label_len = len(OLD_HOST) - len(domain) - 1
    base = "backend-eu-central-1-prod"
    if label_len < 1:
        raise SystemExit(f"domain too long for a same-length host ({len(domain)} chars)")
    label = (base * 2)[:label_len].rstrip("-")
    label = label + "0" * (label_len - len(label))
    host = f"{label}.{domain}"
    assert len(host) == len(OLD_HOST), host
    return host


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="propnightrevival.online")
    args = ap.parse_args()
    new_host = backend_host(args.domain)
    stage = REVIVAL / "online/stage"
    if stage.exists():
        shutil.rmtree(stage)
    for asset in ASSETS:
        for ext in ("uasset", "uexp"):
            entry = f"{asset}.{ext}"
            data = subprocess.run([REPAK, "-a", KEY, "get", str(GAME_PAK), entry], check=True, capture_output=True).stdout
            count = data.count(OLD_HOST.encode())
            data = data.replace(OLD_HOST.encode(), new_host.encode())
            # UTF-16 copies, if any
            data = data.replace(OLD_HOST.encode("utf-16-le"), new_host.encode("utf-16-le"))
            out = stage / entry
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            if count:
                print(f"{entry}: {count} URL(s) -> {new_host}")
    pak = REVIVAL / "online/Propnight-WindowsNoEditor_RevivalOnline_P.pak"
    subprocess.run([REPAK, "pack", "--version", "V11", str(stage), str(pak)], check=True, capture_output=True)
    print(f"pak: {pak} ({pak.stat().st_size} bytes)")
    print(f"backend host to put in DNS/Caddy: {new_host}")


if __name__ == "__main__":
    main()
