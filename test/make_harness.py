"""Assemble the offline browser harness from the game's own files (read-only).

  python -I test/make_harness.py <outdir>
  cd <outdir> && python -I -m http.server 8765 --bind 127.0.0.1
  open http://127.0.0.1:8765/uiresources/p7/hud.html

Query switches: ?vanilla (stock bundle)  ?broken (module throws at load)  ?raf (timer-based
requestAnimationFrame, for when the browser pane is hidden/occluded).
Open the loadout with:  engine.trigger("OnGameplayMenuOpened"), then OnNavigateRight + OnSelect.
After editing src/, run tools/build.py --harness <outdir>.
"""

import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from rmdp import read_index  # noqa: E402
from uitool import UiBundle  # noqa: E402

GAME_PACKS = r"E:\SteamLibrary\steamapps\common\Control\data_packfiles"


def read_from_pack(pack, wanted):
    for path, off, ln in read_index(os.path.join(GAME_PACKS, pack + ".bin")):
        if path == wanted:
            with open(os.path.join(GAME_PACKS, pack + ".rmdp"), "rb") as f:
                f.seek(off)
                return f.read(ln)
    raise SystemExit(f"{wanted} not found in {pack}")


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def decode_strings(data):
    p, out = 12, {}
    while p < len(data):
        (kl,) = struct.unpack_from("<I", data, p)
        p += 4
        key = data[p : p + kl].decode("ascii")
        p += kl
        (vl,) = struct.unpack_from("<I", data, p)
        p += 4
        out[key] = data[p : p + vl * 2].decode("utf-16le")
        p += vl * 2
    return out


def main():
    out = os.path.abspath(sys.argv[1])
    p7 = os.path.join(out, "uiresources", "p7")

    hud = UiBundle(read_from_pack("ep100-000-generic", "data/uiresources/p7/hud.ui"))
    persistent = UiBundle(read_from_pack("ep100-000-generic", "data/uiresources/p7/persistent.ui"))
    for ui in (hud, persistent):
        for e in ui.entries:
            write(os.path.join(out, *e[0].split("/")), ui.blob_of(e))
    # the "vanilla" copies for A/B comparison
    os.replace(os.path.join(p7, "hud.bundle.js"), os.path.join(p7, "hud.bundle.vanilla.js"))
    with open(os.path.join(p7, "hud.css"), "rb") as f:
        write(os.path.join(p7, "hud.vanilla.css"), f.read())

    html = open(os.path.join(p7, "hud.html"), encoding="utf-8").read()
    raf = (
        "<script>if(/raf/.test(location.search)){window.requestAnimationFrame=function(cb){"
        "return setTimeout(function(){cb(performance.now())},16)};"
        "window.cancelAnimationFrame=function(i){clearTimeout(i)}}</script>"
    )
    html = html.replace("<title>Webpack App</title>", "<title>Webpack App</title>\n" + raf)
    html = html.replace(
        '<link href="hud.css" rel="stylesheet">',
        "<script>var V=/vanilla/.test(location.search);document.write('<link href=\"'"
        '+(V?"hud.vanilla.css":"hud.css")+\'" rel="stylesheet">\')</script>',
    )
    html = html.replace(
        '<script type="text/javascript" src="hud.bundle.js"></script>',
        "<script>document.write('<script src=\"'+(V?\"hud.bundle.vanilla.js\":(/broken/.test(location.search)"
        '?"hud.bundle.broken.js":"hud.bundle.js"))+\'"><\\/script>\')</script>\n'
        '<script src="testdata.js"></script>',
    )
    write(os.path.join(p7, "hud.html"), html.encode("utf-8"))

    en = read_from_pack("ep100-000-generic-en", "data/locale/en/string_table.bin")
    loc_json = os.path.join(out, "loc_en.json")
    write(loc_json, json.dumps(decode_strings(en), ensure_ascii=False).encode("utf-8"))
    subprocess.check_call(
        [sys.executable, "-I", os.path.join(HERE, "gen_testdata.py"), loc_json, os.path.join(p7, "testdata.js")]
    )

    subprocess.check_call([sys.executable, "-I", os.path.join(HERE, "icons_to_png.py"), out])

    build = os.path.join(ROOT, "tools", "build.py")
    subprocess.check_call([sys.executable, "-I", build, "--harness", out])

    # variant whose module throws at load (fail-soft test)
    js = open(os.path.join(ROOT, "build", "hud.bundle.patched.js"), encoding="utf-8").read()
    marker = '"./mod/ModTable.js":function(module,exports,__webpack_require__){"use strict";'
    assert js.count(marker) == 1
    js = js.replace(marker, marker + 'throw new Error("simulated load failure");')
    write(os.path.join(p7, "hud.bundle.broken.js"), js.encode("utf-8"))
    print("harness ready:", out)


if __name__ == "__main__":
    main()
