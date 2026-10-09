"""Read UE4 .locres files (versions 0-3).

usage: python locres.py FILE.locres [REGEX]   -> namespace / key / text (filtered by REGEX on key or text)
As a module: read(path) -> (version, [(namespace, key, source_hash, text)])
"""
import re, struct, sys

MAGIC = bytes.fromhex("0E14747567 4A03FC 4A15909D C3377F1B".replace(" ", ""))


class R:
    def __init__(self, data):
        self.d, self.p = data, 0

    def take(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v[0] if len(v) == 1 else v

    def fstring(self):
        n = self.take("<i")
        if n == 0:
            return ""
        if n < 0:
            raw = self.d[self.p:self.p - 2 * n]
            self.p += -2 * n
            return raw[:-2].decode("utf-16-le")
        raw = self.d[self.p:self.p + n]
        self.p += n
        return raw[:-1].decode("latin-1")


def read(path):
    r = R(open(path, "rb").read())
    if r.d[:16] != MAGIC:
        raise ValueError("legacy locres not supported")
    r.p = 16
    version = r.take("<B")
    strings_offset = r.take("<q")
    if version >= 2:
        r.take("<I")  # entries count
    save = r.p
    r.p = strings_offset
    strings = []
    for _ in range(r.take("<i")):
        s = r.fstring()
        if version >= 2:
            r.take("<i")  # ref count
        strings.append(s)
    r.p = save
    out = []
    for _ in range(r.take("<I")):
        if version >= 2:
            r.take("<I")
        ns = r.fstring()
        for _ in range(r.take("<I")):
            if version >= 2:
                r.take("<I")
            key = r.fstring()
            src_hash = r.take("<I")
            idx = r.take("<i")
            out.append((ns, key, src_hash, strings[idx]))
    return version, out


if __name__ == "__main__":
    version, entries = read(sys.argv[1])
    rx = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
    print("version", version, "entries", len(entries))
    for ns, key, h, text in entries:
        if not rx or rx.search(key) or rx.search(text):
            print(repr(ns), key, "->", text)
