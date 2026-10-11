"use strict";
// Sortable / filterable table for Weapon Mods and Personal Mods.
// Injected into hud.bundle.js as webpack module "./mod/ModTable.js" (ES2015 only: Coherent GT).
// Fail-soft: any runtime error flips state.enabled off and the vanilla tile UI takes over.

var mobx = __webpack_require__("./node_modules/mobx/lib/mobx.module.js");
var coherent = __webpack_require__("northlight/vendor/coherent");
var translateMod = __webpack_require__("./northlight/utils/translate.ts");
var types = __webpack_require__("./northlight/types.ts");
var gameTypes = __webpack_require__("./game/gameplay-menu/types.ts");
var parse = __webpack_require__("./game/gameplay-menu/utils/parse-mod-description.ts");
var constants = __webpack_require__("./northlight/constants.ts");
var ActionButton = __webpack_require__("./northlight/components/ActionButton/ActionButton.tsx").default;
var sound = __webpack_require__("./northlight/utils/sound.ts");
var React = __webpack_require__("./node_modules/react/index.js");
var Img = __webpack_require__("./northlight/components/Image/Image.tsx");
var mobxReact = __webpack_require__("./node_modules/mobx-react/index.module.js");

var ROMAN = ["I", "II", "III", "IV", "V", "VI"];
var TIER_CLASS = ["common", "uncommon", "rare", "legendary", "exquisite", "ascendant"];

// [sortKey, header text, css modifier]
var COL = {
  icon: ["icon", "", "icon"],
  name: ["name", "Name", "name"],
  weapon: ["weapon", "Weapon", "weapon"],
  type: ["type", "Type", "type"],
  effect: ["effect", "Effect", "effect"],
  value: ["value", "Bonus", "value"],
  damage: ["damage", "Damage", "damage"],
  tier: ["tier", "Tier", "tier"],
};

// The Weapon column is redundant while "Fits weapon" is on; Damage needs a weapon to apply mods to.
function columnsFor(kind, gearMenu) {
  if (kind === "player") return [COL.icon, COL.name, COL.type, COL.effect, COL.value, COL.tier];
  var cols = [COL.icon, COL.name];
  if (!(state.weapon.fits && currentWeapon(gearMenu))) cols.push(COL.weapon);
  cols.push(COL.type, COL.effect, COL.value);
  if (currentWeapon(gearMenu)) cols.push(COL.damage);
  cols.push(COL.tier);
  return cols;
}

// Y cycles through these on keyboard / controller.
var SORT_CYCLE = [
  { key: "new", dir: "desc" },
  { key: "tier", dir: "desc" },
  { key: "tier", dir: "asc" },
  { key: "name", dir: "asc" },
  { key: "type", dir: "asc" },
  { key: "effect", dir: "asc" },
  { key: "value", dir: "desc" },
];
var DEFAULT_DIR = {
  new: "desc",
  tier: "desc",
  value: "desc",
  damage: "desc",
  name: "asc",
  weapon: "asc",
  type: "asc",
  effect: "asc",
};

var state = mobx.observable({
  enabled: true,
  weapon: { sortKey: "new", sortDir: "desc", tiers: [], type: "", fits: true },
  player: { sortKey: "new", sortDir: "desc", tiers: [], type: "" },
});

// ---------- classification ----------

var WEAPON_RULES = [
  [/reload/, "Reload"],
  [/ammo|magazine|clip/, "Ammo"],
  [/rate of fire|fire rate/, "Fire rate"],
  [/damage|headshot|armor/, "Damage"],
  [/accuracy|recoil|spread|dispersion|stability|zoom|aim/, "Handling"],
  [/projectile|blast|radius|speed|charge|grenade|fuse/, "Projectile"],
];
var PLAYER_RULES = [
  [/ammo|reload/, "Ammo"],
  [/source/, "Source"],
  [/^health/, "Health"],
  [/cost/, "Efficiency"],
  [/^energy|energy (gained|recovery)/, "Energy"],
  [/evade|dodge|levitat|movement|fall/, "Mobility"],
  [/shield/, "Shield"],
  [/launch|melee|slam|seize|damage|projectile|grenade|weapon|shot|charge/, "Offense"],
];

function classify(label, isPlayer) {
  var rules = isPlayer ? PLAYER_RULES : WEAPON_RULES;
  var text = label.toLowerCase();
  for (var i = 0; i < rules.length; i++) {
    if (rules[i][0].test(text)) return rules[i][1];
  }
  return "Other";
}

function plain(html) {
  return String(html || "").replace(/<[^>]*>/g, "").replace(/\{[^}]*\}/g, "").replace(/\s+/g, " ").trim();
}

// ---------- per-item info (cached by id, flushed on locale change) ----------

var cache = {};
coherent.on("OnLocaleChanged", function () {
  cache = {};
});

function tr(id) {
  return translateMod.default(id) || id;
}

function buildInfo(item, isPlayer) {
  var effects = item.m_mapModEffects || {};
  var stats = [];
  for (var n = 1; n < 10; n++) {
    var descId = effects["STAT_" + n + "_DESC"];
    if (!descId) continue;
    var value = effects["STAT_" + n + "_PARAM_1"] || "";
    stats.push({ label: plain(tr(descId)), value: String(value), num: parseFloat(String(value).replace("%", "")) });
  }
  if (stats.length === 0) {
    var short = plain(parse.getDescription("SHORT", item)) || plain(tr(item.m_strDescription));
    if (short) stats.push({ label: short, value: "", num: NaN });
  }
  var first = stats.length ? stats[0] : { label: "", value: "", num: NaN };
  var weapons = [];
  var ids = item.m_vecExclusiveToTargetLocIDs || [];
  for (var i = 0; i < ids.length; i++) {
    var w = tr(ids[i]);
    if (weapons.indexOf(w) === -1) weapons.push(w);
  }
  var tier = item.m_eItemRarityType || 0;
  var name = plain(tr(item.m_strName));
  return {
    name: name,
    nameKey: name.toLowerCase(),
    stats: stats,
    effectKey: first.label.toLowerCase(),
    valueNum: first.num,
    category: classify(first.label || name, isPlayer),
    weapons: weapons,
    weaponKey: weapons.join(",").toLowerCase(),
    tier: tier,
    tierText: plain(tr(constants.RARITY_LOCID[tier])) || "",
  };
}

function info(item, isPlayer) {
  var key = item.m_uID + ":" + (isPlayer ? "p" : "w");
  var hit = cache[key];
  if (hit && hit.name !== undefined && hit.src === item.m_strName) return hit;
  var made = buildInfo(item, isPlayer);
  made.src = item.m_strName;
  cache[key] = made;
  return made;
}

// ---------- data pipeline ----------

function kindOf(equipmentType) {
  return equipmentType === types.UIItemType.PLAYER_MOD ? "player" : "weapon";
}

// mods the list can show, before our filters (mirrors GearSection.getData)
function source(equipmentType, gearMenu) {
  if (equipmentType === types.UIItemType.PLAYER_MOD) {
    var equipped = gearMenu.equippedPlayerMods;
    return Array.from(gearMenu.inventoryPlayerMods).filter(function (it) {
      for (var i = 0; i < equipped.length; i++) if (equipped[i].m_uID === it.m_uID) return false;
      return true;
    });
  }
  return Array.from(gearMenu.inventoryWeaponMods);
}

// Same rule as gearMenu.isWeaponModUnEquippable, but reads are tracked: that method is a
// mobx action, so calling it from render would never re-render when the weapon changes.
function blocked(item, gearMenu) {
  if (item.m_eType !== gameTypes.ItemType.WEAPON_MOD) return false;
  var targets = item.m_vecExclusiveToTargets;
  if (!targets || targets.length === 0) return false;
  var weaponId = gearMenu.currentWeaponID;
  var weapons = gearMenu.inventoryWeapons;
  for (var i = 0; i < weapons.length; i++) {
    if (weapons[i].m_uID === weaponId) return targets.indexOf(weapons[i].m_uArchetypeID) === -1;
  }
  return false;
}

// ---------- weapon damage ----------
// Percentages from damage mods add together and multiply the weapon's base damage; this is the
// same rule as the game's own (unused) addWeaponModEffectsToWeapon. Conditional damage mods
// (aiming, low health, after a kill) and headshot/armor bonuses only apply in those situations.

var DMG_KIND = {
  MOD_EFFECT_WEAPON_DAMAGE: "base",
  MOD_EFFECT_WEAPON_PELLET_COUNT: "pellets", // flat +N pellets, not a percentage
  MOD_EFFECT_WEAPON_AIMED_DAMAGE: "aimed",
  MOD_EFFECT_WEAPON_LOW_HEALTH_DAMAGE: "lowhp",
  MOD_EFFECT_WEAPON_AFTER_KILL_DAMAGE: "kill",
  MOD_EFFECT_WEAPON_HEADSHOT_DAMAGE: "head",
  MOD_EFFECT_ARMOR_DAMAGE: "armor",
};
var KIND_TAG = {
  pellets: "pellets",
  aimed: "aiming",
  lowhp: "low HP",
  kill: "on kill",
  head: "headshot",
  armor: "armor",
};
var KIND_NAME = { aimed: "Aimed", lowhp: "Low health", kill: "After kill", head: "Headshot", armor: "Armor" };
var KIND_ORDER = ["aimed", "lowhp", "kill", "head", "armor"];
var NUMBER_KINDS = ["aimed", "lowhp", "kill"]; // shown as a damage number; head/armor only as a multiplier

// Rays (pellets) fired per shot, from the game's balancing table (cid_balancing_data.bin, the
// "ray-cast damage" record: PLAYER_SHOTGUN_DAMAGE = 1500 damage over 10 rays; pistol/SMG/railgun = 1).
// The weapon's damage figure is the total for a shot, so each pellet deals total / pellets. Anything
// not listed fires one ray.
var BASE_PELLETS = { WEAPON_SHOTGUN_SINGLESHOT: 10 };

function fmt(n) {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function mult(pct) {
  return "×" + (1 + pct / 100).toFixed(2);
}

function currentWeapon(gearMenu) {
  var w = gearMenu.moddingWeapon;
  return w && w.m_iDamage > 0 ? w : null;
}

// {base: 12, aimed: 34, pellets: 3, ...} totals of one mod
function modPcts(mod) {
  var out = {};
  var effects = mod && mod.m_mapModEffects;
  if (!effects || mod.m_eType === gameTypes.ItemType.NONE) return out;
  for (var n = 1; n < 10; n++) {
    var id = effects["STAT_" + n + "_DESC"];
    if (!id) continue;
    var kind = DMG_KIND[String(id).replace(/_(LONG|SHORT)$/, "")];
    if (!kind) continue;
    var pct = parseFloat(String(effects["STAT_" + n + "_PARAM_1"]).replace("%", ""));
    if (!isNaN(pct)) out[kind] = (out[kind] || 0) + pct;
  }
  return out;
}

// totals over a weapon's equipped mods, optionally ignoring the slot being replaced
function weaponCtx(weapon, skipSlot) {
  var sums = {};
  var mods = weapon.m_vecMods || [];
  for (var i = 0; i < mods.length; i++) {
    if (i === skipSlot) continue;
    var p = modPcts(mods[i]);
    for (var k in p) sums[k] = (sums[k] || 0) + p[k];
  }
  return { base: weapon.m_iDamage, pellets: BASE_PELLETS[weapon.m_strName] || 1, sums: sums };
}

// One shot: damage mods are percentages that add up and scale the base; pellet mods add pellets that
// each deal the same damage as the others (assumption: the game data doesn't say how a pellet mod
// interacts with damage).
function shot(ctx, dmgPct, extraPellets) {
  var total0 = ctx.base * (1 + dmgPct / 100);
  var each = total0 / ctx.pellets;
  var n = ctx.pellets + (extraPellets || 0);
  return { total: each * n, each: each, n: n };
}

function plainShot(ctx) {
  return shot(ctx, ctx.sums.base || 0, ctx.sums.pellets || 0);
}

function plainDamage(ctx) {
  return plainShot(ctx).total;
}

// what equipping `item` in the slot being edited would give; delta is vs. what is equipped now
function candidate(item, ctx, now) {
  var p = modPcts(item);
  var s = ctx.sums;
  var nowShot = plainShot(now);
  if (p.base !== undefined || p.pellets !== undefined) {
    var sh = shot(ctx, (s.base || 0) + (p.base || 0), (s.pellets || 0) + (p.pellets || 0));
    return {
      kind: p.base !== undefined ? "base" : "pellets",
      num: sh.total,
      delta: sh.total - nowShot.total,
      n: sh.n,
      each: sh.each,
    };
  }
  for (var i = 0; i < NUMBER_KINDS.length; i++) {
    var k = NUMBER_KINDS[i];
    if (p[k] === undefined) continue;
    var cond = shot(ctx, (s.base || 0) + (s[k] || 0) + p[k], s.pellets || 0);
    var was = shot(now, (now.sums.base || 0) + (now.sums[k] || 0), now.sums.pellets || 0);
    return { kind: k, num: cond.total, delta: cond.total - was.total, n: cond.n, each: cond.each };
  }
  for (var j = 0; j < KIND_ORDER.length; j++) {
    var m = KIND_ORDER[j];
    if (p[m] !== undefined) return { kind: m, multiplier: mult((s[m] || 0) + p[m]) };
  }
  return null;
}

function damageOf(item, gearMenu) {
  var w = currentWeapon(gearMenu);
  if (!w || item.m_eType !== gameTypes.ItemType.WEAPON_MOD) return null;
  var slot = gearMenu.currentModSlot;
  return candidate(item, weaponCtx(w, slot), weaponCtx(w, -1));
}

function compare(a, b, key, dir, isPlayer, gearMenu) {
  var ia = info(a, isPlayer);
  var ib = info(b, isPlayer);
  var r = 0;
  if (key === "damage") {
    var da = damageOf(a, gearMenu);
    var db = damageOf(b, gearMenu);
    var xa = da && da.num !== undefined ? da.num : -Infinity;
    var xb = db && db.num !== undefined ? db.num : -Infinity;
    r = xa === xb ? 0 : xa < xb ? -1 : 1;
  } else if (key === "tier") r = ia.tier - ib.tier;
  else if (key === "value") {
    var na = isNaN(ia.valueNum) ? -Infinity : ia.valueNum;
    var nb = isNaN(ib.valueNum) ? -Infinity : ib.valueNum;
    r = na === nb ? 0 : na < nb ? -1 : 1;
  } else if (key === "weapon") r = ia.weaponKey < ib.weaponKey ? -1 : ia.weaponKey > ib.weaponKey ? 1 : 0;
  else if (key === "type") r = ia.category < ib.category ? -1 : ia.category > ib.category ? 1 : 0;
  else if (key === "effect") r = ia.effectKey < ib.effectKey ? -1 : ia.effectKey > ib.effectKey ? 1 : 0;
  else if (key === "name") r = ia.nameKey < ib.nameKey ? -1 : ia.nameKey > ib.nameKey ? 1 : 0;
  if (dir === "desc") r = -r;
  if (r !== 0) return r;
  // tie-breakers keep the order stable and meaningful
  if (key !== "name" && ia.nameKey !== ib.nameKey) return ia.nameKey < ib.nameKey ? -1 : 1;
  if (ia.tier !== ib.tier) return ib.tier - ia.tier;
  return 0;
}

function apply(list, equipmentType, gearMenu) {
  var kind = kindOf(equipmentType);
  var isPlayer = kind === "player";
  var f = state[kind];
  var tiers = f.tiers.slice();
  var out = list.filter(function (it) {
    if (!it || it.m_eType === gameTypes.ItemType.NONE) return false;
    var inf = info(it, isPlayer);
    if (tiers.length && tiers.indexOf(inf.tier) === -1) return false;
    if (f.type && inf.category !== f.type) return false;
    if (!isPlayer && f.fits && blocked(it, gearMenu)) return false;
    return true;
  });
  if (f.sortKey !== "new") {
    var key = f.sortKey;
    var dir = f.sortDir;
    out.sort(function (a, b) {
      return compare(a, b, key, dir, isPlayer, gearMenu);
    });
  }
  return out;
}

// ---------- state mutators ----------

function click() {
  try {
    sound.playSound(sound.MENU_SOUNDS.TabChanged);
  } catch (e) {}
}

var setSort = mobx.action(function (kind, key) {
  var f = state[kind];
  if (f.sortKey === key) f.sortDir = f.sortDir === "asc" ? "desc" : "asc";
  else {
    f.sortKey = key;
    f.sortDir = DEFAULT_DIR[key] || "asc";
  }
  click();
});

var cycleSort = mobx.action(function (kind) {
  var f = state[kind];
  var at = -1;
  for (var i = 0; i < SORT_CYCLE.length; i++) {
    if (SORT_CYCLE[i].key === f.sortKey && SORT_CYCLE[i].dir === f.sortDir) at = i;
  }
  var next = SORT_CYCLE[(at + 1) % SORT_CYCLE.length];
  f.sortKey = next.key;
  f.sortDir = next.dir;
  click();
});

var toggleTier = mobx.action(function (kind, tier) {
  var tiers = state[kind].tiers;
  var at = tiers.indexOf(tier);
  if (at === -1) tiers.push(tier);
  else tiers.splice(at, 1);
  click();
});

var setType = mobx.action(function (kind, type) {
  state[kind].type = state[kind].type === type ? "" : type;
  click();
});

var toggleFits = mobx.action(function () {
  state.weapon.fits = !state.weapon.fits;
  click();
});

var clearFilters = mobx.action(function (kind) {
  state[kind].tiers.clear ? state[kind].tiers.clear() : state[kind].tiers.splice(0, state[kind].tiers.length);
  state[kind].type = "";
  if (kind === "weapon") state.weapon.fits = false;
  click();
});

// ---------- rendering ----------

function fail(err) {
  module.exports.lastError = String(err && err.stack ? err.stack : err).slice(0, 1500);
  try {
    console.error("[ModTable] disabled after error:", err && err.stack ? err.stack : err);
  } catch (e) {}
  mobx.runInAction(function () {
    state.enabled = false;
  });
  document.body.classList.remove("mt-on");
}

function row(tile, React, Tile) {
  var h = React.createElement;
  var item = tile.props.item;
  var gearMenu = tile.props.gearMenu;
  var isPlayer = tile.props.type === types.UIItemType.PLAYER_MOD;
  var inf = info(item, isPlayer);
  var cant = !isPlayer && blocked(item, gearMenu);
  var focused = tile.link.focused;
  var tierClass = TIER_CLASS[inf.tier] || "common";

  var onWeapon = "";
  if (!isPlayer) {
    var ws = gearMenu.inventoryWeapons;
    for (var i = 0; i < ws.length && !onWeapon; i++) {
      var mods = ws[i].m_vecMods || [];
      for (var j = 0; j < mods.length; j++) {
        if (mods[j] && mods[j].m_uID === item.m_uID) {
          onWeapon = plain(tr(ws[i].m_strName));
          break;
        }
      }
    }
  }

  var labels = [];
  var values = [];
  for (var s = 0; s < inf.stats.length; s++) {
    labels.push(inf.stats[s].label);
    if (inf.stats[s].value) values.push(inf.stats[s].value);
  }

  var made = {
    icon: h("div", { key: "icon", className: "mt-cell mt-cell--icon" }, iconCell(h, item)),
    name: h(
      "div",
      { key: "name", className: "mt-cell mt-cell--name" },
      h("span", { className: "mt-text" }, inf.name),
      item.m_bUnique ? h("span", { className: "mt-tag mt-tag--unique" }, "Unique") : null,
      onWeapon ? h("span", { className: "mt-tag mt-tag--on" }, "On " + onWeapon) : null
    ),
    weapon: h(
      "div",
      { key: "weapon", className: "mt-cell mt-cell--weapon" + (cant ? " mt-cell--bad" : "") },
      h("span", { className: "mt-text" }, inf.weapons.length ? inf.weapons.join(", ") : "Any")
    ),
    type: h(
      "div",
      { key: "type", className: "mt-cell mt-cell--type" },
      h("span", { className: "mt-text" }, inf.category)
    ),
    effect: h(
      "div",
      { key: "effect", className: "mt-cell mt-cell--effect" },
      h("span", { className: "mt-text" }, labels.join(" / "))
    ),
    value: h(
      "div",
      { key: "value", className: "mt-cell mt-cell--value" },
      h("span", { className: "mt-text mt-value" }, values.join(" / "))
    ),
    damage: h("div", { key: "damage", className: "mt-cell mt-cell--damage" }, damageCell(h, item, gearMenu)),
    tier: h(
      "div",
      { key: "tier", className: "mt-cell mt-cell--tier" },
      h(
        "span",
        { className: "mt-tier mt-tier--" + tierClass, title: inf.tierText },
        h("span", { className: "mt-tier__num" }, ROMAN[inf.tier] || "?"),
        h("span", { className: "mt-tier__text" }, inf.tierText)
      )
    ),
  };
  var cols = columnsFor(isPlayer ? "player" : "weapon", gearMenu);
  var cells = [];
  for (var c = 0; c < cols.length; c++) cells.push(made[cols[c][0]]);

  return h(
    "div",
    { className: "mt-row-wrap" + (focused ? " mt-row-wrap--focused" : "") },
    h(
      Tile,
      {
        isSelected: focused,
        onMouseEnter: tile.selectable.onMouseHover,
        className: "mod-row mod-row--" + tierClass + (cant ? " mod-row--blocked" : ""),
        visibilityState: item.m_eVisibilityState,
        autoScroll: !tile.link.wasFocusedOnMouseHover,
        isLocked: false,
        hideActionKey: true,
        onClick: tile.selectable.select,
        isHidden: tile.gearBehaviour.isForceHidden,
        hiddenClass: "tile--force-hidden",
        isDisabled: tile.gearBehaviour.isDisabled,
      },
      cells
    )
  );
}

function sortLabel(kind) {
  var f = state[kind];
  if (f.sortKey === "new") return "Newest";
  var col = COL[f.sortKey];
  return col ? col[1] + (f.sortDir === "asc" ? " ▲" : " ▼") : "";
}

// Small 60px icon (glyph sits in the central 60% of the canvas; CSS crops it). Streamed by the
// game's own image component. Two stock icons have off-centre art and are shown uncropped.
var RAW_ICONS = { MOD_BLIND_FURY: 1, MOD_RANGE: 1 };
function iconCell(h, item) {
  var name = String(item.m_strName || "").replace("LOOT_ITEM_", "").replace("_TITLE", "");
  if (!name) return null;
  return h(Img.BackgroundImage, {
    src: "images/items/small/" + name + "_SMALL.png",
    className: "mt-icon" + (RAW_ICONS[name] ? " mt-icon--raw" : ""),
  });
}

// Damage column: the weapon's damage if this mod went into the slot being edited
function damageCell(h, item, gearMenu) {
  var d = damageOf(item, gearMenu);
  if (!d) return h("span", { className: "mt-dim" }, "—");
  var kids = [];
  if (d.num !== undefined) {
    kids.push(h("span", { key: "n", className: "mt-text mt-dmg" }, fmt(d.num)));
    if (Math.round(d.delta) !== 0) {
      kids.push(
        h(
          "span",
          { key: "d", className: "mt-dmg__delta" + (d.delta < 0 ? " mt-dmg__delta--neg" : "") },
          (d.delta > 0 ? "+" : "−") + fmt(Math.abs(d.delta))
        )
      );
    }
  } else {
    kids.push(h("span", { key: "m", className: "mt-text mt-dmg" }, d.multiplier));
  }
  var tag = d.kind === "base" ? "" : KIND_TAG[d.kind];
  if (d.n > 1 && d.num !== undefined) tag = d.n + "×" + fmt(d.each) + (d.kind === "base" || d.kind === "pellets" ? "" : " " + tag);
  if (tag) kids.push(h("span", { key: "t", className: "mt-dmg__tag" }, tag));
  return kids;
}

// "1,500 -> 1,725 (+15%)" plus multipliers for the conditional bonuses
function weaponLine(h, gearMenu) {
  var w = currentWeapon(gearMenu);
  if (!w) return null;
  var ctx = weaponCtx(w, -1);
  var sh = plainShot(ctx);
  var parts = [h("span", { key: "n", className: "mt-wline__name" }, plain(tr(w.m_strName)))];
  parts.push(h("span", { key: "l", className: "mt-label" }, "Damage"));
  parts.push(h("span", { key: "b", className: "mt-dmg" }, fmt(sh.total)));
  if (sh.n > 1) {
    parts.push(h("span", { key: "pe", className: "mt-dim" }, sh.n + " pellets × " + fmt(sh.each)));
  }
  if (Math.round(sh.total) !== Math.round(ctx.base)) {
    parts.push(h("span", { key: "o", className: "mt-dim" }, "base " + fmt(ctx.base)));
    if (ctx.sums.base) parts.push(h("span", { key: "p", className: "mt-dmg__delta" }, "+" + ctx.sums.base + "%"));
  }
  for (var i = 0; i < KIND_ORDER.length; i++) {
    var k = KIND_ORDER[i];
    if (ctx.sums[k]) {
      parts.push(
        h(
          "span",
          { key: k, className: "mt-wline__cond" },
          KIND_NAME[k] + " ",
          h("span", { className: "mt-dmg__delta" }, mult(ctx.sums[k]))
        )
      );
    }
  }
  return h("div", { className: "mt-bar__line mt-wline" }, parts);
}

// Compact damage readout for weapon tiles (observer so it follows mod changes)
var StatsView = mobxReact.observer(
  class extends React.Component {
    render() {
      var item = this.props.item;
      if (!state.enabled) return null;
      if (!item || item.m_eType === gameTypes.ItemType.NONE || !(item.m_iDamage > 0)) return null;
      var h = React.createElement;
      var ctx = weaponCtx(item, -1);
      var sh = plainShot(ctx);
      var lines = [
        h(
          "div",
          { key: "d", className: "mt-wstats__line" },
          h("span", { className: "mt-wstats__label" }, "Damage"),
          h("span", { className: "mt-wstats__num" }, fmt(sh.total))
        ),
      ];
      if (sh.n > 1) {
        lines.push(
          h("div", { key: "p", className: "mt-wstats__line mt-wstats__sub" }, sh.n + " × " + fmt(sh.each))
        );
      }
      if (Math.round(sh.total) !== Math.round(ctx.base)) {
        lines.push(h("div", { key: "b", className: "mt-wstats__line mt-wstats__sub" }, "base " + fmt(ctx.base)));
      }
      return h("div", { className: "mt-wstats" }, lines);
    }
  }
);

function header(equipmentType, React, active, gearMenu) {
  var h = React.createElement;
  var kind = kindOf(equipmentType);
  var isPlayer = kind === "player";
  var f = state[kind];
  var all = source(equipmentType, gearMenu);

  var tierCount = {};
  var typeCount = {};
  for (var i = 0; i < all.length; i++) {
    var inf = info(all[i], isPlayer);
    tierCount[inf.tier] = (tierCount[inf.tier] || 0) + 1;
    typeCount[inf.category] = (typeCount[inf.category] || 0) + 1;
  }
  var shown = apply(all, equipmentType, gearMenu).length;

  var tierChips = [];
  for (var t = 0; t < 6; t++) {
    if (!tierCount[t]) continue;
    tierChips.push(
      h(
        "div",
        {
          key: "t" + t,
          className: "mt-chip mt-chip--tier mt-chip--" + TIER_CLASS[t] + (f.tiers.indexOf(t) > -1 ? " mt-chip--on" : ""),
          onClick: toggleTier.bind(null, kind, t),
        },
        ROMAN[t],
        h("span", { className: "mt-chip__count" }, tierCount[t])
      )
    );
  }

  var typeNames = Object.keys(typeCount).sort();
  var typeChips = [];
  for (var k = 0; k < typeNames.length; k++) {
    var tn = typeNames[k];
    typeChips.push(
      h(
        "div",
        {
          key: "y" + tn,
          className: "mt-chip" + (f.type === tn ? " mt-chip--on" : ""),
          onClick: setType.bind(null, kind, tn),
        },
        tn,
        h("span", { className: "mt-chip__count" }, typeCount[tn])
      )
    );
  }

  var weaponName = !isPlayer && gearMenu.currentWeaponName ? plain(tr(gearMenu.currentWeaponName)) : "";
  var fitsChip = isPlayer
    ? null
    : h(
        "div",
        {
          key: "fits",
          className: "mt-chip mt-chip--fits" + (f.fits ? " mt-chip--on" : ""),
          onClick: toggleFits,
        },
        weaponName ? "Fits " + weaponName : "Fits weapon"
      );

  var filtersActive = f.tiers.length > 0 || f.type !== "" || (!isPlayer && f.fits);
  var cols = columnsFor(kind, gearMenu);
  var heads = [];
  for (var c = 0; c < cols.length; c++) {
    if (cols[c][0] === "icon") {
      heads.push(h("div", { key: "icon", className: "mt-head mt-head--icon" }));
      continue;
    }
    var on = f.sortKey === cols[c][0];
    heads.push(
      h(
        "div",
        {
          key: cols[c][0],
          className: "mt-head mt-head--" + cols[c][2] + (on ? " mt-head--on" : ""),
          onClick: setSort.bind(null, kind, cols[c][0]),
        },
        cols[c][1],
        on ? h("span", { className: "mt-head__arrow" }, f.sortDir === "asc" ? "▲" : "▼") : null
      )
    );
  }

  return h(
    "div",
    { className: "mt-bar" },
    isPlayer ? null : weaponLine(h, gearMenu),
    h(
      "div",
      { className: "mt-bar__line" },
      h("span", { className: "mt-label" }, "Tier"),
      tierChips,
      fitsChip,
      h("span", { className: "mt-spacer" }),
      h("span", { className: "mt-count" }, shown + " / " + all.length),
      filtersActive
        ? h("div", { className: "mt-chip mt-chip--clear", onClick: clearFilters.bind(null, kind) }, "Clear")
        : null
    ),
    h(
      "div",
      { className: "mt-bar__line" },
      h("span", { className: "mt-label" }, "Type"),
      typeChips,
      h("span", { className: "mt-spacer" }),
      h(ActionButton, {
        inputEvent: constants.InputEvent.TOGGLE,
        variant: constants.KeyVariant.LIGHT,
        locId: "INVENTORY_MOD_SORT",
        onClick: cycleSort.bind(null, kind),
        alignKeyRight: true,
        disabled: !active,
      }),
      h("span", { className: "mt-sortname" }, sortLabel(kind))
    ),
    h("div", { className: "mt-heads mt-heads--" + kind }, heads),
    shown === 0 ? h("div", { className: "mt-empty" }, "No mods match these filters") : null
  );
}

// ---------- body classes (CSS hooks) ----------

var wired = false;
function wire(gearMenu) {
  if (wired) return;
  wired = true;
  module.exports._gm = gearMenu; // test hook
  mobx.autorun(function () {
    var open = state.enabled && (gearMenu.isAnyWeaponModSectionActive || gearMenu.isPlayerModSectionActive);
    document.body.classList.toggle("mt-open", !!open);
    document.body.classList.toggle("mt-on", !!state.enabled);
  });
}

module.exports = {
  on: function () {
    return state.enabled;
  },
  state: state,
  wire: wire,
  fail: fail,
  row: row,
  weaponStats: function (item) {
    try {
      return React.createElement(StatsView, { item: item });
    } catch (e) {
      fail(e);
      return null;
    }
  },
  header: function (equipmentType, React, active, gearMenu) {
    try {
      wire(gearMenu);
      return header(equipmentType, React, active, gearMenu);
    } catch (e) {
      fail(e);
      return null;
    }
  },
  apply: function (list, equipmentType, gearMenu) {
    wire(gearMenu);
    return apply(list, equipmentType, gearMenu);
  },
  // exposed for the offline test harness
  _info: info,
  _classify: classify,
  _damageOf: damageOf,
  _fmt: fmt,
  _act: function (f) {
    mobx.runInAction(f);
  },
};
