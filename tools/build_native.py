"""Build the inventory-limit plugin (native/modinventory.c) and package it for Vortex.

  python -I tools/build_native.py [--show]

Steps: verify every signature against the installed Control_DX12/DX11.exe (each must match
exactly once), simulate the edits and check the patched code with capstone if it is
installed, generate native/patches.h, compile with zig, write dist/Control-ModInventory.zip.

--show prints the disassembly of every patched region (needs capstone).
"""

import os
import struct
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"E:\SteamLibrary\steamapps\common\Control"
EXES = ("Control_DX12.exe", "Control_DX11.exe")
DEFAULT_LIMIT = 500
VERSION = "1.0.0"

LIM = None  # marks the 4-byte limit immediate inside an edit


def h(s):
    return bytes.fromhex(s.replace(" ", ""))


# Inventory object (at [inventory+0x38]): +0x24 = m_iCharacterModsLimit (Personal Mods),
# +0x28 = m_iWeaponModsLimit. Both are read by the "can this item be added" check and
# mirrored for the UI by a getter that falls back to r12d when the object is missing.
# Each edit: (offset in signature, original bytes, new bytes, limit immediate offset or -1)
PATCHES = [
    {
        "name": "can-add personal mods",
        "sig": h("48 8B 4B 38  03 C6  3B 41 24  0F 8F"),  # mov rcx,[rbx+38]; add eax,esi; cmp eax,[rcx+24]; jg fail
        "edits": [(0, h("48 8B 4B 38 03 C6 3B 41 24"), h("90 90  03 C6  3D 00 00 00 00"), 5)],  # cmp eax,LIMIT
    },
    {
        "name": "can-add weapon mods",
        "sig": h("48 8B 43 38  3B 48 28  0F 8E"),  # mov rax,[rbx+38]; cmp ecx,[rax+28]; jle ok
        "edits": [(0, h("48 8B 43 38 3B 48 28"), h("90  81 F9 00 00 00 00"), 3)],  # cmp ecx,LIMIT
    },
]
for slot, name in ((0x24, "personal"), (0x28, "weapon")):
    sig = h("48 85 C0 74 12  48 8B 40 38  48 85 C0 74 09  48 8B 40 38  8B 48 %02X EB 03 41 8B CC" % slot)
    PATCHES.append(
        {
            "name": "ui readout %s mods" % name,
            "sig": sig,
            "edits": [
                (4, h("12"), h("0D"), -1),  # null-object paths now land on the immediate load
                (13, h("09"), h("04"), -1),
                (18, sig[18:26], h("B9 00 00 00 00  90 90 90"), 1),  # mov ecx,LIMIT
            ],
        }
    )


def sections(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n = struct.unpack_from("<H", data, pe + 6)[0]
    opt = pe + 24
    so = opt + struct.unpack_from("<H", data, pe + 20)[0]
    out = []
    for i in range(n):
        o = so + i * 40
        vs, va, rs, rp, _, _, _, _, ch = struct.unpack_from("<IIIIIIHHI", data, o + 8)
        out.append((va, vs, rp, rs, ch))
    return out


def exec_ranges(data):
    return [(rp, rp + min(vs, rs)) for va, vs, rp, rs, ch in sections(data) if ch & 0x20000000]


def find_all(data, sig, ranges):
    hits = []
    for lo, hi in ranges:
        p = lo
        while True:
            p = data.find(sig, p, hi)
            if p < 0:
                break
            hits.append(p)
            p += 1
    return hits


def verify():
    patched_views = {}
    for exe in EXES:
        path = os.path.join(GAME, exe)
        if not os.path.exists(path):
            print("skip (not installed):", exe)
            continue
        data = bytearray(open(path, "rb").read())
        ranges = exec_ranges(data)
        for p in PATCHES:
            hits = find_all(bytes(data), p["sig"], ranges)
            if len(hits) != 1:
                sys.exit("%s: %r matched %d times (need exactly 1)" % (exe, p["name"], len(hits)))
            at = hits[0]
            for off, orig, new, lim in p["edits"]:
                assert bytes(data[at + off : at + off + len(orig)]) == orig, (exe, p["name"], off)
                assert len(new) == len(orig), (exe, p["name"], off)
                if lim >= 0:
                    assert new[lim : lim + 4] == b"\0\0\0\0"
                    new = new[:lim] + struct.pack("<i", DEFAULT_LIMIT) + new[lim + 4 :]
                data[at + off : at + off + len(new)] = new
            p.setdefault("_at", {})[exe] = at
        patched_views[exe] = bytes(data)
        print("verified:", exe, {p["name"]: hex(p["_at"][exe]) for p in PATCHES})
    return patched_views


def check_with_capstone(views, show):
    try:
        import capstone
    except ImportError:
        print("capstone not installed; skipping disassembly checks")
        return
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for exe, data in views.items():
        for p in PATCHES:
            at = p["_at"][exe]
            ins = list(md.disasm(data[at : at + len(p["sig"]) + 8], 0))
            if show:
                print("---", exe, p["name"])
                for i in ins:
                    print("   %3x: %-6s %s" % (i.address, i.mnemonic, i.op_str))
            by_addr = {i.address: i for i in ins}
            if p["name"].startswith("can-add"):
                cmp_i = [i for i in ins if i.mnemonic == "cmp"][0]
                assert str(DEFAULT_LIMIT) in cmp_i.op_str or hex(DEFAULT_LIMIT) in cmp_i.op_str, cmp_i.op_str
                jmp_i = [i for i in ins if i.mnemonic in ("jg", "jle")][0]
                assert jmp_i.address == cmp_i.address + cmp_i.size, "conditional jump must follow cmp directly"
            else:
                mov = by_addr[18]
                assert mov.mnemonic == "mov" and mov.op_str == "ecx, %s" % hex(DEFAULT_LIMIT), mov
                jes = [i for i in ins if i.mnemonic == "je"]
                assert len(jes) == 2 and all(int(j.op_str, 16) == 18 for j in jes), [str(j) for j in jes]
                assert by_addr[23].mnemonic == "nop"
    print("capstone checks passed")


def write_header():
    lines = ["/* generated by tools/build_native.py - do not edit */", "#ifndef PATCHES_H", "#define PATCHES_H", ""]
    lines += ["typedef struct { unsigned off, len; const unsigned char *bytes; int limit_off; } Edit;"]
    lines += ["typedef struct { const char *name; const unsigned char *sig; unsigned sig_len;"]
    lines += ["               const Edit *edits; unsigned n_edits; } Patch;", ""]

    def arr(b):
        return "{" + ",".join("0x%02X" % x for x in b) + "}"

    for i, p in enumerate(PATCHES):
        lines.append("static const unsigned char sig%d[] = %s;" % (i, arr(p["sig"])))
        for j, (off, orig, new, lim) in enumerate(p["edits"]):
            lines.append("static const unsigned char new%d_%d[] = %s;" % (i, j, arr(new)))
        lines.append("static const Edit edits%d[] = {" % i)
        for j, (off, orig, new, lim) in enumerate(p["edits"]):
            lines.append("    {%d, %d, new%d_%d, %d}," % (off, len(new), i, j, lim))
        lines.append("};")
    lines.append("")
    lines.append("#define PATCH_COUNT %d" % len(PATCHES))
    lines.append("static const Patch g_patches[PATCH_COUNT] = {")
    for i, p in enumerate(PATCHES):
        lines.append(
            '    {"%s", sig%d, sizeof sig%d, edits%d, sizeof edits%d / sizeof edits%d[0]},' % (p["name"], i, i, i, i, i)
        )
    lines += ["};", "", "#endif", ""]
    with open(os.path.join(ROOT, "native", "patches.h"), "w", newline="\n") as f:
        f.write("\n".join(lines))


def compile_dll(src, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [
        "zig", "cc", "-target", "x86_64-windows-gnu", "-shared", "-O2", "-s",
        "-fno-builtin", "-fno-stack-protector", "-Wall", "-Wextra",
        "-Wl,--entry=DllMain", "-I", os.path.join(ROOT, "native"),
        os.path.join(ROOT, "native", src), "-lkernel32", "-o", out,
    ]
    subprocess.check_call(cmd)
    return out


def compile_loader():
    """The plugin that loads our bundled Loose Files Loader (used by tools/build.py)."""
    return compile_dll("tableloader.c", os.path.join(ROOT, "build", "native", "ControlModTableLoader.dll"))


INI = """[Inventory]
; Maximum number of Weapon Mods and of Personal Mods you can carry (each).
; The game's own limit is much lower. Valid range 1-9999.
Limit=%d
""" % DEFAULT_LIMIT


def package(dll):
    dist = os.path.join(ROOT, "dist")
    zpath = os.path.join(dist, "Control-ModInventory.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(dll, "plugins/ControlModInventory.dll")
        z.writestr("plugins/ControlModInventory.ini", INI)
    print("wrote", zpath, os.path.getsize(zpath), "bytes")
    loose = os.path.join(dist, "ControlModInventory", "plugins")
    os.makedirs(loose, exist_ok=True)
    with open(dll, "rb") as s, open(os.path.join(loose, "ControlModInventory.dll"), "wb") as d:
        d.write(s.read())
    with open(os.path.join(loose, "ControlModInventory.ini"), "w", newline="\n") as f:
        f.write(INI)


def main():
    views = verify()
    if not views:
        sys.exit("no game executable found to verify against")
    check_with_capstone(views, "--show" in sys.argv)
    write_header()
    dll = os.path.join(ROOT, "build", "native", "ControlModInventory.dll")
    compile_dll("modinventory.c", dll)
    compile_loader()
    package(dll)


if __name__ == "__main__":
    main()
