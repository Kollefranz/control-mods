# Control mod table (Weapon Mods + Personal Mods)

Replaces the tile grids on the Loadout screen with a sortable, filterable table.
Columns: **Icon · Name · Weapon · Type · Effect · Bonus · Damage · Tier** (Personal Mods has no Weapon/Damage column).
The icon is the game's own small mod icon, cropped to the glyph (the originals are ~40% padding) so it adds no height; two mods have no icon in the game data.

## Install (Vortex)

1. **Quit the game.**
2. Vortex → Control → *Install From File* → `dist/Control-ModTable.zip`. **Enable it and click Deploy.**
   The zip bundles reg2k's Loose Files Loader DLL (`iphlpapi.dll`, copied from your own Vortex
   staging) because the game ignores a loose `hud.ui` without it. You do not need to enable the
   separate "Loose Files Loader" mod; if you do, Vortex will just flag the identical DLL.
3. **Check the deploy actually happened** (Vortex has silently deployed nothing before):
   the game folder must contain `iphlpapi.dll` and `data\uiresources\p7\hud.ui`.
4. Start the game; `%LOCALAPPDATA%\Remedy\Control\LooseFilesLoader.log` must now exist and list
   `data\uiresources\p7\hud.ui`. If it doesn't exist, the loader never ran and nothing will change.
5. Open Loadout → click a Weapon Mod slot or a Personal Mod slot.

Known trap: Vortex auto-updates itself and quits, which can interrupt a deploy or leave the game
folder empty (the loader log and files above are the quick way to tell).

### Troubleshooting (nothing shows up in-game)

Symptom of a broken deploy: the game runs fine but shows the stock tile UI. Check in order:

1. **Files deployed at all?** `E:\...\Control` must contain `iphlpapi.dll` and
   `data\uiresources\p7\hud.ui`. If either is missing → click **Deploy** in Vortex.
2. **Loader ran?** `%LOCALAPPDATA%\Remedy\Control\LooseFilesLoader.log` must have a fresh
   timestamp from the last game launch and list `data\uiresources\p7\hud.ui` under
   "Loose file request". No new timestamp = the DLL didn't load (or the game was never launched).
3. **File readable through the link?** Vortex deploys *symlinks* to its staging copies. A symlink
   can report `Length 0` in PowerShell — that is normal. Verify it actually resolves:
   ```powershell
   ([System.IO.File]::OpenRead("E:\...\Control\data\uiresources\p7\hud.ui")).Length
   # must print 1702731 (or similar non-zero), not 0
   ```
   If it throws or returns 0, the staging copy is bad.
4. **Half-deployed state** (one file missing, the other unreadable): click **Purge** in Vortex,
   then **Deploy** again, then re-check 1–3.
5. **Still nothing?** The staging copy itself is wrong: check
   `%APPDATA%\Vortex\control\mods\Control-ModTable\data\uiresources\p7\hud.ui` exists and is
   non-zero. If it is, rebuild (`python -I tools/build.py`) and reinstall; if it isn't, the build
   failed — rerun it and read the output.

If all of the above pass but the table still doesn't appear, check the browser harness
(`python -I test/make_harness.py <dir>`) to see whether the UI code itself is broken.

Manual install: copy `dist/ControlModTable/data` into the game folder (next to `Control_DX12.exe`).

**Uninstall:** disable the mod in Vortex (or delete `data/uiresources/p7/hud.ui` from the game folder).
The original game files are never modified; the loader serves this file in place of the packed one.

**Check the loader picked it up:** `%LOCALAPPDATA%\Remedy\Control\LooseFilesLoader.log` should
list `data\uiresources\p7\hud.ui` after launching the game.

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
  multiply the base (the game's own unused `addWeaponModEffectsToWeapon` does the same). Headshot and
  armor bonuses are shown as multipliers only because the base headshot/armor multiplier isn't in
  the UI data. Per-enemy multipliers are not shown.
- **Assumption to confirm in game:** `m_iDamage` is the weapon's *unmodded* damage. Check: equip a
  damage mod and the tile's `base` number must stay the same while the main number rises.

## Safety

If the table code fails to load or throws at runtime, it switches itself off and the stock tile UI
takes over (both paths tested in the harness). Every patch point is matched exactly once at build
time, so after a game update `tools/build.py` refuses to build instead of producing a broken file.

## What was NOT verified

I never launched the game. Everything was tested in a browser against the game's own UI code with
mock data (sorting, filters, navigation, equip event, failure fallback). Not covered: the real
Coherent GT renderer (CSS/JS quirks), the Loose Files Loader accepting a `.ui` file, gamepad hardware.
If the Loadout screen looks wrong in-game, disable the mod; nothing else is affected.

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

Layout: `src/modtable.js` (module, ES2015 only), `src/modtable.css`, `tools/rmdp.py` (pack reader),
`tools/uitool.py` (`.ui` container extract/repack, byte-exact round trip), `tools/build.py`.
See `REQUIREMENTS.md` for planned work (weapon damage with/without mods).
`build/original/hud.ui` is a copy of the stock game file; it is for personal use, don't redistribute.
