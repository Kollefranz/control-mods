"""Check that both mods are really installed and running. Read-only.

  python -I tools/check_install.py

Looks at the game folder (what Vortex deployed), the plugin/loader logs from the last game
launch, and whether several Vortex mods ship the same loader file (that conflict is what broke
earlier installs). Exit code 1 if anything needed for the UI table is wrong.
"""

import os
import sys
import time

GAME = r"E:\SteamLibrary\steamapps\common\Control"
STAGING = os.path.join(os.environ.get("APPDATA", ""), "Vortex", "control", "mods")
LOGS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Remedy", "Control")

problems = 0


def say(kind, msg):
    global problems
    if kind == "FAIL":
        problems += 1
    print("%-5s %s" % (kind, msg))


def size_through_link(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except OSError:
        return None


def need(rel, min_size=1):
    p = os.path.join(GAME, rel)
    n = size_through_link(p)
    if n is None:
        say("FAIL", "%s missing (or a broken link). Deploy in Vortex." % rel)
    elif n < min_size:
        say("FAIL", "%s is empty/too small (%d bytes)." % (rel, n))
    else:
        say("ok", "%s (%d bytes)" % (rel, n))
    return n is not None and n >= min_size


DEPLOYED = 0


def deploy_time():
    """When Vortex last linked our files (lstat: the link itself, not the staged target)."""
    times = []
    for rel in (r"data\uiresources\p7\hud.ui", r"plugins\ControlModTableLoader.dll", r"plugins\ControlModInventory.dll"):
        p = os.path.join(GAME, rel)
        if os.path.lexists(p):
            times.append(os.lstat(p).st_mtime)
    return max(times) if times else 0


def log(name):
    """(timestamp, text); logs older than the last deploy are ignored, they predate this install."""
    p = os.path.join(LOGS, name)
    if not os.path.exists(p) or os.path.getmtime(p) < DEPLOYED:
        return None, ""
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))), open(p, errors="replace").read()


def main():
    global DEPLOYED
    DEPLOYED = deploy_time()
    print("== files in the game folder")
    need("xinput1_4.dll", 1000)  # Control Plugin Loader; loads plugins\*.dll
    ui = need(r"data\uiresources\p7\hud.ui", 1_000_000)
    ldr = need(r"plugins\ControlModTableLoader.dll", 1000)
    lfl = need(r"plugins\ControlModTable\LooseFilesLoader.bin", 1000)
    ip = os.path.join(GAME, "iphlpapi.dll")
    if os.path.lexists(ip):
        if size_through_link(ip):
            say("ok", "iphlpapi.dll present: the plugin will leave loading to it")
        else:
            say("warn", "iphlpapi.dll is a broken link; the bundled loader is used instead. Purge+Deploy in Vortex cleans it up.")
    inv = os.path.exists(os.path.join(GAME, "plugins", "ControlModInventory.dll"))
    say("ok" if inv else "info", "inventory plugin %s" % ("installed" if inv else "not installed (optional)"))

    print("== Vortex staging: files several mods ship (this is what breaks installs)")
    owners = {}
    if os.path.isdir(STAGING):
        for mod in sorted(os.listdir(STAGING)):
            for name in ("iphlpapi.dll", "xinput1_4.dll"):
                if os.path.lexists(os.path.join(STAGING, mod, name)):
                    owners.setdefault(name, []).append(mod)
    for name, mods in owners.items():
        if len(mods) > 1:
            say("warn", "%s is shipped by %d mods: %s" % (name, len(mods), "; ".join(m[:40] for m in mods)))
        else:
            say("ok", "%s only in: %s" % (name, mods[0][:60]))

    print("== logs from the last game launch")
    t, txt = log("PluginLoader.log")
    if t is None:
        say("info", "PluginLoader.log: no launch since the last deploy; start the game, then run this again")
    else:
        say("ok", "PluginLoader.log %s: %s" % (t, " | ".join(l for l in txt.splitlines()[1:]) or "no plugins"))
    t, txt = log("ModTableLoader.log")
    if t is None:
        say("info", "ModTableLoader.log: nothing since the last deploy (normal if iphlpapi.dll is deployed)")
    else:
        say("ok" if "loaded" in txt or "Not loading" in txt else "FAIL", "ModTableLoader.log %s: %s" % (t, txt.splitlines()[-1] if txt else ""))
    t, txt = log("LooseFilesLoader.log")
    if t is None:
        say("info", "LooseFilesLoader.log: nothing since the last deploy; start the game, then run this again")
    else:
        served = r"data\uiresources\p7\hud.ui" in txt
        say("ok" if served else "FAIL", "LooseFilesLoader.log %s: hud.ui %s" % (t, "found" if served else "NOT listed"))
    t, txt = log("ModInventory.log")
    if t is not None:
        say("ok" if "Patched." in txt else "FAIL", "ModInventory.log %s: %s" % (t, txt.splitlines()[-1] if txt else ""))

    ready = ui and ldr and lfl
    print()
    print("READY: start the game and open a mod list." if ready and not problems else "NOT READY: fix the FAIL lines above.")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
