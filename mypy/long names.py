import os

folder = r"C:\Users\RhQNS\Archive\library"

for dirpath, dirnames, filenames in os.walk(folder):
    for f in filenames:
        full = dirpath+os.sep+f
        if len(full) >= 260:
            print(full)
