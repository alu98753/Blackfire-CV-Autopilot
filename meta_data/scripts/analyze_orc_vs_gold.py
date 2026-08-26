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

# Let's inspect where orc designs and gold designs drop
target_designs = [
    # Orc Set
    'design_head_leather_orc', 'design_chest_leather_orc', 'design_hands_leather_orc', 'design_waist_leather_orc', 'design_feet_leather_orc', 'design_necklace_leather_orc',
    # Gold Set
    'design_head_gold', 'design_chest_gold', 'design_hands_gold', 'design_waist_gold', 'design_feet_gold', 'design_shield_gold', 'design_spear_gold'
]

print("=== DETAILED DROP LOCATIONS FOR ORC & GOLD DESIGNS ===")
for did in target_designs:
    sources = []
    # 1. Characters
    for cid, cdata in characters.items():
        if not isinstance(cdata, dict): continue
        drops = cdata.get('droppable_items', []) or cdata.get('drops', [])
        for d in drops:
            item_id = d.get('id') if isinstance(d, dict) else d
            if item_id == did:
                sources.append(('character', cid, cdata.get('name')))

    # 2. Level groups
    for gid, gdata in level_groups.items():
        if not isinstance(gdata, dict): continue
        levels = gdata.get('levels', [])
        for l_idx, lvl in enumerate(levels):
            # check enemies / bosses
            lvl_id = lvl.get('level_id', l_idx + 1)
            enemies = lvl.get('enemies', [])
            bosses = lvl.get('bosses', [])
            for src_type, cid, cname in list(sources):
                if cid in bosses:
                    sources.append(('level_group_boss', gid, f"Level {lvl_id} Boss: {cid} ({cname})"))
                elif cid in enemies:
                    sources.append(('level_group_enemy', gid, f"Level {lvl_id} Enemy: {cid} ({cname})"))

    # 3. Dungeons
    for did_k, ddata in dungeons.items():
        if not isinstance(ddata, dict): continue
        for l_idx, lvl in enumerate(ddata.get('levels', [])):
            for src_type, cid, cname in list(sources):
                if cid in lvl.get('bosses', []):
                    sources.append(('dungeon_boss', did_k, f"Level {l_idx+1} Boss: {cid} ({cname})"))
                elif cid in lvl.get('enemies', []):
                    sources.append(('dungeon_enemy', did_k, f"Level {l_idx+1} Enemy: {cid} ({cname})"))

    # 4. Lord boss
    for lid, ldata in lord_boss.items():
        if not isinstance(ldata, dict): continue
        for src_type, cid, cname in list(sources):
            if cid == lid or cid in ldata.get('bosses', []) or cid in ldata.get('enemies', []):
                sources.append(('lord_boss', lid, f"Lord: {lid} ({ldata.get('name')})"))

    # 5. World
    if did in world.get('expedition_exchange_dic', {}):
        sources.append(('world_shop', 'expedition_shop', f"Cost: {world['expedition_exchange_dic'][did]}"))

    print(f"\n[{did}] -> {items.get(did, {}).get('name', did)}:")
    for s in sources:
        print(f"   - Type: {s[0]} | Target: {s[1]} | Detail: {s[2]}")

print("\n=== CHECK LEATHER_ORC MATERIAL & REFINED INGOT & GOLD INGOT ===")
print("leather_orc recipe:", items.get('leather_orc', {}).get('processing_items'))
print("ingot_gold recipe:", items.get('ingot_gold', {}).get('processing_items'))
