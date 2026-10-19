"""Test the inventory plugin DLL without starting the game.

  python -I test/test_native.py

Builds a tiny host exe whose .text contains the real patch signatures, loads the DLL into it
and compares the resulting bytes with the edits from tools/build_native.py. Also covers:
a custom limit from the .ini, a missing signature (nothing may be patched), an ambiguous
signature (nothing may be patched).
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_native as bn  # noqa: E402


def host_source(sigs):
    lines = ["#include <windows.h>", "#include <stdio.h>"]
    for i, s in enumerate(sigs):
        body = ",".join("0x%02X" % b for b in s)
        lines.append('__attribute__((section(".text"),used)) const volatile unsigned char g%d[] = {%s};' % (i, body))
        lines.append('__attribute__((section(".text"),used)) const volatile unsigned char pad%d[16] = {0xCC};' % i)
    lines.append("int main(int argc, char **argv) {")
    lines.append('    if (!LoadLibraryA(argv[1])) { printf("LOADFAIL\\n"); return 2; }')
    for i, s in enumerate(sigs):
        lines.append('    for (int k = 0; k < %d; k++) printf("%%02X", g%d[k]); printf("\\n");' % (len(s), i))
    lines.append("    return 0;\n}")
    return "\n".join(lines)


def expected(sig, patch, limit):
    out = bytearray(sig)
    for off, orig, new, lim in patch["edits"]:
        assert bytes(out[off : off + len(orig)]) == orig
        if lim >= 0:
            new = new[:lim] + struct.pack("<i", limit) + new[lim + 4 :]
        out[off : off + len(new)] = new
    return bytes(out)


def run(work, sigs, limit_ini):
    src = os.path.join(work, "host.c")
    exe = os.path.join(work, "host.exe")
    open(src, "w").write(host_source(sigs))
    subprocess.check_call(["zig", "cc", "-target", "x86_64-windows-gnu", src, "-o", exe], cwd=work)
    plug = os.path.join(work, "plugins")
    os.makedirs(plug, exist_ok=True)
    shutil.copy(os.path.join(ROOT, "build", "native", "ControlModInventory.dll"), plug)
    ini = os.path.join(plug, "ControlModInventory.ini")
    if os.path.exists(ini):
        os.remove(ini)
    if limit_ini is not None:
        open(ini, "w").write("[Inventory]\nLimit=%s\n" % limit_ini)
    env = dict(os.environ, LOCALAPPDATA=work)
    os.makedirs(os.path.join(work, "Remedy", "Control"), exist_ok=True)
    out = subprocess.run(
        [exe, os.path.join(plug, "ControlModInventory.dll")], env=env, capture_output=True, text=True, cwd=work
    )
    assert out.returncode == 0, out.stdout + out.stderr
    log = open(os.path.join(work, "Remedy", "Control", "ModInventory.log")).read()
    return [bytes.fromhex(l) for l in out.stdout.split()], log


def main():
    sigs = [p["sig"] for p in bn.PATCHES]
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("ok   " if cond else "FAIL ") + name + (("  " + extra) if not cond else ""))
        fails += 0 if cond else 1

    with tempfile.TemporaryDirectory() as work:
        for ini, limit in ((None, 500), ("1234", 1234), ("0", 500), ("99999999", 9999), ("junk", 500)):
            got, log = run(work, sigs, ini)
            want = [expected(p["sig"], p, limit) for p in bn.PATCHES]
            check("ini=%r -> limit %d, all patches applied" % (ini, limit), got == want, log)
            check("  log says Patched", "Patched." in log, log)

        # one signature missing -> nothing patched at all
        broken = [bytes(s) for s in sigs]
        broken[2] = bytes([broken[2][0] ^ 0xFF]) + broken[2][1:]
        got, log = run(work, broken, None)
        check("missing signature: untouched", got == broken and "no match" in log, log)

        # ambiguous: two copies of one signature -> nothing patched
        got, log = run(work, sigs + [sigs[1]], None)
        check("ambiguous signature: untouched", got == sigs + [sigs[1]] and "ambiguous" in log, log)

    print("FAILED" if fails else "all passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
