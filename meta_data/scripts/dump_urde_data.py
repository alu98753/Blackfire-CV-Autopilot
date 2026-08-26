import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
characters = data.get('characters', {})
items = data.get('items', {})
skills = data.get('skills', {})
characteristics = data.get('characteristics', {})
lord_boss = data.get('lord_boss', {}) or data.get('lords', {})
demon_lords = data.get('demon_lords', {})
world = data.get('world', {})
quests = data.get('quests', {})

print("=== MONSTER: treant_urde ===")
urde = characters.get('treant_urde', {})
print("treant_urde character data:")
print(json.dumps(urde, indent=2, ensure_ascii=False))

print("\n=== SKILLS OF treant_urde ===")
for sk_id in urde.get('skills', []):
    sk = skills.get(sk_id, {})
    print(f"\nSkill [{sk_id}]:")
    print(json.dumps(sk, indent=2, ensure_ascii=False))

print("\n=== CHARACTERISTICS / PASSIVES ===")
for ch_id in urde.get('characteristics', []):
    ch = characteristics.get(ch_id, {})
    print(f"\nCharacteristic [{ch_id}]:")
    print(json.dumps(ch, indent=2, ensure_ascii=False))

print("\n=== ITEMS RELATED TO treant_urde / CORE ===")
for i_id, it in items.items():
    if 'urde' in i_id or 'treant' in i_id or 'core' in i_id:
        if 'urde' in i_id or 'root' in i_id:
            print(f"Item [{i_id}]: {it}")

print("\n=== LORDS / DEMON LORDS / SUMMON DATA ===")
for lid, ldata in {**lord_boss, **demon_lords}.items():
    if 'urde' in lid or 'treant' in lid:
        print(f"Lord [{lid}]: {ldata}")

print("\n=== QUESTS / ACHIEVEMENTS ===")
for qid, qdata in quests.items():
    if 'urde' in qid or 'treant' in qid:
        print(f"Quest [{qid}]: {qdata}")
