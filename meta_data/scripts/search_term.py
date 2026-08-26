import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()

# Search string in all data
def search_in_obj(obj, term, path=""):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if term.lower() in str(k).lower():
                results.append((new_path, "KEY_MATCH"))
            if isinstance(v, (dict, list)):
                results.extend(search_in_obj(v, term, new_path))
            elif term.lower() in str(v).lower():
                results.append((new_path, str(v)[:100]))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            new_path = f"{path}[{idx}]"
            if isinstance(item, (dict, list)):
                results.extend(search_in_obj(item, term, new_path))
            elif term.lower() in str(item).lower():
                results.append((new_path, str(item)[:100]))
    return results

for term in ['kraghul', 'grumor', 'altalim', 'tulakh', 'mythril_hag', 'orc_bunker', 'ancient_tomb']:
    res = search_in_obj(data, term)
    print(f"\n=== SEARCH: {term} (matches: {len(res)}) ===")
    for p, v in res[:6]:
        print(f"   {p} -> {v}")
