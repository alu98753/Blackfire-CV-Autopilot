import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()

items = data.get('items', {})
bs = data.get('blacksmith', {})
craft_dic = bs.get('craft_dic', {})
characters = data.get('characters', {})
level_groups = data.get('level_groups', {})
dungeons = data.get('dungeons', {})
lord_boss = data.get('lord_boss', {})
world = data.get('world', {})
expedition_shop = world.get('expedition_exchange_dic', {})

heavy_slots = ['head', 'chest', 'hands', 'waist', 'feet']
offhands = ['shield']
weapon_types = ['spear', 'hammer', 'axe']

all_knight_crafts = []

for slot in heavy_slots:
    for item_id in craft_dic.get('heavy_armor', {}).get(slot, []):
        it = items.get(item_id, {})
        all_knight_crafts.append((slot, item_id, it))

for slot in offhands:
    for item_id in craft_dic.get('off_hand', {}).get(slot, []):
        it = items.get(item_id, {})
        all_knight_crafts.append((slot, item_id, it))

for w in weapon_types:
    for item_id in craft_dic.get('weapon', {}).get(w, []):
        it = items.get(item_id, {})
        all_knight_crafts.append((w, item_id, it))

all_knight_crafts.sort(key=lambda x: (x[2].get('level', 0), x[2].get('rarity', 0), x[0]))

print(f"Total knight craft items found: {len(all_knight_crafts)}")
for slot, item_id, it in all_knight_crafts:
    lvl = it.get('level', 0)
    rarity = it.get('rarity', 0)
    name = it.get('name', item_id)
    set_name = it.get('set_name', '')
    craft_items = it.get('craft_items', [])
    craft_str = ', '.join([f"{c.get('id')}: x{c.get('count')}" for c in craft_items])
    design_id = it.get('design_id') or it.get('craft_design')
    attrs = it.get('attributes', {})
    skill = it.get('passive_skill') or it.get('skill')
    print(f"[{lvl}級 | R{rarity} | {slot}] {name} ({item_id}) | Set: {set_name} | Attrs: {attrs} | Skill: {skill} | Craft: [{craft_str}]")
