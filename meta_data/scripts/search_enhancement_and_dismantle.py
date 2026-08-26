import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()

items = data.get('items', {})
bs = data.get('blacksmith', {})
alchemy = data.get('alchemy_hut', {})
world = data.get('world', {})

print("=== SEARCH ENHANCEMENT STONES / ESSENCES / SHARDS ===")
enhancement_items = {}
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    name = str(it.get('name', ''))
    cats = it.get('categories', [])
    desc = str(it.get('description', ''))
    if 'enhancement' in i_id or 'essence' in i_id or 'reinforce' in i_id or 'stone' in i_id or '強化' in name or '精華' in name:
        enhancement_items[i_id] = it

for k, v in sorted(enhancement_items.items()):
    print(f"[{k}] name={v.get('name')} | cats={v.get('categories')} | rarity={v.get('rarity')} | level={v.get('level')} | meta={v}")

print("\n=== SEARCH DISMANTLE / RECYCLE IN BLACKSMITH / ALCHEMY / WORLD ===")
print("Blacksmith keys:", list(bs.keys()))
for k in bs.keys():
    if 'dismantle' in k or 'recycle' in k or 'decom' in k or 'enhance' in k or 'refine' in k:
        print(f"BS.{k}: {bs[k]}")

print("Alchemy keys:", list(alchemy.keys()))
for k in alchemy.keys():
    if 'dismantle' in k or 'recycle' in k or 'decom' in k:
        print(f"Alc.{k}: {alchemy[k]}")

print("World keys containing dismantle/recycle:")
for k in world.keys():
    if 'dismantle' in k or 'recycle' in k or 'enhance' in k:
        print(f"World.{k}: {world[k]}")
