"""Search all files in a directory for a text string"""
import os

rootdir=('Y:\\win98\\CPA_RENEWALS\\safe')
for folder, dirs, files in os.walk(rootdir):
    for file in files:
        if file.endswith('.txt'):
            fullpath = os.path.join(folder, file)
            with open(fullpath, 'r', encoding='utf-8') as f:
                for line in f:
                    if "3674991" in line:
                        print(fullpath)
                        break