"""Test the plugin that loads the bundled Loose Files Loader, without starting the game.

  python -I test/test_loader.py

A stand-in host exe loads the game's real render library (rl_rmdwin10_f.dll, where the loader
installs its hook) and then our plugin, exactly like the Control Plugin Loader would. Checks:
  1. no iphlpapi.dll in the game folder -> our copy of the loader loads, finds the render
     library's file lookup and sees data\\uiresources\\p7\\hud.ui
  2. an iphlpapi.dll in the game folder    -> we do not load a second copy
  3. bundled loader missing                 -> clean log line, no crash
Note: the loader writes %LOCALAPPDATA%\\Remedy\\Control\\LooseFilesLoader.log (overwritten).
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_native  # noqa: E402

RL = r"E:\SteamLibrary\steamapps\common\Control\rl_rmdwin10_f.dll"
LOG_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Remedy", "Control")

HOST = r"""
#include <windows.h>
#include <stdio.h>
int main(int argc, char **argv) {
    HMODULE rl = LoadLibraryExA(argv[1], NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    HMODULE p = LoadLibraryA(argv[2]);
    printf("%d %d\n", rl != NULL, p != NULL);
    Sleep(3000);
    printf("%d\n", GetModuleHandleA("LooseFilesLoader.bin") != NULL);
    return 0;
}
"""


def read(name):
    p = os.path.join(LOG_DIR, name)
    return open(p, errors="replace").read() if os.path.exists(p) else ""


def run_case(work, with_iphlpapi, with_bin):
    for name in ("ModTableLoader.log", "LooseFilesLoader.log"):
        p = os.path.join(LOG_DIR, name)
        if os.path.exists(p):
            os.remove(p)
    game = os.path.join(work, "game")
    shutil.rmtree(game, ignore_errors=True)
    os.makedirs(os.path.join(game, "plugins", "ControlModTable"))
    os.makedirs(os.path.join(game, "data", "uiresources", "p7"))
    open(os.path.join(game, "data", "uiresources", "p7", "hud.ui"), "wb").write(b"x")
    shutil.copy(HOSTEXE, os.path.join(game, "host.exe"))
    plugin = os.path.join(game, "plugins", "ControlModTableLoader.dll")
    shutil.copy(build_native.compile_loader(), plugin)
    bin_src = os.path.join(ROOT, "build", "vendor", "LooseFilesLoader.bin")
    if with_bin:
        shutil.copy(bin_src, os.path.join(game, "plugins", "ControlModTable", "LooseFilesLoader.bin"))
    if with_iphlpapi:
        shutil.copy(bin_src, os.path.join(game, "iphlpapi.dll"))
    out = subprocess.run([os.path.join(game, "host.exe"), RL, plugin], cwd=game, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.split()
    return lines[-1] == "1", read("ModTableLoader.log"), read("LooseFilesLoader.log")


def main():
    global HOSTEXE
    if not os.path.exists(RL):
        sys.exit("game render library not found: " + RL)
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            print("     " + extra.replace("\n", "\n     "))
            fails += 1

    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "host.c")
        HOSTEXE = os.path.join(work, "host.exe")
        open(src, "w").write(HOST)
        subprocess.check_call(["zig", "cc", "-target", "x86_64-windows-gnu", src, "-o", HOSTEXE], cwd=work)

        loaded, mt, lfl = run_case(work, with_iphlpapi=False, with_bin=True)
        check("no iphlpapi.dll: bundled loader loads", loaded and "Loose Files Loader loaded" in mt, mt)
        check("  loader hooked the file lookup and sees hud.ui",
              "getFileHandle at" in lfl and r"data\uiresources\p7\hud.ui" in lfl, lfl)

        loaded, mt, lfl = run_case(work, with_iphlpapi=True, with_bin=True)
        check("iphlpapi.dll present: no second copy", not loaded and "Not loading our copy" in mt, mt)

        loaded, mt, lfl = run_case(work, with_iphlpapi=False, with_bin=False)
        check("bundled loader missing: logged, no crash", not loaded and "Bundled loader missing" in mt, mt)

    print("FAILED" if fails else "all passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
