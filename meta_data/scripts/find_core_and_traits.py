import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
items = data.get('items', {})
demon_lords = data.get('demon_lords', {})
lords = data.get('lords', {})
world = data.get('world', {})
characteristics = data.get('characteristics', {})

print("=== SEARCH KING CORES (王核) IN ITEMS ===")
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    name = str(it.get('name', ''))
    desc = str(it.get('description', ''))
    cats = it.get('categories', [])
    if '王核' in name or '王核' in desc or 'core' in i_id or 'summon' in i_id or 'urde' in i_id or 'root' in i_id or 'boss' in i_id:
        print(f"Item [{i_id}]: name={name}, categories={cats}, use_effect={it.get('use_effect') or it.get('effects') or it}")

print("\n=== SEARCH ALL DEMON LORDS / LORDS ===")
for lid, ldata in demon_lords.items():
    print(f"Demon Lord [{lid}]: {ldata}")

for lid, ldata in lords.items():
    print(f"Lord [{lid}]: {ldata}")

print("\n=== TREANT RACE TRAITS ===")
for ch_id, ch in characteristics.items():
    if 'treant' in ch_id or 'plant' in ch_id or 'nature' in ch_id:
        print(f"Trait [{ch_id}]: {ch}")
