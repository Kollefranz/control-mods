"""List / extract files from Control (Northlight) .bin/.rmdp packs.

Format per profMagija/control-unpack file_formats.md; this is an independent
reimplementation. Reads only the small .bin index unless extracting.

  python -I tools/rmdp.py list    <pack-base-path> [--grep REGEX]
  python -I tools/rmdp.py extract <pack-base-path> <outdir> --grep REGEX
"""

import argparse
import os
import re
import shutil
import struct
import sys

HEADER_SIZE = 0x9D
DIR_FMT = "<qqiqiqq"
FILE_FMT = "<qqiqqq"
FILE_PAD = 16
NAMES_PAD = 44


def read_index(bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()
    if data[0] != 0:
        raise ValueError("unexpected endianness marker (big-endian pack?)")
    _version, num_dirs, num_files = struct.unpack_from("<iii", data, 1)

    pos = HEADER_SIZE
    dirs = []
    dsz = struct.calcsize(DIR_FMT)
    for _ in range(num_dirs):
        _, parent, _, name_off, *_ = struct.unpack_from(DIR_FMT, data, pos)
        dirs.append((parent, name_off))
        pos += dsz

    files = []
    fsz = struct.calcsize(FILE_FMT)
    for _ in range(num_files):
        _, dir_idx, _, name_off, c_off, c_len = struct.unpack_from(FILE_FMT, data, pos)
        files.append((dir_idx, name_off, c_off, c_len))
        pos += fsz + FILE_PAD
    pos += NAMES_PAD

    def text(off):
        end = data.index(b"\0", pos + off)
        return data[pos + off : end].decode("utf8")

    full = []
    for parent, name_off in dirs:
        if name_off == -1:
            full.append("")
        else:
            base = full[parent]
            full.append(f"{base}/{text(name_off)}" if base else text(name_off))

    out = []
    for dir_idx, name_off, c_off, c_len in files:
        base = full[dir_idx]
        name = text(name_off)
        out.append((f"{base}/{name}" if base else name, c_off, c_len))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "extract"])
    ap.add_argument("pack")
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("--grep", default="")
    a = ap.parse_args()

    rx = re.compile(a.grep, re.I) if a.grep else None
    entries = [e for e in read_index(a.pack + ".bin") if not rx or rx.search(e[0])]

    if a.cmd == "list":
        for path, off, ln in entries:
            print(f"{ln}\t{off}\t{path}")
        return

    if not a.outdir:
        sys.exit("extract needs <outdir>")
    with open(a.pack + ".rmdp", "rb") as src:
        for path, off, ln in entries:
            dest = os.path.join(a.outdir, *path.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            src.seek(off)
            with open(dest, "wb") as out:
                remaining = ln
                while remaining:
                    chunk = src.read(min(remaining, 1 << 20))
                    if not chunk:
                        raise IOError(f"short read for {path}")
                    out.write(chunk)
                    remaining -= len(chunk)
    print(f"extracted {len(entries)} files")


if __name__ == "__main__":
    main()
