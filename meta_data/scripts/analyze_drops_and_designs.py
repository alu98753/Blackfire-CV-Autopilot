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
alchemy = data.get('alchemy_hut', {})
bs = data.get('blacksmith', {})

print("=== CHECK ALL DESIGN DROPS / SOURCES ===")
# Find all places where design_... items drop or are sold
design_sources = {}
for cid, cdata in characters.items():
    if not isinstance(cdata, dict): continue
    drops = cdata.get('droppable_items', []) or cdata.get('drops', [])
    for d in drops:
        did = d.get('id') if isinstance(d, dict) else d
        if 'design' in str(did) or 'gold' in str(did) or 'shield' in str(did) or 'spear' in str(did) or 'warden' in str(did) or 'knight' in str(did):
            if did not in design_sources:
                design_sources[did] = []
            design_sources[did].append(f"Character: {cid} ({cdata.get('name')})")

# Check level groups drops
for gid, gdata in level_groups.items():
    if not isinstance(gdata, dict): continue
    for lvl in gdata.get('levels', []):
        drops = lvl.get('droppable_items', []) or lvl.get('rewards', [])
        for d in drops:
            did = d.get('id') if isinstance(d, dict) else d
            if 'design' in str(did) or 'gold' in str(did) or 'shield' in str(did) or 'spear' in str(did):
                if did not in design_sources:
                    design_sources[did] = []
                design_sources[did].append(f"Map {gid} level {lvl.get('level_id')}")

# Check lord boss
for lid, ldata in lord_boss.items():
    if not isinstance(ldata, dict): continue
    drops = ldata.get('droppable_items', []) or ldata.get('drops', []) or ldata.get('rewards', [])
    for d in drops:
        did = d.get('id') if isinstance(d, dict) else d
        if did not in design_sources:
            design_sources[did] = []
        design_sources[did].append(f"Lord Boss: {lid} ({ldata.get('name')})")

for k, v in sorted(design_sources.items()):
    print(f"[{k}]:")
    for s in v[:5]:
        print(f"   - {s}")

print("\n=== CHECK GOLD INGOT & GOLD DESIGNS IN WORLD ===")
for k in world.keys():
    print(f"world.{k}: {world[k]}")

print("\n=== CHECK DUNGEONS ===")
for did, ddata in dungeons.items():
    if isinstance(ddata, dict):
        print(f"Dungeon {did}: name={ddata.get('name')}, levels={len(ddata.get('levels', []))}")
        for l in ddata.get('levels', []):
            print(f"   Dungeon level: {l.get('name')} | bosses={l.get('bosses')} | drops={l.get('droppable_items')}")

print("\n=== CHECK FORGOTTEN WASTELAND (Level Group 7) ===")
for gid, gdata in level_groups.items():
    if 'waste' in gid or 'orc' in gid or '7' in gid or 'forgotten' in gid:
        print(f"Map {gid}: name={gdata.get('name')}, req_power={gdata.get('required_power')}, levels={len(gdata.get('levels', []))}")
        for lvl in gdata.get('levels', []):
            enemies = lvl.get('enemies', [])
            bosses = lvl.get('bosses', [])
            drops = lvl.get('droppable_items', [])
            print(f"   Lvl {lvl.get('level_id')}: enemies={enemies}, bosses={bosses}")

