import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
level_groups = data.get('level_groups', {})
dungeons = data.get('dungeons', {})
lord_boss = data.get('lord_boss', {})
domains = data.get('domains', {})

print("=== ALL MAIN MAPS PROGRESSION & REQUIRED POWER ===")
maps = []
for k, v in level_groups.items():
    if isinstance(v, dict):
        maps.append((k, v))

ordered_maps = []
cur = 'none'
while True:
    found = False
    for k, v in maps:
        if v.get('pre_level_group') == cur:
            ordered_maps.append((k, v))
            cur = k
            found = True
            break
    if not found:
        break

for k, v in maps:
    if k not in [m[0] for m in ordered_maps]:
        ordered_maps.append((k, v))

for idx, (m_id, m_data) in enumerate(ordered_maps):
    name = m_data.get('name', m_id)
    req_pwr = m_data.get('required_power', 0)
    pre = m_data.get('pre_level_group')
    levels = m_data.get('levels', [])
    min_lvl = levels[0].get('enemy_level') if levels else 'N/A'
    max_lvl = levels[-1].get('enemy_level') if levels else 'N/A'
    print(f"Stage {idx+1}: [{m_id}] (Enemy Lv.{min_lvl}~{max_lvl}) | Required Power: {req_pwr} | Pre: {pre}")

print("\n=== ALL DUNGEONS UNLOCK / POWER LIMITS ===")
for did, ddata in dungeons.items():
    if isinstance(ddata, dict):
        req_pwr = ddata.get('required_power') or ddata.get('require_power')
        req_acc = ddata.get('unlock_account_level') or ddata.get('require_level')
        pre_d = ddata.get('require_dungeon_id') or ddata.get('pre_dungeon')
        print(f"Dungeon: {did} | Required Power: {req_pwr} | Unlock Level: {req_acc} | Pre Dungeon: {pre_d}")

print("\n=== ALL DOMAINS UNLOCK / POWER LIMITS ===")
for did, ddata in domains.items():
    if isinstance(ddata, dict):
        req_pwr = ddata.get('required_power') or ddata.get('require_power')
        print(f"Domain: {did} | Required Power: {req_pwr} | Data: {ddata}")

print("\n=== ALL LORD BOSS UNLOCK / POWER LIMITS ===")
for lid, ldata in lord_boss.items():
    if isinstance(ldata, dict):
        req_pwr = ldata.get('required_power') or ldata.get('require_power')
        req_dun = ldata.get('required_dungeon_id')
        print(f"Lord: {lid} | Required Power: {req_pwr} | Required Dungeon: {req_dun}")
