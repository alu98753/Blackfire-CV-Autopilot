import os
import time

path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9"
today_start = 1783382400 # 2026-07-07 08:00:00

files_today = []
for root, dirs, files in os.walk(path):
    for f in files:
        fp = os.path.join(root, f)
        mtime = os.path.getmtime(fp)
        if mtime >= today_start:
            files_today.append((fp, mtime, os.path.getsize(fp)))

files_today = sorted(files_today, key=lambda x: x[1], reverse=True)

print("Files modified today:")
for fp, mtime, sz in files_today:
    rel = os.path.relpath(fp, path)
    print(f" - {rel}: size={sz}, time={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
