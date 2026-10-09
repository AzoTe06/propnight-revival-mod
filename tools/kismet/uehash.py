"""Hashes used by UE4.26 localization resources (.locres version 3).

text_key_hash(s): TextKeyUtil::HashString = GetTypeHash(CityHash64(UTF-16LE bytes))
source_hash(s):   FTextLocalizationResource::HashString = FCrc::StrCrc32 (CRC32 over 4 bytes per char)
"""
import struct, zlib

M = (1 << 64) - 1
K0, K1, K2 = 0xC3A5C85C97CB3127, 0xB492B66FBE98F273, 0x9AE16A3B2F90404F
KMUL = 0x9DDFEA08EB382D69


def f64(s, i):
    return struct.unpack_from("<Q", s, i)[0]


def f32(s, i):
    return struct.unpack_from("<I", s, i)[0]


def rot(v, n):
    return v if n == 0 else ((v >> n) | (v << (64 - n))) & M


def smix(v):
    return v ^ (v >> 47)


def bswap(v):
    return int.from_bytes(v.to_bytes(8, "little"), "big")


def h16(u, v, mul=KMUL):
    a = ((u ^ v) * mul) & M
    a ^= a >> 47
    b = ((v ^ a) * mul) & M
    b ^= b >> 47
    return (b * mul) & M


def h0to16(s, n):
    if n >= 8:
        mul = (K2 + n * 2) & M
        a = (f64(s, 0) + K2) & M
        b = f64(s, n - 8)
        c = (rot(b, 37) * mul + a) & M
        d = ((rot(a, 25) + b) * mul) & M
        return h16(c, d, mul)
    if n >= 4:
        mul = (K2 + n * 2) & M
        a = f32(s, 0)
        return h16((n + (a << 3)) & M, f32(s, n - 4), mul)
    if n > 0:
        a, b, c = s[0], s[n >> 1], s[n - 1]
        y = (a + (b << 8)) & 0xFFFFFFFF
        z = (n + (c << 2)) & 0xFFFFFFFF
        return (smix(((y * K2) ^ (z * K0)) & M) * K2) & M
    return K2


def h17to32(s, n):
    mul = (K2 + n * 2) & M
    a = (f64(s, 0) * K1) & M
    b = f64(s, 8)
    c = (f64(s, n - 8) * mul) & M
    d = (f64(s, n - 16) * K2) & M
    return h16((rot((a + b) & M, 43) + rot(c, 30) + d) & M, (a + rot((b + K2) & M, 18) + c) & M, mul)


def h33to64(s, n):
    mul = (K2 + n * 2) & M
    a = (f64(s, 0) * K2) & M
    b = f64(s, 8)
    c = f64(s, n - 24)
    d = f64(s, n - 32)
    e = (f64(s, 16) * K2) & M
    f = (f64(s, 24) * 9) & M
    g = f64(s, n - 8)
    h = (f64(s, n - 16) * mul) & M
    u = (rot((a + g) & M, 43) + (rot(b, 30) + c) * 9) & M
    v = (((a + g) ^ d) + f + 1) & M
    w = (bswap(((u + v) * mul) & M) + h) & M
    x = (rot((e + f) & M, 42) + c) & M
    y = ((bswap(((v + w) * mul) & M) + g) * mul) & M
    z = (e + f + c) & M
    a = (bswap(((x + z) * mul + y) & M) + b) & M
    b = (smix(((z + a) * mul + d + h) & M) * mul) & M
    return (b + x) & M


def weak32(w, x, y, z, a, b):
    a = (a + w) & M
    b = rot((b + a + z) & M, 21)
    c = a
    a = (a + x + y) & M
    b = (b + rot(a, 44)) & M
    return (a + z) & M, (b + c) & M


def weak32s(s, i, a, b):
    return weak32(f64(s, i), f64(s, i + 8), f64(s, i + 16), f64(s, i + 24), a, b)


def city64(s):
    n = len(s)
    if n <= 32:
        return h0to16(s, n) if n <= 16 else h17to32(s, n)
    if n <= 64:
        return h33to64(s, n)
    x = f64(s, n - 40)
    y = (f64(s, n - 16) + f64(s, n - 56)) & M
    z = h16((f64(s, n - 48) + n) & M, f64(s, n - 24))
    v = weak32s(s, n - 64, n, z)
    w = weak32s(s, n - 32, (y + K1) & M, x)
    x = (x * K1 + f64(s, 0)) & M
    rem = (n - 1) & ~63
    i = 0
    while True:
        x = (rot((x + y + v[0] + f64(s, i + 8)) & M, 37) * K1) & M
        y = (rot((y + v[1] + f64(s, i + 48)) & M, 42) * K1) & M
        x ^= w[1]
        y = (y + v[0] + f64(s, i + 40)) & M
        z = (rot((z + w[0]) & M, 33) * K1) & M
        v = weak32s(s, i, (v[1] * K1) & M, (x + w[0]) & M)
        w = weak32s(s, i + 32, (z + w[1]) & M, (y + f64(s, i + 16)) & M)
        z, x = x, z
        i += 64
        rem -= 64
        if rem == 0:
            break
    return h16((h16(v[0], w[0]) + smix(y) * K1 + z) & M, (h16(v[1], w[1]) + x) & M)


def text_key_hash(s):
    h = city64(s.encode("utf-16-le"))
    return ((h & 0xFFFFFFFF) + ((h >> 32) * 23)) & 0xFFFFFFFF


def source_hash(s):
    return zlib.crc32(s.encode("utf-32-le")) & 0xFFFFFFFF
