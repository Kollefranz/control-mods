"""Inspect / repack Control .ui bundles (Coherent GT assets in a Northlight container).

Layout (reverse engineered):
  u32 MAGIC, u32 2, u32 total_file_len, 'aZcp', ...
  per resource: ... MAGIC <u64 offset> <u64 length> MAGIC ...   (length 0 => asset lives elsewhere)
  MAGIC <u32 blob_len> <blob: all embedded files concatenated> MAGIC   <- EOF

  python -I tools/uitool.py list    <file.ui>
  python -I tools/uitool.py extract <file.ui> <outdir>
  python -I tools/uitool.py repack  <file.ui> <replacements_dir> <out.ui>
"""

import os
import re
import struct
import sys

MAGIC = b"\x3f\xb3\x4d\xd3"
ENTRY_RX = re.compile(re.escape(MAGIC) + rb"(.{8})(.{8})" + re.escape(MAGIC), re.S)


class UiBundle:
    def __init__(self, data):
        self.data = data
        if data[:4] != MAGIC:
            raise ValueError("not a .ui bundle")
        (self.total_len,) = struct.unpack_from("<I", data, 8)
        if self.total_len != len(data):
            raise ValueError("header length mismatch")
        if data[-4:] != MAGIC:
            raise ValueError("missing trailing marker")

        # blob marker: MAGIC <u32 len> blob MAGIC(EOF)
        self.blob_len_pos = None
        for m in re.finditer(re.escape(MAGIC), data):
            p = m.start()
            if p + 8 > len(data):
                continue
            (n,) = struct.unpack_from("<I", data, p + 4)
            if p + 8 + n + 4 == len(data):
                self.blob_len_pos = p + 4
                break
        if self.blob_len_pos is None:
            raise ValueError("blob marker not found")
        self.blob_start = self.blob_len_pos + 4
        (self.blob_len,) = struct.unpack_from("<I", data, self.blob_len_pos)

        self.entries = []  # (name, field_pos, offset, length)
        for m in ENTRY_RX.finditer(data, 0, self.blob_len_pos):
            off, ln = struct.unpack("<QQ", m.group(1) + m.group(2))
            if ln == 0 or off + ln > self.blob_len:
                continue
            fpos = m.start() + 4
            self.entries.append((self._name_before(m.start()), fpos, off, ln))
        self.entries.sort(key=lambda e: e[2])

    def _name_before(self, pos):
        idx = self.data.rfind(b"uiresources/", 0, pos)
        (n,) = struct.unpack_from("<I", self.data, idx - 4)
        return self.data[idx : idx + n].decode("ascii")

    def blob_of(self, e):
        s = self.blob_start + e[2]
        return self.data[s : s + e[3]]

    def repack(self, replacements):
        """replacements: {name: bytes}. Returns new file bytes."""
        buf = bytearray(self.data[: self.blob_start])
        blob = bytearray()
        for name, fpos, off, ln in self.entries:
            payload = replacements.get(name)
            if payload is None:
                payload = self.data[self.blob_start + off : self.blob_start + off + ln]
            struct.pack_into("<QQ", buf, fpos, len(blob), len(payload))
            blob += payload
        if len(blob) != self.blob_len and not replacements:
            raise ValueError("unmodified repack changed blob length")
        struct.pack_into("<I", buf, self.blob_len_pos, len(blob))
        out = bytes(buf) + bytes(blob) + MAGIC
        struct.pack_into("<I", (o := bytearray(out)), 8, len(out))
        return bytes(o)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    ui = UiBundle(open(path, "rb").read())

    if cmd == "list":
        for name, _fpos, off, ln in ui.entries:
            print(f"{ln}\t{off}\t{name}")
    elif cmd == "extract":
        for e in ui.entries:
            dest = os.path.join(sys.argv[3], *e[0].split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(ui.blob_of(e))
        print(f"extracted {len(ui.entries)} files")
    elif cmd == "repack":
        rep = {}
        for e in ui.entries:
            cand = os.path.join(sys.argv[3], *e[0].split("/"))
            if os.path.isfile(cand):
                rep[e[0]] = open(cand, "rb").read()
        out = ui.repack(rep)
        open(sys.argv[4], "wb").write(out)
        print(f"replaced {len(rep)} entries -> {sys.argv[4]} ({len(out)} bytes)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
