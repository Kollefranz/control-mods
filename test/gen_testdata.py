"""Generate harness/testdata.js: a large, realistic mod inventory for the offline mock UI.

  python -I test/gen_testdata.py <loc_en.json> <out testdata.js>

loc_en.json is the decoded English string table (data/locale/en/string_table.bin).
Names/effects are real game strings; stat values and tiers are pseudo-random but seeded.
"""

import json
import random
import re
import sys

loc = json.load(open(sys.argv[1], encoding="utf-8"))
rnd = random.Random(1234)

# weapon archetype ids (3 upgrade levels each) taken from the game's own mock data
ARCH = {
    "WEAPON_SHOTGUN_SINGLESHOT": [56953316322301, 0x6B04ADDBD01E, 0xF4AAF2EF99B6],
    "WEAPON_SMG_STANDARD": [0x5B9AF3DD0CBC, 0x682F278CA23E, 0xFBD3089B8A5D],
    "WEAPON_RAILGUN_STANDARD": [0xD6D67C0C513A, 0xFB1636405F6, 0xA7DB637073EE],
    "WEAPON_ROCKETLAUNCHER_TRIPLESHOT": [0x75FC76FF656F, 0xA308734F7D5E, 0xE48C3E418F5F],
}

# mod key -> (effect id, weapon family or None)
WEAPON_MODS = {
    "STABILIZER": ("MOD_EFFECT_WEAPON_KICKBACK", "WEAPON_SHOTGUN_SINGLESHOT"),
    "PELLET_SPREAD": ("MOD_EFFECT_WEAPON_PELLET_SCATTER", "WEAPON_SHOTGUN_SINGLESHOT"),
    "PELLET_COUNT": ("MOD_EFFECT_WEAPON_PELLET_COUNT", "WEAPON_SHOTGUN_SINGLESHOT"),
    "GYROSCOPE": ("MOD_EFFECT_WEAPON_ACCURACY", "WEAPON_SMG_STANDARD"),
    "RECEIVER": ("MOD_EFFECT_WEAPON_RATE_OF_FIRE", "WEAPON_SMG_STANDARD"),
    "ZOOM": ("MOD_EFFECT_WEAPON_ZOOM", "WEAPON_RAILGUN_STANDARD"),
    "BOOSTER": ("MOD_EFFECT_WEAPON_BOOST_SPEED", "WEAPON_RAILGUN_STANDARD"),
    "MISSILE_BLAST": ("MOD_EFFECT_WEAPON_BLAST_RADIUS", "WEAPON_ROCKETLAUNCHER_TRIPLESHOT"),
    "MISSILE_VELOCITY": ("MOD_EFFECT_WEAPON_PROJECTILE_SPEED", "WEAPON_ROCKETLAUNCHER_TRIPLESHOT"),
    "ACCURACY": ("MOD_EFFECT_WEAPON_ACCURACY", None),
    "WEAPON_DAMAGE": ("MOD_EFFECT_WEAPON_DAMAGE", None),
    "WEAPON_RELOAD": ("MOD_EFFECT_WEAPON_RELOAD_SPEED", None),
    "WEAPON_ROF": ("MOD_EFFECT_WEAPON_RATE_OF_FIRE", None),
    "WEAPON_AMMO_EFFICIENCY": ("MOD_EFFECT_WEAPON_AMMO_COST", None),
    "WEAPON_ARMOR_DAMAGE": ("MOD_EFFECT_ARMOR_DAMAGE", None),
    "DEADEYE": ("MOD_EFFECT_WEAPON_HEADSHOT_DAMAGE", None),
    "ADRENALINE": ("MOD_EFFECT_WEAPON_LOW_HEALTH_DAMAGE", None),
    "BLOODTHIRST": ("MOD_EFFECT_WEAPON_AFTER_KILL_DAMAGE", None),
    "CONTROLLED_FIRE": ("MOD_EFFECT_WEAPON_AIMED_DAMAGE", "WEAPON_RAILGUN_STANDARD"),
    "DEADLY_RAIN": ("MOD_EFFECT_WEAPON_AIRBORNE_AMMO_COST", None),
    "SUPPRESSIVE_FIRE": ("MOD_EFFECT_WEAPON_AMMO_REFUND_CHANCE", None),
    "DLC2_SHELL_COUNT": ("MOD_EFFECT_WEAPON_DEPLOYED_PROJECTILE_COUNT", "WEAPON_ROCKETLAUNCHER_TRIPLESHOT"),
    "DLC2_PROX_DETONATOR": ("MOD_EFFECT_WEAPON_PROJECTILE_PROXIMITY_DETONATION_RANGE", "WEAPON_ROCKETLAUNCHER_TRIPLESHOT"),
    "SHIELD_RELOAD": ("MOD_EFFECT_WEAPON_SHIELD_ACTIVE_RELOAD_SPEED", None),
}

# personal mods whose effect id is not simply MOD_EFFECT_<KEY>[_SHORT]
PLAYER_EFFECT = {
    "IMPROVED_PHYSIQUE": "MOD_EFFECT_HEALTH_POOL",
    "MENTAL_FORTITUDE": "MOD_EFFECT_RESOURCE_POOL",
    "MENTAL_FOCUS": "MOD_EFFECT_RESOURCE_REGEN",
    "RAPID_RECOVERY": "MOD_EFFECT_HEALTH_REGEN",
    "LAUNCHER": "MOD_EFFECT_LAUNCH_COST",
    "LIGHT_FOOT": "MOD_EFFECT_DODGE_COST",
    "FLEET_FOOT": "MOD_EFFECT_FLEET_FOOT_SHORT",
    "REINFORCED_SHIELD": "MOD_EFFECT_SHIELD_STRENGTH",
    "EFFICIENT_SHIELD": "MOD_EFFECT_SHIELD_COST",
    "COMPELLER": "MOD_EFFECT_COMPEL_RATE",
    "DEATH_FEEDER": "MOD_EFFECT_DEATH_FEEDER_SHORT",
    "LEAF_ON_THE_WIND": "MOD_EFFECT_FALL_DAMAGE",
    "BLIND_FURY": "MOD_EFFECT_MELEE_DAMAGE",
    "ETERNAL_FIRE": "MOD_EFFECT_LAUNCH_DAMAGE",
}

effects = set(k for k in loc if k.startswith("MOD_EFFECT_"))
titles = sorted(k for k in loc if re.match(r"^LOOT_ITEM_MOD_.*_TITLE$", k))
used_loc = set()
uid = [0x100000000000]


def next_id():
    uid[0] += rnd.randint(1000, 99999999)
    return uid[0]


def value_for(effect):
    # reductions for costs/recoil/spread, boosts otherwise
    neg = any(t in effect for t in ("COST", "KICKBACK", "SCATTER", "FALL_DAMAGE", "SPREAD", "FUSE"))
    n = rnd.choice([5, 8, 10, 12, 15, 18, 22, 25, 30, 40, 50])
    return ("-" if neg else "+") + str(n) + "%"


def mk_effects(effect):
    used_loc.add(effect)
    return {"STAT_1_DESC": effect, "STAT_1_PARAM_1": value_for(effect)}


weapon_items, player_items = [], []
for t in titles:
    key = re.sub(r"^LOOT_ITEM_MOD_|_TITLE$", "", t)
    used_loc.add(t)
    if key in WEAPON_MODS:
        eff, fam = WEAPON_MODS[key]
        copies = rnd.choice([1, 2, 3])
        for _ in range(copies):
            it = {
                "m_iPrice": rnd.choice([100, 250, 500, 1000]),
                "m_uSourceID": next_id(),
                "m_eVisibilityState": rnd.choice([10, 11, 11, 12, 12, 12]),
                "m_uID": next_id(),
                "m_eItemRarityType": rnd.choice([0, 1, 1, 2, 2, 3, 4, 5]),
                "m_strName": t,
                "m_vecExclusiveToTargets": ARCH[fam] if fam else [],
                "m_vecExclusiveToTargetLocIDs": [fam] * 3 if fam else [],
                "m_mapModEffects": mk_effects(eff),
                "m_eType": 6,
            }
            if fam:
                used_loc.add(fam)
            if rnd.random() < 0.2:
                it["m_bUnique"] = True
            weapon_items.append(it)
    else:
        eff = PLAYER_EFFECT.get(key)
        if not eff:
            for cand in ("MOD_EFFECT_" + key + "_SHORT", "MOD_EFFECT_" + key):
                if cand in effects:
                    eff = cand
                    break
        if not eff:
            continue
        for _ in range(rnd.choice([1, 1, 2])):
            player_items.append(
                {
                    "m_iPrice": rnd.choice([100, 250, 500]),
                    "m_uSourceID": next_id(),
                    "m_eVisibilityState": rnd.choice([10, 11, 12, 12, 12]),
                    "m_uID": next_id(),
                    "m_eItemRarityType": rnd.choice([0, 1, 1, 2, 2, 3, 4, 5]),
                    "m_strName": t,
                    "m_strDescription": t.replace("_TITLE", "_DESC"),
                    "m_mapModEffects": mk_effects(eff),
                    "m_eType": 4,
                    "m_strImagePath": "",
                }
            )
            used_loc.add(t.replace("_TITLE", "_DESC"))

for k in list(loc):
    if k.startswith("LOOT_ITEM_RARITY_") or k.startswith("WEAPON_") or k in ("INVENTORY_MOD_SORT",):
        used_loc.add(k)

used = {k: loc[k] for k in sorted(used_loc) if k in loc}
js = """(function () {
  var LOC = %s;
  var base = engine.translate; engine.translate = function (k) { return LOC[k] || base(k); };
  g_Loadout.m_vecInventoryWeaponMods = %s;
  g_Loadout.m_vecInventoryRunes = g_Loadout.m_vecInventoryRunes.concat(%s);
  window.__testCounts = { weapon: g_Loadout.m_vecInventoryWeaponMods.length, player: g_Loadout.m_vecInventoryRunes.length };
})();
""" % (json.dumps(used), json.dumps(weapon_items), json.dumps(player_items))
open(sys.argv[2], "w", encoding="utf-8").write(js)
print("weapon mods:", len(weapon_items), "personal mods:", len(player_items), "loc strings:", len(used))
