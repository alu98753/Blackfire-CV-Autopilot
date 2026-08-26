import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
items = data.get('items', {})
characters = data.get('characters', {})
level_groups = data.get('level_groups', {})
races = data.get('races', {})

# Rarity chances lookup
# 0.0 -> 100.0%, 1.0 -> 40.0%, 2.0 -> 20.0%, 3.0 -> 10.0%, 4.0 -> 5.0%
def get_rarity_chance(rarity):
    if rarity is None or rarity == 0.0: return 1.0
    if rarity == 1.0: return 0.40
    if rarity == 2.0: return 0.20
    if rarity == 3.0: return 0.10
    if rarity == 4.0: return 0.05
    return 1.0

# All leather materials in tree
leather_tree = {
    'heavy': {
        'leather_heavy': items.get('leather_heavy', {})
    },
    'medium': {
        'giant_hide': items.get('giant_hide', {}),
        'thick_bear_hide': items.get('thick_bear_hide', {}),
        'snake_hide': items.get('snake_hide', {}),
        'ice_fur': items.get('ice_fur', {}),
        'behemoth_hide': items.get('behemoth_hide', {}),
        'leather_medium': items.get('leather_medium', {})
    },
    'light': {
        'leopard_hide': items.get('leopard_hide', {}),
        'petrified_scale': items.get('petrified_scale', {}),
        'leather_light': items.get('leather_light', {})
    },
    'base': {
        'wolf_pelt': items.get('wolf_pelt', {}),
        'boar_hide': items.get('boar_hide', {}),
        'frog_skin': items.get('frog_skin', {}),
        'tough_lizard_hide': items.get('tough_lizard_hide', {}),
        'sandworm_scale': items.get('sandworm_scale', {}),
        'bat_wing': items.get('bat_wing', {})
    }
}

print("=== LEATHER SYNTHESIS TREE EQUIVALENCES ===")
print("1 x 重皮革 (leather_heavy) = ")
print("  - 4 x 中皮革 (leather_medium) = 16 x 輕皮革 (leather_light)")
print("  - 2 x 巨人皮 (giant_hide) [2星藍]")
print("  - 2 x 厚熊皮 (thick_bear_hide) [2星藍]")
print("  - 2 x 蛇皮 (snake_hide) [2星藍]")
print("  - 2 x 冰原毛皮 (ice_fur) [2星藍]")
print("  - 1 x 巨獸皮 (behemoth_hide) [3星紫]")

print("\n1 x 中皮革 (leather_medium) = ")
print("  - 4 x 輕皮革 (leather_light)")
print("  - 2 x 花豹皮 (leopard_hide) [1星綠]")
print("  - 2 x 石化鱗片 (petrified_scale) [1星綠]")

print("\n1 x 輕皮革 (leather_light) = ")
print("  - 2 x 狼皮 (wolf_pelt) [0星白]")
print("  - 2 x 野豬皮 (boar_hide) [0星白]")
print("  - 2 x 蛙皮 (frog_skin) [0星白]")
print("  - 2 x 堅韌蜥蜴皮 (tough_lizard_hide) [0星白]")
print("  - 2 x 沙蟲鱗片 (sandworm_scale) [0星白]")
print("  - 4 x 蝙蝠翅膀 (bat_wing) [0星白]")

# Find monster drop channels for all materials
target_item_ids = [
    'giant_hide', 'thick_bear_hide', 'snake_hide', 'ice_fur', 'behemoth_hide',
    'leopard_hide', 'petrified_scale',
    'wolf_pelt', 'boar_hide', 'frog_skin', 'tough_lizard_hide', 'sandworm_scale', 'bat_wing'
]

monster_drops_map = {}
for cid, cdata in characters.items():
    if not isinstance(cdata, dict): continue
    c_name = cdata.get('name') or cid
    c_race = cdata.get('race')
    droppable = cdata.get('droppable_items', []) or cdata.get('drops', [])
    
    drops_found = []
    for d in droppable:
        did = d.get('id') if isinstance(d, dict) else d
        if did in target_item_ids:
            drops_found.append((did, 'droppable', d))
            
    if c_race and c_race in races:
        for r_item in races[c_race].get('items', []):
            rid = r_item.get('id') if isinstance(r_item, dict) else r_item
            if rid in target_item_ids:
                drops_found.append((rid, f'race:{c_race}', r_item))
                
    if drops_found:
        monster_drops_map[cid] = {
            'name': c_name,
            'race': c_race,
            'guaranteed': cdata.get('guaranteed'),
            'drops': drops_found
        }

print("\n=== MONSTER DROPS FOR LEATHER MATERIALS ===")
for cid, minfo in monster_drops_map.items():
    print(f"Monster [{cid}] ({minfo['name']}) race={minfo['race']}, guaranteed={minfo['guaranteed']}:")
    for item_id, drop_type, d_meta in minfo['drops']:
        it_meta = items.get(item_id, {})
        rarity = it_meta.get('rarity')
        chance = get_rarity_chance(rarity)
        print(f"   -> [{item_id}] (Rarity {rarity}, Chance {chance*100:.1f}%) via {drop_type}")

# Map stage / level groups details
print("\n=== STAGE FARMING MAPS & MONSTER DENSITY ===")
stage_details = []
for gid, gdata in level_groups.items():
    if not isinstance(gdata, dict): continue
    gname = gdata.get('name') or gid
    levels = gdata.get('levels', [])
    for idx, lvl in enumerate(levels):
        lvl_num = lvl.get('level_id', idx+1)
        enemies = lvl.get('enemies', [])
        bosses = lvl.get('bosses', [])
        
        # count occurrences of leather dropping monsters
        enemy_counts = {}
        for e in enemies:
            if e in monster_drops_map:
                enemy_counts[e] = enemy_counts.get(e, 0) + 1
        boss_counts = {}
        for b in bosses:
            if b in monster_drops_map:
                boss_counts[b] = boss_counts.get(b, 0) + 1
                
        if enemy_counts or boss_counts:
            print(f"Stage [{gid}] (Level {lvl_num}): Enemies={enemy_counts}, Bosses={boss_counts}")
