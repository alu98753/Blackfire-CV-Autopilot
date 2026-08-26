import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
characters = data.get('characters', {})
level_groups = data.get('level_groups', {})
dungeons = data.get('dungeons', {})
lord_boss = data.get('lord_boss', {})
world = data.get('world', {})

target_mobs = [
    'orc_harugor', 'orc_kraghul', 'orc_grumor', 'orc_gorsak',
    'undead_altalim', 'voidborn_golden_behemoth', 'voidborn_goldwall_guardian',
    'human_golden_tulakh', 'elf_mythril_hag', 'voidborn_gold_chest', 'voidborn_coin'
]

print("=== MONSTER LOCATIONS IN WORLD / DUNGEONS / MAPS / LORD ===")
for mob_id in target_mobs:
    locs = []
    # 1. level groups
    for gid, gdata in level_groups.items():
        if isinstance(gdata, dict):
            for idx, lvl in enumerate(gdata.get('levels', [])):
                if mob_id in lvl.get('enemies', []):
                    locs.append(f"Map {gid} Lv.{lvl.get('level_id', idx+1)} (Enemy)")
                if mob_id in lvl.get('bosses', []):
                    locs.append(f"Map {gid} Lv.{lvl.get('level_id', idx+1)} (Boss)")

    # 2. dungeons
    for did, ddata in dungeons.items():
        if isinstance(ddata, dict):
            for idx, lvl in enumerate(ddata.get('levels', [])):
                if mob_id in lvl.get('enemies', []):
                    locs.append(f"Dungeon {did} Floor {idx+1} (Enemy)")
                if mob_id in lvl.get('bosses', []):
                    locs.append(f"Dungeon {did} Floor {idx+1} (Boss)")

    # 3. lord boss
    for lid, ldata in lord_boss.items():
        if isinstance(ldata, dict):
            if mob_id == lid or mob_id in ldata.get('bosses', []) or mob_id in ldata.get('enemies', []):
                locs.append(f"Lord Boss: {lid}")

    # 4. world
    if mob_id in world.get('world_enemies', []):
        locs.append("World Map Roaming / Event Enemy")

    print(f"[{mob_id}] -> {locs if locs else 'Not directly in maps (Special spawn/Shop)'}")

