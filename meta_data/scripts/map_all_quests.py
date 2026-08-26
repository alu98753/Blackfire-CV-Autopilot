import sys
import os
sys.path.append('.')
from meta_data.tres_parser import TresParser
import json

parser = TresParser()
data = parser.parse()
quests = data.get('quests', {})
items = data.get('items', {})

def print_chain(category_name):
    print(f"\n==========================================")
    print(f"=== {category_name.upper()} QUEST CHAIN ===")
    print(f"==========================================")
    
    # Filter quests in this category
    cat_quests = {}
    for qk, qv in quests.items():
        cats = qv.get('categories', [])
        if category_name in cats or category_name in qk:
            cat_quests[qk] = qv
            
    for qk, qv in cat_quests.items():
        req = qv.get('require_id', 'None (Start)')
        print(f"\n[Quest ID]: {qk}")
        print(f"  前置條件 (require_id): {req}")
        print(f"  NPC: {qv.get('entruster')}")
        progs = qv.get('progress', [])
        for idx, p in enumerate(progs):
            targets = p.get('targets', {})
            rewards = p.get('rewards', [])
            print(f"  階段 {idx+1}:")
            print(f"    - 目標: {targets}")
            print(f"    - 獎勵: {rewards}")

print_chain('blacksmith')
print_chain('jewelry')
print_chain('alchemy')
print_chain('tavern')
