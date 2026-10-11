"""Measure the opaque area of Control UI icons (.tex = DDS with DX10 header, RGBA8).

  python -I tools/iconstats.py <dir with .tex files> [alpha_threshold]

Prints per-set statistics of the glyph bounding box as a fraction of the canvas.
"""

import glob
import os
import struct
import sys

DXGI = {28: "RGBA", 87: "BGRA"}


def read_tex(path):
    data = open(path, "rb").read()
    if data[:4] != b"DDS ":
        raise ValueError("not DDS")
    h, w = struct.unpack_from("<II", data, 12)
    fourcc = data[84:88]
    off = 128
    fmt = None
    if fourcc == b"DX10":
        (fmt,) = struct.unpack_from("<I", data, 128)
        off = 148
    return w, h, fmt, data[off : off + w * h * 4]


def bbox(w, h, px, thr):
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = px[y * w * 4 : (y + 1) * w * 4]
        alphas = row[3::4]
        xs = [x for x, a in enumerate(alphas) if a > thr]
        if xs:
            x0, x1 = min(x0, xs[0]), max(x1, xs[-1])
            y0, y1 = min(y0, y), max(y1, y)
    return None if x1 < 0 else (x0, y0, x1 + 1, y1 + 1)


def main():
    root = sys.argv[1]
    thr = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    sets = {}
    for path in sorted(glob.glob(os.path.join(root, "**", "*.tex"), recursive=True)):
        w, h, fmt, px = read_tex(path)
        if fmt not in DXGI:
            print("skip (format", fmt, "):", os.path.basename(path))
            continue
        b = bbox(w, h, px, thr)
        kind = "small" if "/small/" in path.replace("\\", "/") else "big"
        sets.setdefault(kind, []).append((os.path.basename(path), w, h, b))
    for kind, items in sets.items():
        fr = [((b[2] - b[0]) / w, (b[3] - b[1]) / h, b[0] / w, b[1] / h, (w - b[2]) / w, (h - b[3]) / h) for _, w, h, b in items if b]
        n = len(fr)
        print(f"== {kind}: {n} icons, canvas {items[0][1]}x{items[0][2]}")
        print("   glyph width  fraction  min/avg/max: %.2f %.2f %.2f" % (min(f[0] for f in fr), sum(f[0] for f in fr) / n, max(f[0] for f in fr)))
        print("   glyph height fraction  min/avg/max: %.2f %.2f %.2f" % (min(f[1] for f in fr), sum(f[1] for f in fr) / n, max(f[1] for f in fr)))
        print("   margins   left min/max %.2f %.2f   top min/max %.2f %.2f" % (min(f[2] for f in fr), max(f[2] for f in fr), min(f[3] for f in fr), max(f[3] for f in fr)))
        print("   margins  right min/max %.2f %.2f bottom min/max %.2f %.2f" % (min(f[4] for f in fr), max(f[4] for f in fr), min(f[5] for f in fr), max(f[5] for f in fr)))
        u = (
            min(b[0] / w for _, w, h, b in items if b),
            min(b[1] / h for _, w, h, b in items if b),
            max(b[2] / w for _, w, h, b in items if b),
            max(b[3] / h for _, w, h, b in items if b),
        )
        print("   UNION bbox (fractions of canvas): left %.3f top %.3f right %.3f bottom %.3f" % u)
        odd = [(name, b) for name, w, h, b in items if not b]
        if odd:
            print("   fully transparent:", [o[0] for o in odd][:5])


if __name__ == "__main__":
    main()
