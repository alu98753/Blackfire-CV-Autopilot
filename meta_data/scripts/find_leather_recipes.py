import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
bs = data.get('blacksmith', {})
bs_proc = bs.get('processing_dic', {})
items = data.get('items', {})

print("=== LEATHER PROCESSING DIC IN DETAIL ===")
leather_keys = ['leather_heavy', 'leather_medium', 'leather_rough', 'leather_light', 'leather_orc']
for k in leather_keys:
    print(f"BS Proc Key [{k}]:", bs_proc.get(k))

print("\n=== ITEMS PROCESSING DIC IN DETAIL ===")
for k in leather_keys:
    it = items.get(k, {})
    print(f"Item [{k}]: rarity={it.get('rarity')}, proc_items={it.get('processing_items')}, craft_items={it.get('craft_items')}")

# Also search all items in bs_proc for any key containing 'leather' or 'hide' or 'skin' or 'pelt'
print("\n=== ALL BS PROC WITH LEATHER/HIDE/SKIN/PELT ===")
for k, v in bs_proc.items():
    if any(x in k for x in ['leather', 'hide', 'skin', 'pelt', 'fur', 'beast', 'bear', 'wolf', 'leopard', 'lizard', 'frog', 'giant']):
        print(f"[{k}] -> {v}")

# Also search all items in items with processing_items
print("\n=== ALL ITEMS WITH PROCESSING ITEMS INVOLVING LEATHER/HIDE/SKIN ===")
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    proc = it.get('processing_items')
    if proc:
        print(f"Item [{i_id}] processing_items: {proc}")
