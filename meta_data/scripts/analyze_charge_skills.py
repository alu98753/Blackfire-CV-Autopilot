import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
skills = data.get('skills', {})
characters = data.get('characters', {})

charge_skills = {}
for s_id, s_data in skills.items():
    if not isinstance(s_data, dict): continue
    s_name = s_data.get('name') or s_id
    if 'charge' in s_id or 'rush' in s_id or s_data.get('require_move') or s_data.get('move'):
        charge_skills[s_id] = s_data

print(f"Found {len(charge_skills)} charge / move skills:")
for s_id, s_data in charge_skills.items():
    print(f"Skill [{s_id}]: name={s_data.get('name')}, require_move={s_data.get('require_move')}, target_data={s_data.get('target_data')}, cool_round={s_data.get('cool_round')}, effects={s_data.get('effects')}")

# Find monsters with these skills
print("\n=== MONSTERS WITH CHARGE SKILLS ===")
for c_id, c_data in characters.items():
    if not isinstance(c_data, dict): continue
    c_skills = c_data.get('skills', [])
    matched = [s for s in c_skills if s in charge_skills]
    if matched:
        print(f"Monster [{c_id}] ({c_data.get('name')}): skills={matched}")
