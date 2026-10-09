"""Binary editor for UE4.26 cooked package headers (.uasset/.umap with .uexp).

Re-points imports at new package names without re-serializing export data
(UAssetGUI json round trips corrupt some exports, e.g. Materials):
new names are appended to the name map, the matching import entries get the new
name index, and every header offset after the name map is shifted.

repoint_imports(path, mapping) -> number of imports changed
  mapping: lower-case old package path -> new package path
"""
import struct, zlib

# --- FName hashes stored next to each name (FNameEntrySerialized, 4.26)
def _crc_table_deprecated():
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) if crc & 0x80000000 else (crc << 1)
        table.append(crc & 0xFFFFFFFF)
    return table


_T = _crc_table_deprecated()


def strihash_deprecated(s):
    h = 0
    for ch in s:
        b = ord(ch.upper()) & 0xFF
        h = ((h >> 8) & 0x00FFFFFF) ^ _T[(h ^ b) & 0xFF]
    return h


def name_hashes(s):
    return strihash_deprecated(s) & 0xFFFF, zlib.crc32(s.encode("utf-32-le")) & 0xFFFF


class Reader:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def i64(self):
        v = struct.unpack_from("<q", self.d, self.p)[0]
        self.p += 8
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            s = self.d[self.p:self.p - 2 * n][:-2].decode("utf-16-le")
            self.p += -2 * n
        else:
            s = self.d[self.p:self.p + n][:-1].decode("latin-1")
            self.p += n
        return s


def encode_name(s):
    h1, h2 = name_hashes(s)
    if all(ord(c) < 128 for c in s):
        raw = s.encode("latin-1") + b"\0"
        return struct.pack("<i", len(raw)) + raw + struct.pack("<HH", h1, h2)
    raw = s.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(raw) // 2)) + raw + struct.pack("<HH", h1, h2)


def parse(data):
    """Return dict of field positions in the summary plus tables."""
    r = Reader(data)
    f = {}
    assert r.i32() == -1641380927 or True  # tag 0x9E2A83C1
    legacy = r.i32()
    assert legacy == -7, legacy
    r.i32()  # legacy UE3
    r.i32()  # UE4 version (0 when unversioned)
    r.i32()  # licensee
    count = r.i32()
    r.p += count * 20
    f["TotalHeaderSize"] = r.p; r.i32()
    r.fstring()  # folder name
    r.p += 4  # package flags
    f["NameCount"] = r.p; r.i32()
    f["NameOffset"] = r.p; r.i32()
    f["GatherableTextDataCount"] = r.p; r.i32()
    f["GatherableTextDataOffset"] = r.p; r.i32()
    f["ExportCount"] = r.p; r.i32()
    f["ExportOffset"] = r.p; r.i32()
    f["ImportCount"] = r.p; r.i32()
    f["ImportOffset"] = r.p; r.i32()
    f["DependsOffset"] = r.p; r.i32()
    f["SoftPackageReferencesCount"] = r.p; r.i32()
    f["SoftPackageReferencesOffset"] = r.p; r.i32()
    f["SearchableNamesOffset"] = r.p; r.i32()
    f["ThumbnailTableOffset"] = r.p; r.i32()
    r.p += 16  # guid
    gens = r.i32()
    f["Generations"] = r.p
    r.p += gens * 8
    for _ in range(2):  # saved-by and compatible-with engine versions
        r.p += 2 + 2 + 2 + 4
        r.fstring()
    r.p += 4  # compression flags
    assert r.i32() == 0, "compressed chunks"
    r.p += 4  # package source
    for _ in range(r.i32()):
        r.fstring()
    f["AssetRegistryDataOffset"] = r.p; r.i32()
    f["BulkDataStartOffset"] = r.p; r.i64()
    f["WorldTileInfoDataOffset"] = r.p; r.i32()
    chunk_ids = r.i32()
    r.p += chunk_ids * 4
    f["PreloadDependencyCount"] = r.p; r.i32()
    f["PreloadDependencyOffset"] = r.p; r.i32()
    return f, gens


def get32(d, pos):
    return struct.unpack_from("<i", d, pos)[0]


def repoint_imports(path, mapping):
    data = bytearray(open(path, "rb").read())
    f, gens = parse(data)
    name_count = get32(data, f["NameCount"])
    name_off = get32(data, f["NameOffset"])
    r = Reader(data, name_off)
    names = []
    for _ in range(name_count):
        names.append(r.fstring())
        r.p += 4
    names_end = r.p
    imp_off = get32(data, f["ImportOffset"])
    imp_count = get32(data, f["ImportCount"])
    lower_index = {}
    appended = []

    def index_for(s):
        if s.lower() in lower_index:
            return lower_index[s.lower()]
        idx = name_count + len(appended)
        appended.append(s)
        lower_index[s.lower()] = idx
        return idx

    changed = 0
    for k in range(imp_count):
        e = imp_off + k * 28  # ClassPackage(8) ClassName(8) Outer(4) ObjectName(8)
        idx, num = struct.unpack_from("<ii", data, e + 20)
        base = names[idx]
        full = base if num == 0 else f"{base}_{num - 1}"
        new = mapping.get(full.lower())
        if not new:
            continue
        new_base = new[: len(new) - len(full) + len(base)] if num else new
        struct.pack_into("<ii", data, e + 20, index_for(new_base), num)
        changed += 1
    if not changed:
        return 0
    blob = b"".join(encode_name(s) for s in appended)
    delta = len(blob)
    data[names_end:names_end] = blob
    struct.pack_into("<i", data, f["NameCount"], name_count + len(appended))
    for g in range(gens):  # generation name counts follow the name map size
        pos = f["Generations"] + g * 8 + 4
        if get32(data, pos) == name_count:
            struct.pack_into("<i", data, pos, name_count + len(appended))
    for key in ("TotalHeaderSize", "GatherableTextDataOffset", "ExportOffset", "ImportOffset", "DependsOffset",
                "SoftPackageReferencesOffset", "SearchableNamesOffset", "ThumbnailTableOffset",
                "AssetRegistryDataOffset", "WorldTileInfoDataOffset", "PreloadDependencyOffset"):
        v = get32(data, f[key])
        if v > name_off:
            struct.pack_into("<i", data, f[key], v + delta)
    bulk = struct.unpack_from("<q", data, f["BulkDataStartOffset"])[0]
    if bulk > name_off:
        struct.pack_into("<q", data, f["BulkDataStartOffset"], bulk + delta)
    exp_off = get32(data, f["ExportOffset"])
    for k in range(get32(data, f["ExportCount"])):
        pos = exp_off + k * 104 + 36  # SerialOffset after Class/Super/Template/Outer, name, flags, size
        struct.pack_into("<q", data, pos, struct.unpack_from("<q", data, pos)[0] + delta)
    open(path, "wb").write(data)
    return changed


def check_hashes(path):
    """Compare stored name hashes with name_hashes() (sanity check)."""
    data = open(path, "rb").read()
    f, _ = parse(data)
    r = Reader(data, get32(data, f["NameOffset"]))
    ok = bad = 0
    for _ in range(get32(data, f["NameCount"])):
        s = r.fstring()
        stored = struct.unpack_from("<HH", data, r.p)
        r.p += 4
        if stored == name_hashes(s):
            ok += 1
        else:
            bad += 1
    return ok, bad
