"""Pull Risk Numbers from email subjects"""
import re

REGEX = r"RC: (?P<riskNum>\S{6}-\d)"
riskNums = []

with open(
    "C:\\dev\\scripts\\python\\Landy\\get-risk-nums-from-emails\\emails2.txt",
    encoding="utf-8",
) as f:
    data = f.read()
    for riskNum in re.findall(REGEX, data):
        if riskNum not in riskNums:
            riskNums.append(riskNum)

print(",".join(riskNums))
