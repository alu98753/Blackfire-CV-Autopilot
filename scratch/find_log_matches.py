import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\.system_generated\logs\transcript.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if "偵測到背包入口按鈕" in line:
            try:
                obj = json.loads(line)
                content = obj.get("content", "")
                if "準備點擊座標" in content or "偵測到背包入口按鈕" in content:
                    # Let's print only if it looks like a real command output, e.g. starts with date
                    lines = content.split("\n")
                    for l in lines:
                        if "偵測到背包入口按鈕" in l or "準備點擊座標" in l or "成功匹配模板 'common/bag.png'" in l:
                            print(l)
            except Exception:
                pass
