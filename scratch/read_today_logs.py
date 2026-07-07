import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\.system_generated\logs\transcript.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if "2026-07-07 08:" in line:
            try:
                obj = json.loads(line)
                content = obj.get("content", "")
                # Print only lines containing log messages of interest
                for l in content.split("\n"):
                    if "2026-07-07 08:09:" in l or "2026-07-07 08:10:" in l:
                        print(l)
            except Exception:
                pass
