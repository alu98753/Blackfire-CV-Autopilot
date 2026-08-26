import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from meta_data.tres_parser import TresParser
import json

data = TresParser().parse()

def search_text(obj, term, path=""):
    res = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            np = f"{path}.{k}" if path else k
            if term in str(k) or term in str(v):
                res.append((np, str(v)[:200] if not isinstance(v, (dict, list)) else f"Type: {type(v)}"))
            if isinstance(v, (dict, list)):
                res.extend(search_text(v, term, np))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            np = f"{path}[{idx}]"
            if term in str(item):
                res.append((np, str(item)[:200] if not isinstance(item, (dict, list)) else f"Type: {type(item)}"))
            if isinstance(item, (dict, list)):
                res.extend(search_text(item, term, np))
    return res

for term in ['根結王核', '萬根之眼', '厄德', 'root', 'treant', 'eye', 'ede']:
    r = search_text(data, term)
    print(f"\n=== SEARCH TERM: {term} (matches: {len(r)}) ===")
    for p, v in r[:10]:
        print(f"   {p} -> {v}")
