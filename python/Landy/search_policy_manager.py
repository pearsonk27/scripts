"""Recursively search the Policy_Manager directory for a policy number"""

import os
from pathlib import Path
import time

DIRECTORY = "Y:\\Policy_Manager\\webdocs"
POLICY_NUMBERS = [
    "3082824",
    "4451088",
    "3083622",
    "4447688",
    "4446190",
    "4449418",
    "4444437",
    "3083032",
    "3082662",
    "4443869",
    "3082144",
    "3665555",
    "3665303",
    "3665464",
    "4117348",
]

#for path in Path(DIRECTORY).rglob(f"*{POLICY_NUMBERS[11]}*"):
for path in Path(DIRECTORY).rglob("*4453782*"):
    print(f"{path.absolute()} : {time.ctime(os.path.getctime(path))}")
