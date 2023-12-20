"""Scan the ora2 directory for directories that need OLD folders and confirm they have them"""
import os
import re

DIRECTORY = "Y:\\"
REGEX = r"^[a-zA-Z]{2,3}$"

subfolders = [f.path for f in os.scandir(DIRECTORY) if f.is_dir()]

for dirname in list(subfolders):
    name = os.path.basename(os.path.normpath(dirname))
    name_match = re.match(REGEX, name)
    if (name_match and not os.path.exists(os.path.join(dirname, "OLD"))):
        print(name)
