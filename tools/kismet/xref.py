"""Find code references to a string in Propnight.exe and disassemble around them.

usage: python xref.py EXE "utf16 string" [before_bytes] [after_bytes]
       python xref.py EXE --rva 0x1234 [before] [after]      (disassemble at an RVA)
"""
import re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

exe = open(sys.argv[1], "rb").read()
pe = struct.unpack_from("<I", exe, 0x3C)[0]
nsec = struct.unpack_from("<H", exe, pe + 6)[0]
opt = struct.unpack_from("<H", exe, pe + 20)[0]
base = struct.unpack_from("<Q", exe, pe + 24 + 24)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + 40 * i
    name = exe[o:o + 8].rstrip(b"\0").decode()
    vs, va, rs, rp = struct.unpack_from("<IIII", exe, o + 8)
    secs.append((name, va, vs, rp, rs))


def off2rva(off):
    for n, va, vs, rp, rs in secs:
        if rp <= off < rp + rs:
            return va + off - rp


def rva2off(rva):
    for n, va, vs, rp, rs in secs:
        if va <= rva < va + rs:
            return rp + rva - va


text = next(s for s in secs if s[0] == ".text")
md = Cs(CS_ARCH_X86, CS_MODE_64)


def dis(rva, before, after):
    start = rva - before
    off = rva2off(start)
    code = exe[off:off + before + after]
    for ins in md.disasm(code, start):
        mark = ">>" if ins.address == rva else "  "
        print(f"{mark} {ins.address:08x}: {ins.mnemonic} {ins.op_str}")


def xrefs(target_rva):
    _, va, vs, rp, rs = text
    data = exe[rp:rp + rs]
    hits = []
    # any rip-relative disp32 at position p whose instruction ends at p+4 (+imm)
    for m in re.finditer(rb"[\x48\x4c][\x8d\x8b]", data):
        p = m.start()
        modrm = data[p + 2]
        if (modrm & 0xC7) != 0x05:
            continue
        disp = struct.unpack_from("<i", data, p + 3)[0]
        insn_end = va + p + 7
        if insn_end + disp == target_rva:
            hits.append(va + p)
    return hits


before = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x60
after = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x80
if sys.argv[2] == "--rva":
    dis(int(sys.argv[3], 0), int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x60, int(sys.argv[5], 0) if len(sys.argv) > 5 else 0x100)
    sys.exit()
needle = sys.argv[2].encode("utf-16-le") + b"\0\0"
for m in re.finditer(re.escape(needle), exe):
    if exe[m.start() - 2:m.start()] != b"\0\0":
        continue
    rva = off2rva(m.start())
    print(f"string at file {m.start():#x} rva {rva:#x}")
    for h in xrefs(rva):
        print(f"--- xref at rva {h:#x}")
        dis(h, before, after)
