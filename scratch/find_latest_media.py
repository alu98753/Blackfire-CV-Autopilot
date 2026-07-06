import os
import glob

brain_dir = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9"
files = glob.glob(os.path.join(brain_dir, "*")) + glob.glob(os.path.join(brain_dir, ".tempmediaStorage", "*"))
files = [f for f in files if os.path.isfile(f) and (f.endswith(".png") or f.endswith(".img") or f.endswith(".webp"))]
files.sort(key=os.path.getmtime, reverse=True)

print("Files sorted by modified time:")
for f in files[:10]:
    print(f, os.path.getmtime(f), os.path.getsize(f))
