"""Copy files from the winmerge to interfacedocs"""
import glob
import shutil
import sys

try:
    LOB = sys.argv[1]
except Exception as exc:
    raise ValueError("Argument supplied must be CPA or RE") from exc

if LOB not in ("CPA", "RE"):
    raise ValueError("Argument supplied must be CPA or RE")

print('Copying LOB: ', LOB)

DEST_DIR = "Y:/interfacedocs/" + LOB
SOURCE_GLOB = r'Y:/mailmerge/' + LOB + '/*/*.pdf'

for file in glob.glob(SOURCE_GLOB):
    print(file)
    shutil.copy(file, DEST_DIR)
