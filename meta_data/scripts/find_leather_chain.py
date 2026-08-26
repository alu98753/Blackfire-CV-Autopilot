import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
items = data.get('items', {})
bs = data.get('blacksmith', {})
bs_proc = bs.get('processing_dic', {})
bs_craft = bs.get('craft_dic', {})
characters = data.get('characters', {})
level_groups = data.get('level_groups', {})
races = data.get('races', {})

print("=== ALL PROCESSING ITEMS CONTAINING LEATHER / HIDE / SKIN ===")
for item_id, proc_data in bs_proc.items():
    if 'leather' in item_id or 'hide' in item_id or 'skin' in item_id or 'beast' in item_id:
        print(f"BS Proc: {item_id} -> {proc_data}")

print("\n=== ALL ITEMS CONTAINING LEATHER / HIDE / SKIN ===")
for item_id, it in items.items():
    if not isinstance(it, dict): continue
    name = it.get('name', item_id)
    if any(k in item_id for k in ['leather', 'hide', 'skin', 'beast', 'pelt', 'fur', 'orc']):
        print(f"Item: [{item_id}] name={name}, rarity={it.get('rarity')}, proc_items={it.get('processing_items')}, craft_items={it.get('craft_items')}")

print("\n=== SEARCH ALL MONSTERS DROPPING LEATHER / HIDE / SKIN ITEMS ===")
leather_item_ids = [
    'leather_heavy', 'leather_medium', 'leather_rough', 
    'leather_orc', 'beast_hide', 'beast_pelt', 'beast_skin',
    'giant_hide', 'thick_bear_hide', 'tough_lizard_hide', 'lizard_skin', 'frog_skin'
]

monster_drops = {}
for cid, cdata in characters.items():
    if not isinstance(cdata, dict): continue
    c_name = cdata.get('name', cid)
    c_race = cdata.get('race')
    droppable = cdata.get('droppable_items', []) or cdata.get('drops', [])
    equipments = cdata.get('equipments', {})
    
    # Check droppable
    dropped_here = []
    for d in droppable:
        did = d.get('id') if isinstance(d, dict) else d
        if did in leather_item_ids or 'leather' in str(did) or 'hide' in str(did) or 'skin' in str(did) or 'pelt' in str(did):
            dropped_here.append((did, 'droppable', d))
            
    # Check race items
    if c_race and c_race in races:
        r_items = races[c_race].get('items', [])
        for r_item in r_items:
            rid = r_item.get('id') if isinstance(r_item, dict) else r_item
            if rid in leather_item_ids or 'leather' in str(rid) or 'hide' in str(rid) or 'skin' in str(rid) or 'pelt' in str(rid):
                dropped_here.append((rid, f'race:{c_race}', r_item))
                
    if dropped_here:
        monster_drops[cid] = {
            'name': c_name,
            'race': c_race,
            'guaranteed': cdata.get('guaranteed'),
            'drops': dropped_here
        }

for cid, info in monster_drops.items():
    print(f"\nMonster [{cid}] ({info['name']}) race={info['race']}, guaranteed={info['guaranteed']}:")
    for item_id, source_type, d_meta in info['drops']:
        it_meta = items.get(item_id, {})
        rarity = it_meta.get('rarity')
        print(f"   -> Drop [{item_id}] (Rarity {rarity}) via {source_type}")

print("\n=== SEARCH STAGES / LEVEL GROUPS FOR THESE MONSTERS ===")
for gid, gdata in level_groups.items():
    if not isinstance(gdata, dict): continue
    levels = gdata.get('levels', [])
    for idx, lvl in enumerate(levels):
        enemies = lvl.get('enemies', [])
        bosses = lvl.get('bosses', [])
        found_enemies = [e for e in enemies if e in monster_drops]
        found_bosses = [b for b in bosses if b in monster_drops]
        if found_enemies or found_bosses:
            print(f"Map [{gid}] Lvl {lvl.get('level_id', idx+1)}: Enemies={found_enemies}, Bosses={found_bosses}")
