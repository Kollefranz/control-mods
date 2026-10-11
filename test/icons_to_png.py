"""Convert the game's small mod icons (.tex = DDS RGBA8) to PNG for the browser harness.

  python -I test/icons_to_png.py <harness dir>

Writes uiresources/p7/images/{1080,4k}/images/items/small/<NAME>_SMALL.png (4k is a copy of the
1080 art, enough for layout testing).
"""

import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

from rmdp import read_index  # noqa: E402

PACKS = r"E:\SteamLibrary\steamapps\common\Control\data_packfiles"
PREFIX = "data_pc/uiresources/p7/images/1080/images/items/small/"


def decode(data):
    h, w = struct.unpack_from("<II", data, 12)
    fmt, off = None, 128
    if data[84:88] == b"DX10":
        (fmt,) = struct.unpack_from("<I", data, 128)
        off = 148
    px = bytearray(data[off : off + w * h * 4])
    if fmt == 87:  # BGRA -> RGBA
        px[0::4], px[2::4] = px[2::4], px[0::4]
    return w, h, bytes(px)


def png(w, h, rgba):
    raw = b"".join(b"\x00" + rgba[y * w * 4 : (y + 1) * w * 4] for y in range(h))

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def main():
    out = sys.argv[1]
    n = 0
    for pack in ("ep100-000-pc", "ep101-000-pc"):
        base = os.path.join(PACKS, pack)
        entries = [e for e in read_index(base + ".bin") if e[0].startswith(PREFIX) and e[0].endswith(".tex")]
        with open(base + ".rmdp", "rb") as f:
            for path, off, ln in entries:
                f.seek(off)
                w, h, px = decode(f.read(ln))
                name = os.path.basename(path)[:-4] + ".png"
                blob = png(w, h, px)
                for size in ("1080", "4k"):
                    d = os.path.join(out, "uiresources", "p7", "images", size, "images", "items", "small")
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, name), "wb") as o:
                        o.write(blob)
                n += 1
    print("wrote", n, "icons")


if __name__ == "__main__":
    main()
