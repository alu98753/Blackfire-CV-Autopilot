import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()
bs = data.get('blacksmith', {})
alchemy = data.get('alchemy_hut', {})
items = data.get('items', {})

print("=== BLACKSMITH PROCESSING DIC ===")
bs_proc = bs.get('processing_dic', {})
for k, v in bs_proc.items():
    if 'gold' in k or 'ingot' in k:
        print(f"BS Proc: {k} -> {v}")

print("\n=== ALCHEMY CRAFT / PROCESSING ===")
alc_proc = alchemy.get('processing_dic', {})
for k, v in alc_proc.items():
    if 'gold' in k or 'essence' in k:
        print(f"Alc Proc: {k} -> {v}")

alc_craft = alchemy.get('craft_dic', {})
for k, v in alc_craft.items():
    if 'gold' in k or 'essence' in k:
        print(f"Alc Craft: {k} -> {v}")

print("\n=== CHECK GOLD INGOT ITEM ===")
print("ingot_gold item meta:", items.get('ingot_gold'))
print("gold_fragments item meta:", items.get('gold_fragments'))
print("gold_fragment_small item meta:", items.get('gold_fragment_small'))
