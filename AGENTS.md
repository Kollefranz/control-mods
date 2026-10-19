# AGENTS.md

Notes for AI agents working on this repo. Read before debugging "the mod doesn't work".

## Where known issues and state live

- `python -I tools/check_install.py` (read-only): checks deployed files, Vortex file conflicts and the logs.
  Run it first for any "UI is gone / mod doesn't show up".
- `docs/GUIDE.md` → **Troubleshooting** section: the same checklist by hand.
- `docs/GUIDE.md` → **What was NOT verified**: untested areas (real Coherent GT renderer,
  Loose Files Loader `.ui` acceptance, gamepad hardware). Suspect these first for
  in-game-only failures.
- `REQUIREMENTS.md`: planned/unfinished work — check whether the "bug" is actually
  known-unimplemented.
- `%LOCALAPPDATA%\Remedy\Control\LooseFilesLoader.log`: proof the loader served the mod;
  needs a fresh timestamp from the last game launch to mean anything.

## Environment facts (easy to get wrong)

- Game: `E:\SteamLibrary\steamapps\common\Control`; pack at
  `data_packfiles\ep100-000-generic`. `tools/build.py` hardcodes this.
- The UI mod does NOT ship `iphlpapi.dll` (see docs/GUIDE.md "Why not iphlpapi.dll?"): several Vortex mods ship it and
  Vortex's override symlinks fail with EPERM, leaving the game folder without it. Our `plugins/ControlModTableLoader.dll`
  (loaded by the Control Plugin Loader) loads a bundled copy of the Loose Files Loader instead. Don't put it back.
- Installed via **Vortex**: staging in `%APPDATA%\Vortex\control\mods\`, game folder gets
  **symlinks**. Symlink `Length 0` in PowerShell is normal — read through the link instead
  (`[System.IO.File]::OpenRead(path).Length`).
- The stock `hud.ui` cache in `build/original/` is a copy of game data — never commit or
  redistribute it.
- After a game update `tools/build.py` refuses to build (patch anchors no longer match
  exactly once). That is by design; update the anchors in `patch_js()`.

## Debug workflow

1. Verify install/deploy first (docs/GUIDE.md Troubleshooting) — most failures are deploys, not code.
2. In-game UI logic is testable offline: `python -I test/make_harness.py <dir>`, serve it,
   open `http://127.0.0.1:8765/uiresources/p7/hud.html`, trigger events via
   `engine.trigger(...)` in the console. See docs/GUIDE.md "Rebuild / develop".
3. `?vanilla` / `?broken` harness switches isolate stock UI vs the failure-fallback path.
