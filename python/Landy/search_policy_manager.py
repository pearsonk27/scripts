"""Recursively search the Policy_Manager directory for a policy number"""

import os
from pathlib import Path
import time

DIRECTORY = "/volumes/pdf_files/Policy_Manager/webdocs"
POLICY_NUMBERS = [
    "3677877",
    "3676838",
    "3675388",
    "3676439",
    "3677672",
    "3674331",
    "3677981",
    "3674893",
    "3675605",
    "3675523",
    "3674652",
    "3675265",
    "3674788",
    "3674680",
    "3674322",
    "3677639",
    "3674462",
    "3674371",
    "3676183",
    "3675312",
    "3675147",
    "3674228",
    "3675241",
    "3675066",
    "3674493",
]

#for path in Path(DIRECTORY).rglob(f"*{POLICY_NUMBERS[11]}*"):
for key in POLICY_NUMBERS:
    for path in Path(DIRECTORY).rglob(f"*DEC_*{key}*"):
        path_string = path.absolute().as_posix().replace("/", "\\").replace("volumes", "\\ix200")
        print(path_string)
