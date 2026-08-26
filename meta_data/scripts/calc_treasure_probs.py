import sys
import os
sys.path.append('.')
from meta_data.tres_parser import TresParser
import json

parser = TresParser()
data = parser.parse()

rarity_chances = data.get('rarity', {}).get('chances', [100.0, 40.0, 20.0, 10.0, 5.0, 2.5, 1.25])
items = data.get('items', {})
treasures = data['domains']['golden_empire']['treasures']

pool_items = []
total_weight = 0.0

for t in treasures:
    item_info = items.get(t, {})
    r = int(item_info.get('rarity', 0))
    weight = rarity_chances[r]
    total_weight += weight
    pool_items.append({
        'id': t,
        'rarity': item_info.get('rarity'),
        'weight': weight,
        'cats': item_info.get('categories')
    })

print(f"Total Weight: {total_weight}")
print("\n| 物品 ID | 稀有度 | 權重 (Weight) | 單抽機率 (Single %) | 10連抽至少中1個機率 (10-Draw %) | 10連期望獲得數 |")
print("| :--- | :---: | :---: | :---: | :---: | :---: |")

for item in pool_items:
    p = item['weight'] / total_weight
    p_10 = 1.0 - (1.0 - p) ** 10
    exp_10 = p * 10
    print(f"| `{item['id']}` | Rarity {item['rarity']} | {item['weight']} | **{p*100:.2f}%** | **{p_10*100:.2f}%** | {exp_10:.2f} 個 |")
