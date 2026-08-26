import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
items = data.get('items', {})
characters = data.get('characters', {})
level_groups = data.get('level_groups', {})
dungeons = data.get('dungeons', {})
lord_boss = data.get('lord_boss', {})
world = data.get('world', {})
bs = data.get('blacksmith', {}).get('craft_dic', {})

print("=== ALL SETS IN GAME / ITEMS WITH SET ATTRIBUTES ===")
# Check all items that have set_name or related naming
set_groups = {}
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    sname = it.get('set_name')
    # Also check id prefix
    parts = i_id.split('_')
    # common prefixes: leather_orc, gold, frozen_warden, ancient_beast_warden, oathbound, dragonscale, frostbinder, etc.
    for prefix in ['leather_orc', 'gold', 'frozen_warden', 'ancient_beast_warden', 'oathbound', 'dragonscale', 'frostbinder', 'expedition', 'moltenflare', 'demon', 'phase_spiral']:
        if prefix in i_id:
            if prefix not in set_groups:
                set_groups[prefix] = []
            set_groups[prefix].append((i_id, it))

for s_name, s_items in set_groups.items():
    print(f"\n--- SET: {s_name} ({len(s_items)} items) ---")
    for i_id, it in s_items:
        slot = it.get('availables') or it.get('slot')
        rarity = it.get('rarity')
        craft = it.get('craft_items', [])
        print(f"   [{slot}] {i_id} | Rarity: {rarity} | Craft: {craft}")

print("\n=== SEARCH ALL ORC / WASTELAND ITEMS IN CRAFT DIC ===")
for cat, sub in bs.items():
    if isinstance(sub, dict):
        for sub_k, item_list in sub.items():
            for i_id in item_list:
                if 'orc' in i_id or 'waste' in i_id or 'bone' in i_id or 'grunt' in i_id:
                    print(f"Craft category {cat} -> {sub_k}: {i_id}")

print("\n=== SEARCH ALL DUNGEON LEVELS & BOSSES & DROPS ===")
for did, ddata in dungeons.items():
    if isinstance(ddata, dict):
        print(f"Dungeon {did}:")
        levels = ddata.get('levels', [])
        for idx, lvl in enumerate(levels):
            print(f"   Lvl {idx+1} ({lvl.get('name')}): enemies={lvl.get('enemies')}, bosses={lvl.get('bosses')}, drops={lvl.get('droppable_items')}")

print("\n=== SEARCH ALL LORD BOSSES ===")
for lid, ldata in lord_boss.items():
    if isinstance(ldata, dict):
        print(f"Lord {lid}: name={ldata.get('name')}, drops={ldata.get('droppable_items')}, rewards={ldata.get('rewards')}")

