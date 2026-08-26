import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()

items = data.get('items', {})

print("=== ALL ESSENCES ===")
for i in range(1, 10):
    eid = f"essence_{i}"
    if eid in items:
        print(f"{eid}: {items[eid]}")

print("\n=== ALL ENHANCEMENT / UPGRADE ITEMS ===")
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    cats = it.get('categories', [])
    if 'enhancement' in str(cats) or 'upgrade' in str(cats) or 'essence' in i_id:
        print(f"[{i_id}]: {it}")

print("\n=== SEARCH ALL ITEMS WITH DISMANTLE OPTIONS ===")
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    options = it.get('options', {})
    if 'dismantle' in options or 'recycle' in options or 'decompose' in options:
        print(f"Item [{i_id}] has dismantle: {options}")

# Check global dismantle rules or item settings
for k, v in data.items():
    if 'dismantle' in k or 'recycle' in k or 'decompose' in k or 'enhance' in k or 'forge' in k:
        print(f"Root Key: {k} -> {v if not isinstance(v, dict) else list(v.keys())}")
