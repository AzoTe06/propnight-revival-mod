"""Read and rewrite UE4.26 .locres (version 3), adding localized entries.

load(path) -> Locres; Locres.set(namespace, key, source, text); Locres.save(path)
Stored namespace hashes are kept as read; new keys and sources are hashed with
uehash (verified against every key of the game's en/Game.locres).
"""
import struct
from uehash import source_hash, text_key_hash
from locres import MAGIC, R


def wstr(s):
    if s == "":
        return struct.pack("<i", 1) + bytes(1)  # UE writes empty strings with their terminator
    if all(ord(c) < 128 for c in s):
        b = s.encode("latin-1") + b"\0"
        return struct.pack("<i", len(b)) + b
    b = s.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(b) // 2)) + b


class Locres:
    def __init__(self):
        self.namespaces = []  # [ns_hash, ns, [[key_hash, key, src_hash, text], ...]]

    def set(self, ns, key, source, text):
        entry = [text_key_hash(key), key, source_hash(source), text]
        for n in self.namespaces:
            if n[1] == ns:
                for k in n[2]:
                    if k[1] == key:
                        k[:] = entry
                        return
                n[2].append(entry)
                return
        self.namespaces.append([text_key_hash(ns), ns, [entry]])

    def save(self, path):
        strings, index = [], {}
        body = b""
        count = 0
        for ns_hash, ns, keys in self.namespaces:
            body += struct.pack("<I", ns_hash) + wstr(ns) + struct.pack("<I", len(keys))
            for key_hash, key, src_hash, text in keys:
                if text not in index:
                    index[text] = len(strings)
                    strings.append([text, 0])
                strings[index[text]][1] += 1
                body += struct.pack("<I", key_hash) + wstr(key) + struct.pack("<Ii", src_hash, index[text])
                count += 1
        head_len = 16 + 1 + 8 + 4
        body = struct.pack("<I", len(self.namespaces)) + body
        table = struct.pack("<i", len(strings)) + b"".join(wstr(t) + struct.pack("<i", rc) for t, rc in strings)
        data = MAGIC + struct.pack("<B", 3) + struct.pack("<q", head_len + len(body)) + struct.pack("<I", count) + body + table
        open(path, "wb").write(data)


def load(path):
    r = R(open(path, "rb").read())
    assert r.d[:16] == MAGIC
    r.p = 16
    version = r.take("<B")
    assert version == 3, version
    offset = r.take("<q")
    r.take("<I")
    save = r.p
    r.p = offset
    strings = []
    for _ in range(r.take("<i")):
        strings.append(r.fstring())
        r.take("<i")
    r.p = save
    loc = Locres()
    for _ in range(r.take("<I")):
        ns_hash = r.take("<I")
        ns = r.fstring()
        keys = []
        for _ in range(r.take("<I")):
            key_hash = r.take("<I")
            key = r.fstring()
            src_hash = r.take("<I")
            keys.append([key_hash, key, src_hash, strings[r.take("<i")]])
        loc.namespaces.append([ns_hash, ns, keys])
    return loc
