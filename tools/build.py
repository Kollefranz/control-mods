"""Build the Control mod-table UI mod.

Reads the stock hud.ui (cached in build/original after the first run), patches the
bundled React app, repacks it, and writes a Vortex-installable folder to dist/.
Never writes into the game directory.

  python -I tools/build.py [--refresh] [--harness DIR]
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rmdp import read_index  # noqa: E402
from uitool import UiBundle  # noqa: E402

GAME = r"E:\SteamLibrary\steamapps\common\Control"
PACK = os.path.join(GAME, "data_packfiles", "ep100-000-generic")
UI_PATH = "data/uiresources/p7/hud.ui"
JS_NAME = "uiresources/p7/hud.bundle.js"
CSS_NAME = "uiresources/p7/hud.css"
CACHE = os.path.join(ROOT, "build", "original", "hud.ui")
DIST = os.path.join(ROOT, "dist", "ControlModTable", "data", "uiresources", "p7", "hud.ui")

GEAR_SECTION = "./game/gameplay-menu/components/LinkGameplayMenu/GearSection.tsx"
GEAR_TILE = "./game/gameplay-menu/components/LinkGameplayMenu/GearTile.tsx"


def load_original(refresh):
    if refresh or not os.path.isfile(CACHE):
        for path, off, ln in read_index(PACK + ".bin"):
            if path == UI_PATH:
                with open(PACK + ".rmdp", "rb") as f:
                    f.seek(off)
                    data = f.read(ln)
                break
        else:
            sys.exit("hud.ui not found in pack")
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "wb") as f:
            f.write(data)
    with open(CACHE, "rb") as f:
        return f.read()


def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"patch '{label}': expected exactly 1 match, found {n} (game updated?)")
    return text.replace(old, new)


def patch_js(js, module_src):
    # A: load our module when GearSection loads; every other hook checks window.__MT
    js = once(
        js,
        GEAR_SECTION + '":function(e,t,o){"use strict";',
        GEAR_SECTION + '":function(e,t,o){"use strict";'
        'try{window.__MT=o("./mod/ModTable.js")}catch(MTe){window.__MT=null;'
        'try{console.error("[ModTable] load failed",MTe)}catch(MTx){}}',
        "A load module",
    )
    # B: pass numCols down to the tile renderer
    js = once(
        js,
        "showSlots:this.props.showSlots,equipmentType:this.props.equipmentType})}renderEquipmentS",
        "showSlots:this.props.showSlots,equipmentType:this.props.equipmentType,"
        "numCols:this.props.numCols})}renderEquipmentS",
        "B numCols",
    )
    # C: mod rows span the whole grid row
    js = once(
        js,
        "let o=this.props.showSlots?t+1:t;return e.m_eType===n.ItemType.WEAPON&&(o=3*t),",
        "let o=this.props.showSlots?t+1:t;"
        "const MTW=window.__MT&&window.__MT.on()&&this.props.equipmentType!==m.UIItemType.WEAPON"
        "?this.props.numCols:void 0;"
        "return e.m_eType===n.ItemType.WEAPON&&(o=3*t),",
        "C row width",
    )
    for tile in ("WeaponModGearTile", "PlayerModGearTile"):
        js = once(
            js,
            f"c.{tile},{{key:e.m_uID,item:e,type:this.props.equipmentType,index:o,height:1}}",
            f"c.{tile},{{key:e.m_uID,item:e,type:this.props.equipmentType,index:o,height:1,width:MTW}}",
            f"C {tile}",
        )
    # D: filter + sort the data, no empty-slot padding
    js = once(
        js,
        "if(this.props.maxCount)for(let e=t.length;e<this.props.maxCount;e++)t.push({m_eType:n.ItemType.NONE,m_uID:-e});return t}",
        "if(window.__MT&&window.__MT.on()&&this.props.equipmentType!==m.UIItemType.WEAPON){"
        "try{return window.__MT.apply(t,this.props.equipmentType,e)}catch(MTe){window.__MT.fail(MTe)}}"
        "if(this.props.maxCount)for(let e=t.length;e<this.props.maxCount;e++)t.push({m_eType:n.ItemType.NONE,m_uID:-e});return t}",
        "D data",
    )
    # E: our toolbar replaces the Order New/Rarity/Type switcher
    js = once(
        js,
        'this.props.equipmentType!==m.UIItemType.WEAPON&&s.createElement(h.default,{activeSortType:i,disabled:!t,titleLocID:"INVENTORY_MOD_SORT",',
        "this.props.equipmentType!==m.UIItemType.WEAPON&&(window.__MT&&window.__MT.on()"
        "?window.__MT.header(this.props.equipmentType,s,t,o)"
        ':s.createElement(h.default,{activeSortType:i,disabled:!t,titleLocID:"INVENTORY_MOD_SORT",',
        "E header open",
    )
    js = once(
        js,
        "onClick:o.setSortTypeType}]}),s.createElement(I.default,{isActive:t",
        "onClick:o.setSortTypeType}]})),s.createElement(I.default,{isActive:t",
        "E header close",
    )
    # F: tile base class renders a table row for mods (original body is the fallback)
    js = once(
        js,
        "render(){const e=this.isModding(),t=this.isHiddenDown(),",
        "render(){if(window.__MT&&window.__MT.on()&&this.props.type!==m.UIItemType.WEAPON){"
        "try{return window.__MT.row(this,s,d.TileWithScrolling)}catch(MTe){window.__MT.fail(MTe)}}"
        "const e=this.isModding(),t=this.isHiddenDown(),",
        "F row",
    )
    # H: damage readout on the Loadout root weapon tiles
    js = once(
        js,
        's.createElement(T.default,{showLabel:!0}))}};I=i([a.inject("gearMenu")],I)',
        's.createElement(T.default,{showLabel:!0}),'
        '(window.__MT&&window.__MT.on()?window.__MT.weaponStats(this.props.item,s):null))}};I=i([a.inject("gearMenu")],I)',
        "H root weapon tile",
    )
    # J: damage readout on weapon tiles in the weapon list
    js = once(
        js,
        "progress:a,progressTypeDismantle:!0},_),m,c,l)",
        "progress:a,progressTypeDismantle:!0},_),m,c,l,"
        "(window.__MT&&window.__MT.on()&&this.props.item.m_eType===n.ItemType.WEAPON"
        "?window.__MT.weaponStats(this.props.item,s):null))",
        "J list weapon tile",
    )
    # G: register the module
    js = once(
        js,
        '"' + GEAR_TILE + '":function(',
        '"./mod/ModTable.js":function(module,exports,__webpack_require__){' + module_src + '},"' + GEAR_TILE + '":function(',
        "G module",
    )
    return js


VORTEX_LOADER = os.path.join(
    os.environ.get("APPDATA", ""),
    "Vortex",
    "control",
    "mods",
    "Loose Files Loader 1.1-11-1-1-1577247191",
    "iphlpapi.dll",
)
LOADER_CACHE = os.path.join(ROOT, "build", "vendor", "LooseFilesLoader.bin")


def loader_dll():
    """reg2k's Loose Files Loader, cached under build/ so packaging does not depend on Vortex's folder."""
    if not os.path.isfile(LOADER_CACHE):
        if not os.path.isfile(VORTEX_LOADER):
            sys.exit("Loose Files Loader DLL not found; put a copy at " + LOADER_CACHE)
        os.makedirs(os.path.dirname(LOADER_CACHE), exist_ok=True)
        shutil.copyfile(VORTEX_LOADER, LOADER_CACHE)
    return LOADER_CACHE


def package():
    """hud.ui + a plugin that loads the bundled Loose Files Loader (no iphlpapi.dll in the mod)."""
    import zipfile

    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build_native

    plugin = build_native.compile_loader()
    loader = loader_dll()
    out_dir = os.path.join(ROOT, "dist")
    zip_path = os.path.join(out_dir, "Control-ModTable.zip")
    files = {
        "data/uiresources/p7/hud.ui": DIST,
        "plugins/ControlModTableLoader.dll": plugin,
        "plugins/ControlModTable/LooseFilesLoader.bin": loader,
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in files.items():
            z.write(src, arc)
            dst = os.path.join(out_dir, "ControlModTable", *arc.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
    stale = os.path.join(out_dir, "ControlModTable", "iphlpapi.dll")
    if os.path.exists(stale):
        os.remove(stale)
    print("wrote", zip_path, "(loader sha256 %s)" % hashlib.sha256(open(loader, "rb").read()).hexdigest()[:16])


def node_check(path):
    node = r"C:\Users\catsnax\scoop\persist\nvm\nodejs\v24.14.1\node.exe"
    if not os.path.isfile(node):
        print("node not found; skipping syntax check")
        return
    r = subprocess.run([node, "--check", path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("syntax check failed:\n" + r.stderr)
    print("node --check OK:", os.path.basename(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--harness")
    a = ap.parse_args()

    original = load_original(a.refresh)
    print("original hud.ui sha256", hashlib.sha256(original).hexdigest()[:16], len(original), "bytes")
    ui = UiBundle(original)
    parts = {e[0]: ui.blob_of(e) for e in ui.entries}

    module_src = open(os.path.join(ROOT, "src", "modtable.js"), encoding="utf-8").read()
    css_src = open(os.path.join(ROOT, "src", "modtable.css"), encoding="utf-8").read()

    js = patch_js(parts[JS_NAME].decode("utf-8"), module_src)
    css = parts[CSS_NAME].decode("utf-8") + "\n" + css_src

    out = ui.repack({JS_NAME: js.encode("utf-8"), CSS_NAME: css.encode("utf-8")})

    # verify: re-parse and compare every entry
    again = UiBundle(out)
    got = {e[0]: again.blob_of(e) for e in again.entries}
    assert got[JS_NAME] == js.encode("utf-8") and got[CSS_NAME] == css.encode("utf-8")
    for name, blob in parts.items():
        if name not in (JS_NAME, CSS_NAME):
            assert got[name] == blob, name
    print("repack verified; hud.ui", len(original), "->", len(out), "bytes")

    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    with open(DIST, "wb") as f:
        f.write(out)
    print("wrote", DIST)

    package()

    tmp = os.path.join(ROOT, "build", "hud.bundle.patched.js")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(js)
    node_check(tmp)

    if a.harness:
        p7 = os.path.join(a.harness, "uiresources", "p7")
        with open(os.path.join(p7, "hud.bundle.js"), "w", encoding="utf-8", newline="") as f:
            f.write(js)
        with open(os.path.join(p7, "hud.css"), "w", encoding="utf-8", newline="") as f:
            f.write(css)
        print("harness updated:", p7)


if __name__ == "__main__":
    main()
