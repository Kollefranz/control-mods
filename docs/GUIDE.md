# Control mod table (Weapon Mods + Personal Mods): guide

Replaces the tile grids on the Loadout screen with a sortable, filterable table.
Columns: **Icon · Name · Weapon · Type · Effect · Bonus · Damage · Tier** (Personal Mods has no Weapon/Damage column).
The icon is the game's own small mod icon, cropped to the glyph (the originals are ~40% padding) so it adds no height; two mods have no icon in the game data.

## Install (Vortex)

Needs the **Control Plugin Loader** mod (reg2k, `xinput1_4.dll`; the Blurry Textures mod ships it too).
Nothing else: the Loose Files Loader is bundled and loaded by our own plugin.

1. **Quit the game.**
2. Vortex -> Control -> *Install From File* -> `dist/Control-ModTable.zip` (replace the old one if asked).
   Enable it and click Deploy.
3. Run `python -I tools/check_install.py`. It must end with `READY`.
4. Start the game, open Loadout and click a Weapon Mod or Personal Mod slot.

Contents of the zip: `data/uiresources/p7/hud.ui` (the UI), `plugins/ControlModTableLoader.dll` (our plugin) and
`plugins/ControlModTable/LooseFilesLoader.bin` (reg2k's Loose Files Loader, renamed; copied from your own Vortex
staging into `build/vendor/` when packaging).

**Why not `iphlpapi.dll`?** That is the loader's usual file name, and the Loose Files Loader mod, the Blurry Textures
mod and the earlier version of this mod all shipped it. Vortex resolves such conflicts by creating symlinks in its
staging folder, which fails with `EPERM` unless Windows Developer Mode is on, and leaves the game folder with *no*
`iphlpapi.dll` while Vortex still shows everything as enabled (this happened more than once). Our plugin only loads its
own copy when the game folder has no `iphlpapi.dll`, so the UI works either way and the loader is never loaded twice.
(Turning on Windows Developer Mode also stops that Vortex error for other mods.)

### Troubleshooting (stock tile UI shows up)

Run `python -I tools/check_install.py` first; it checks everything below. By hand:

1. The game folder (`E:\...\Control`) must contain `data\uiresources\p7\hud.ui`, `plugins\ControlModTableLoader.dll`,
   `plugins\ControlModTable\LooseFilesLoader.bin` and `xinput1_4.dll`. Anything missing -> Deploy in Vortex
   (if still missing: Purge, then Deploy).
2. `%LOCALAPPDATA%\Remedy\Control\PluginLoader.log` (fresh timestamp) must list `ControlModTableLoader.dll`.
3. `%LOCALAPPDATA%\Remedy\Control\ModTableLoader.log` must say `Loose Files Loader loaded` (or that the game folder
   provides `iphlpapi.dll`).
4. `%LOCALAPPDATA%\Remedy\Control\LooseFilesLoader.log` must list `data\uiresources\p7\hud.ui`.
5. Symlinks can show `Length 0` in PowerShell; that is normal. `check_install.py` reads through the link.
6. If all of that is fine and the table still doesn't appear, try the browser harness
   (`python -I test/make_harness.py <dir>`) to see whether the UI code itself is broken.

Manual install (no Vortex): copy the contents of `dist/ControlModTable` into the game folder (next to
`Control_DX12.exe`).

**Uninstall:** disable the mod in Vortex. The original game files are never modified.

## Using it

| Action | Mouse | Keyboard / controller |
|---|---|---|
| Sort | click a column header (click again to flip) | **Y** cycles Newest → Tier ▼ → Tier ▲ → Name → Type → Effect → Bonus |
| Filter tier | click tier chips (I–VI, multi-select, with counts) | not available |
| Filter type | click a type chip (Damage, Ammo, Health, …) | not available |
| Fits weapon | toggle "Fits <weapon>" (default on; hides mods the current weapon can't use) | not available |
| Clear filters | "Clear" | not available |
| Equip | click a row | move with Up/Down, Select |

Notes
- Left/Right act like Up/Down in the list (the game's grid navigation treats a full-width row that way).
- Filters/sort reset when the game restarts.
- The bar shows `shown / total` mods.
- "Type" is derived from the effect text (Damage, Fire rate, Reload, Ammo, Handling, Projectile for
  weapon mods; Health, Energy, Efficiency, Ammo, Source, Mobility, Shield, Offense for personal
  mods). The game has no such field; unknown effects land in "Other".
- Table labels (Tier, Type, Clear, …) are English only; mod names and effects follow the game language.

## Damage numbers

- **Weapon tiles** (Loadout root and the weapon list) show `DAMAGE <modded>` and, when mods change
  it, `base <n>`. Conditional bonuses show as multipliers (`Low health ×1.74`, `Aimed ×1.34`,
  `After kill`, `Headshot`, `Armor`).
- **Mod table** gets a **Damage** column (weapon mods only): the weapon's damage if that mod went into
  the slot you're editing, with `+/−` vs. what's equipped now and a tag for conditional mods. Mods
  that don't affect damage show `—`. Sortable. A summary line above the filters shows the weapon's
  current damage.
- Model: base is the game's own per-weapon `m_iDamage`; percentages from damage mods **add** and
  multiply the base (the game's own unused `addWeaponModEffectsToWeapon` does the same). Per-enemy
  multipliers are not shown.
- **How headshot damage actually works** (from the exe property tables): headshots run through the
  weapon's crit system. Each weapon has `m_fCriticalChance` / `m_fCriticalMultiplier` (random crits)
  and `m_fCriticalChanceHead` / `m_fCriticalMultiplierHead` ("Damage multiplier when scoring a
  critical hit with a headshot"); a headshot crit multiplies the hit and headshot-damage mods
  (`MOD_EFFECT_WEAPON_HEADSHOT_DAMAGE`) add on top. The **base multiplier cannot be shown in the
  UI damage column**: the engine mirrors a fixed field list to the UI and the crit fields are not
  in it (not on Loadout items, not on `g_playerWeapon`, not in `g_gameplayConstants`; the hud
  bundle never references them, and the values in the CID data files have hashed property names,
  so they can't be extracted to hardcode a per-weapon table either). Verified 2026-10-11.
- **Assumption to confirm in game:** `m_iDamage` is the weapon's *unmodded* damage. Check: equip a
  damage mod and the tile's `base` number must stay the same while the main number rises.

## Bigger mod inventory (plugin)

A second, independent mod: `dist/Control-ModInventory.zip` raises the carry limit for **Weapon Mods** and
**Personal Mods** (each) to **500**. Without it the game stops you picking up new mods at its own, much lower, cap.

- **Needs** reg2k's *Control Plugin Loader* (`xinput1_4.dll`, loads `plugins\*.dll`). Some other mods already
  ship it (the Blurry Textures fix does); `%LOCALAPPDATA%\Remedy\Control\PluginLoader.log` shows whether it runs.
- **Install:** Vortex → *Install From File* → the zip, enable, Deploy. It puts `plugins\ControlModInventory.dll`
  and `.ini` into the game folder.
- **Change the number:** edit `plugins\ControlModInventory.ini` (`Limit=500`, 1-9999; junk or 0 falls back to 500).
- **Check it ran:** `%LOCALAPPDATA%\Remedy\Control\ModInventory.log` must end with `Patched.` (it lists every
  patch point; any mismatch means nothing is patched).
- **How:** the DLL patches the running game in memory (no file on disk is touched). The game checks the cap in
  two "can this item be added" branches and mirrors it for the UI; the plugin swaps the cap for the constant.
  Fields: `m_iCharacterModsLimit` (Personal) and `m_iWeaponModsLimit` (Weapon) of the inventory settings object.
  Patch points are found by byte signature (must match exactly once, in `Control_DX12.exe` and `Control_DX11.exe`),
  so a game update that moves code is harmless; one that changes it makes the plugin do nothing instead of crashing.
- **Verified in the real game:** the mod counter shows `50/500` in the Loadout. Also checked offline: signatures
  against both installed exes, disassembly of every patched region, and the DLL loaded into a stand-in host exe
  (`python -I test/test_native.py`: ini handling, missing and ambiguous signatures). Unknown: whether other game
  code (e.g. a pickup notification) also reads the limit.
- Same technique as the Nexus mod "Infinite Mods" (which sets the cap to 99 and removes the add check); this one keeps a
  real, configurable number and verifies the code before touching it.
- Loot you cannot pick up before this mod is not recovered; only new pickups benefit.

## Safety

If the table code fails to load or throws at runtime, it switches itself off and the stock tile UI
takes over (both paths tested in the harness). Every patch point is matched exactly once at build
time, so after a game update `tools/build.py` refuses to build instead of producing a broken file.

## What was NOT verified

The table, icons and damage readouts were checked in the real game by the user. Not verified: gamepad
hardware, and some edge cases of the inventory plugin (see its section). If the Loadout screen looks wrong
in-game, disable the mod; nothing else is affected.

## Rebuild / develop

```
python -I tools/build.py            # reads stock hud.ui (cached in build/original), writes dist/
python -I test/make_harness.py <dir>  # offline browser harness from the game's own files
cd <dir>; python -I -m http.server 8765 --bind 127.0.0.1
```
Open `http://127.0.0.1:8765/uiresources/p7/hud.html`, then in the console:
`engine.trigger("OnGameplayMenuOpened")`, `engine.trigger("OnNavigateRight")`, `engine.trigger("OnSelect")`.
Switches: `?vanilla` (stock UI), `?broken` (module throws at load), `?raf` (needed if the browser
tab is hidden, otherwise animations/scrolling freeze). After editing `src/`, run
`python -I tools/build.py --harness <dir>`.

Native plugins (need `zig` on PATH, optionally `capstone` for the disassembly checks):
```
python -I tools/build_native.py [--show]   # verify signatures, generate native/patches.h, build, package
python -I test/test_native.py              # inventory plugin: stand-in host exe, checks the patched bytes
python -I test/test_loader.py              # loader plugin: real render library + bundled loader in a fake game folder
```
Layout: `src/modtable.js` (module, ES2015 only), `src/modtable.css`, `tools/rmdp.py` (pack reader),
`tools/uitool.py` (`.ui` container extract/repack, byte-exact round trip), `tools/build.py`.
`native/modinventory.c` (inventory plugin), `native/tableloader.c` (loads the bundled Loose Files Loader), `tools/build_native.py`, `tools/check_install.py`. See `REQUIREMENTS.md` for planned work.
`build/original/hud.ui` is a copy of the stock game file; it is for personal use, don't redistribute.
