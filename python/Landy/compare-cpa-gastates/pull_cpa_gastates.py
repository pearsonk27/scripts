"""Build commands to pull all available version of CPA GAstate"""
import re

DATA = """
220103  221229  230301  230801  231201  240208  240214     clean.sh
220701  221230  230403  230901  240101  240209  240215     ifcfg-eth0
220901  230102  230501  231002  240201  240212  240216     renewals
221101  230201  230601  231101  240207  240213  clean.log
"""

REGEX = r"(\d{6})"

def build_commands():
    """Parse the data to get all the directories to be pulled from and build the commands"""
    pattern = re.compile(REGEX)
    for date_directory in re.findall(pattern, DATA):
        print(f"pull -af /usbx/{date_directory}/usr3/inter/data/GAstate > /ora2/garf/Kris/Projects/MakeGaSliderEditable_20240216/DataForComparison/GAstate{date_directory}.csv")

if __name__ == '__main__':
    build_commands()
