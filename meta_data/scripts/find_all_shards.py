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

print("=== ALL ENHANCEMENT STONES / SHARDS BY CATEGORY ===")
shards = {}
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    cats = it.get('categories', [])
    if 'enhancement_stone' in cats:
        sort_id = it.get('sort_id', 'unknown')
        if sort_id not in shards:
            shards[sort_id] = []
        shards[sort_id].append((i_id, it))

for s_id, s_list in shards.items():
    print(f"\nShard Category: {s_id}")
    for i_id, it in s_list:
        print(f"   [{i_id}] rarity={it.get('rarity')}, craft={it.get('craft_items')}")

# Now let us check how equipment dismantling produces shards!
# In Godot / game logic, when equipment is dismantled:
# - What determines the shard type? (weapon -> weapon_shard, armor -> armor_shard, jewelry -> jewelry_shard?)
# - What determines the shard tier / rarity? (Equipment Rarity / Tier?)
# Let's inspect scripts, global config, or tres for dismantle formula / rules.
