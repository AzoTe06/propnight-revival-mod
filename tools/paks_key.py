"""AES key of the game's paks, kept out of the source.

Set PROPNIGHT_AES_KEY (0x… hex) or put it in revival/tools/.aes-key (never
published). Tools that read or build paks import `KEY` from here.
"""
import os
from pathlib import Path

_FILE = Path(__file__).resolve().parent / ".aes-key"


def _load():
    key = os.environ.get("PROPNIGHT_AES_KEY", "").strip()
    if not key and _FILE.exists():
        key = _FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("The game's pak AES key is needed: set PROPNIGHT_AES_KEY or create revival/tools/.aes-key")
    return key


KEY = _load()
