import pygetwindow as gw

print("Open window titles:")
for w in gw.getAllTitles():
    if w:
        print(f" - {w}")
