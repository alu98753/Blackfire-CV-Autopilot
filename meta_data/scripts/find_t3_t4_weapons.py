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

# Find all tier 3 (rarity 3) and tier 4 (rarity 4) weapons
tier3_weapons = []
tier4_weapons = []

for i_id, it in items.items():
    if not isinstance(it, dict): continue
    cats = it.get('categories', [])
    rarity = it.get('rarity')
    # check if weapon
    if 'weapon' in cats:
        if rarity == 3.0:
            tier3_weapons.append((i_id, it))
        elif rarity == 4.0:
            tier4_weapons.append((i_id, it))

print(f"Found {len(tier3_weapons)} Tier 3 (Purple/Epic) Weapons:")
for i_id, it in tier3_weapons:
    craft = it.get('craft_items')
    # find drops
    drops_from = []
    for cid, cdata in characters.items():
        if not isinstance(cdata, dict): continue
        if i_id in [d.get('id') if isinstance(d, dict) else d for d in (cdata.get('droppable_items', []) or cdata.get('drops', []))]:
            drops_from.append(f"{cid} ({cdata.get('name')})")
    print(f"   [{i_id}] Craft: {craft} | Direct Drops: {drops_from}")

print(f"\nFound {len(tier4_weapons)} Tier 4 (Orange/Legendary) Weapons:")
for i_id, it in tier4_weapons:
    craft = it.get('craft_items')
    drops_from = []
    for cid, cdata in characters.items():
        if not isinstance(cdata, dict): continue
        if i_id in [d.get('id') if isinstance(d, dict) else d for d in (cdata.get('droppable_items', []) or cdata.get('drops', []))]:
            drops_from.append(f"{cid} ({cdata.get('name')})")
    print(f"   [{i_id}] Craft: {craft} | Direct Drops: {drops_from}")

