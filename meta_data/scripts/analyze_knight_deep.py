import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
items = data.get('items', {})
skills = data.get('skills', {})
level_groups = data.get('level_groups', {})
dungeons = data.get('dungeons', {})
lord_boss = data.get('lord_boss', {})
world = data.get('world', {})
bs = data.get('blacksmith', {})

print("=== ALL HEAVY ARMOR / SHIELD / SPEAR ITEMS ===")
knight_items = {}
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    itype = it.get('item_type') or it.get('type')
    sub_type = it.get('sub_type') or it.get('equipment_type') or it.get('slot')
    # check if heavy armor or shield or spear
    name = it.get('name', i_id)
    if 'heavy' in str(itype) or 'heavy' in str(sub_type) or sub_type in ['shield', 'spear', 'heavy_armor'] or 'warden' in i_id or 'gold' in i_id or 'knight' in i_id:
        knight_items[i_id] = it

print(f"Found {len(knight_items)} potential knight items.")

# Check recipes, designs, and drop sources
designs = {}
for i_id, it in items.items():
    if not isinstance(it, dict): continue
    if 'design' in i_id or it.get('item_type') == 'design':
        designs[i_id] = it

print(f"Found {len(designs)} designs.")

# Let's inspect all designs relevant to heavy armor / shield / spear / gold
for d_id, d_it in designs.items():
    name = d_it.get('name', d_id)
    unlock_item = d_it.get('unlock_item') or d_it.get('craft_item') or d_it.get('target_item')
    price = d_it.get('price') or d_it.get('cost') or d_it.get('token_cost')
    desc = d_it.get('description', '')
    print(f"Design: {d_id} | Name: {name} | Target: {unlock_item} | Price: {price} | Desc: {desc[:50]}")

print("\n=== GOLD EQUIPMENT SET CHECK ===")
gold_items = ['chest_gold', 'feet_gold', 'hands_gold', 'head_gold', 'shield_gold', 'spear_gold', 'waist_gold']
for gid in gold_items:
    it = items.get(gid, {})
    print(f"Gold item {gid}: {it}")

print("\n=== FROZEN WARDEN SET CHECK ===")
fw_items = ['head_frozen_warden', 'chest_frozen_warden', 'hands_frozen_warden', 'waist_frozen_warden', 'feet_frozen_warden']
for fwid in fw_items:
    it = items.get(fwid, {})
    print(f"Frozen warden {fwid}: {it}")

print("\n=== CHECK SKILLS ON GEAR ===")
gear_skills = ['chilled_bone', 'stripper_ward', 'frostprey_dominance', 'first_strike_instinct', 'frozenguard_oath', 'infernal_pact_echo', 'crystal_spikes', 'oathbound_aegis', 'iron_jaw_lock', 'attack_crystal_thrust', 'barrier_instinct', 'attack_stab_gold']
for sk_id in gear_skills:
    sk = skills.get(sk_id, {})
    print(f"Skill [{sk_id}]: {sk.get('name')} | Desc: {sk.get('description')} | Effects: {sk.get('effects') or sk.get('buffs') or sk}")

print("\n=== EXPEDITION SHOP CHECK ===")
print("Expedition shop items:", world.get('expedition_exchange_dic'))
print("Lord shop items:", world.get('lord_exchange_dic') or world.get('boss_exchange_dic') or world.get('shop_dic'))
print("Golden token shop / Empire shop:", world.get('golden_exchange_dic') or world.get('empire_shop') or world.get('gold_shop'))
