# Control UI mod: requirements

## Done
- Weapon Mods and Personal Mods lists as a sortable/filterable table (name, weapon, type, effect,
  bonus, tier). Verified in the real game (2026-10-11).
- Delivered as a loose-file override of `data/uiresources/p7/hud.ui` plus the bundled Loose Files Loader.
- Weapon damage on weapon tiles (with/without mods) and a Damage column in the mod table.
  Verified in the browser harness against an independent calculation; needs an in-game check
  (see docs/GUIDE.md "Damage numbers", assumption about `m_iDamage`).

- Inventory cap for Weapon Mods / Personal Mods raised to 500 (configurable) via an in-memory plugin
  (`native/`). Counter shows 50/500 in the real game (docs/GUIDE.md "Bigger mod inventory").

## Later / ideas
- Damage multipliers per enemy type (not in the UI data; would need the game's balance data).
- Real headshot/armor multipliers (base values not in the UI data).
- Damage-per-second (needs the unit of `m_iRateOfFire`, unknown).
- Filter chips reachable by controller (currently mouse only).
- Show damage in the weapon details panel (lives in persistent.ui, a second override file).
- Remember sort/filters across game restarts.
